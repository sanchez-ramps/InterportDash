import datetime
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import pysftp
import csv
import os
from models import *
import odoo_api, process_file, dashboard_config

load_dotenv()
env = os.environ.get('ENVIRONMENT')  # database name here

def flask_extract_data_from_csv(filename, sftp, new_receipts):
        with sftp.open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            warehouse_receipt_statuses = []
        # try:
            for row in reader:
                # Extract data from the CSV row
                status = row['Status']
                number = row['Number']
                created_by_name = row['CreatedBy']
                created_date_str = row['CreatedDate']  # Get the date as a string
                created_date = datetime.datetime.strptime(created_date_str, '%Y-%m-%d').date()  # Convert to date object
                shipper_name = row['ShipperName']
                consignee_name = row['ConsigneeName']
                pieces = float(row['Pieces'])
                package_type = row['PackageType']
                piece_description = row['PieceDescription']
                dimensions = row['Dimensions']
                weight = float(row['Weight'])
                volume = float(row['Volume'])
                hazardous = bool(row['Hazardous'])
                bonded_type = row['BondedType']
                notes = row['Notes'] + ""
                invoice_number = row['InvoiceNumber']
                po_number = row['PONumber']
                carrier_name = row['CarrierName']
                pro_number = row['PRONumber']
                tracking_number = row['TrackingNumber']
                supplier_name = row['SupplierName']
                magic_id = ''
                try:
                    magic_id = row['ID']
                except:
                    pass

                # Check if the contact already exists or create a new one
                shipper = get_or_create_contact(shipper_name)
                consignee = get_or_create_contact(consignee_name, shipper)
                carrier = get_or_create_contact(carrier_name, shipper)
                created_by = get_or_create_contact(created_by_name, shipper)
                if supplier_name == "SAME AS SHIPPER":
                    supplier = shipper
                elif supplier_name:
                    supplier = get_or_create_contact(supplier_name, shipper)
                else:
                    supplier = None

                # Create instances of the models
                # WarehouseReceipt(status=status, number=number, created_date=created_date, pro_number=pro_number,tracking_number=tracking_number )

                receipt_line = ReceiptLine(pieces=pieces, package_type=package_type, piece_description=piece_description, dimensions=dimensions, weight=weight, volume=volume, hazardous=hazardous, bonded_type=bonded_type)
                note = Note(note=notes)
                warehouse_receipt_status = get_or_create_warehouse_receipt(status, number, created_date, pro_number,tracking_number, new_receipts)

                
                invoice = Invoice.query.filter_by(invoice_number=invoice_number).first()
                if not invoice and invoice_number:
                    invoice = Invoice(invoice_number=invoice_number)
                orders = []
                if invoice_number:
                    orders+=odoo_api.search_order_by_supplier_invoice(invoice_number)
                purchase_order = PurchaseOrder.query.filter_by(po_number=po_number).first()
                if not purchase_order and po_number:
                    purchase_order = PurchaseOrder(po_number=po_number)
                if po_number:
                    orders+=odoo_api.search_order_by_po(po_number)
                query = [[['warehouse_receipt_num', '=', number],]]
                orders+=odoo_api.search_orders(query)

                if(number in new_receipts):
                    warehouse_receipt_status.receipt_lines.append(receipt_line)
                # Establish relationships between the models
                warehouse_receipt_status.note = note
                warehouse_receipt_status.invoice = invoice
                warehouse_receipt_status.purchase_order = purchase_order

                warehouse_receipt_status.shipper = shipper
                warehouse_receipt_status.consignee = consignee
                warehouse_receipt_status.supplier = supplier
                warehouse_receipt_status.carrier = carrier
                warehouse_receipt_status.created_by = created_by
                warehouse_receipt_status.magic_id = magic_id

                attachment = process_file.get_file_attachment(sftp, filename)
                attachment_id = odoo_api.create_attachment_record(attachment)
                # warehouse_receipt_status.laser_attachment_id = attachment_id
                new_link = ReceiptLaserLink(laser_order_id=None, laser_attachment_id=attachment_id, link_type='auto',
                                    link_date=datetime.datetime.utcnow(), is_linked=False)
                old_link = warehouse_receipt_status.laser_link
                if(not old_link):
                    warehouse_receipt_status.laser_link = new_link
                for order in orders:
                    type ="auto"
                    is_linked = False
                    receipt_num  = order["warehouse_receipt_num"]
                    if(receipt_num):
                        type="pre"
                    if(not warehouse_receipt_status.laser_link.laser_order_id and (not receipt_num or receipt_num == number)):
                        warehouse_receipt_status.laser_link = ReceiptLaserLink(laser_order_id=order["id"], laser_attachment_id=attachment_id, link_type=type,link_date=datetime.datetime.utcnow(), is_linked=is_linked)
        
                # Append the warehouse_receipt status to the list
                db.session.add(warehouse_receipt_status)
                db.session.commit()
                print(warehouse_receipt_status.formatted_data)
                warehouse_receipt_statuses.append(warehouse_receipt_status)

                # Add all the warehouse_receipt statuses to the database

        # except Exception as e:
        return warehouse_receipt_statuses



def move_file(sftp, filename, source_dir, destination_dir):
    # Move the file from the source directory to the destination directory
    try:
        source_path = source_dir + '/' + filename
        destination_path = destination_dir + '/' + filename
        sftp.rename(source_path, destination_path)
        print("Moved file:", filename)
    except Exception as e:
        print(e)


def run_extract_data():
    ftp_host = os.environ.get('FTP_HOST')
    ftp_user = os.environ.get('FTP_USER')
    ftp_password = os.environ.get('FTP_PASSWORD')
    source_dir = '/In'
    destination_dir = '/Out'
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    with pysftp.Connection(host=ftp_host, username=ftp_user, password=ftp_password, cnopts=cnopts) as sftp:
        print("Connection successfully established...")
        sftp.cwd(source_dir)
        file_list = sftp.listdir()

        for filename in file_list:
            new_reciepts = []
            print("New file detected:", filename)
            try:
                statuses = flask_extract_data_from_csv(filename, sftp, new_reciepts)
                for status in statuses:
                    print(odoo_api.create_order(status.id, requires_review=True))
                # Move the file to the destination directory
                if(env == 'production'):
                    move_file(sftp, filename, source_dir, destination_dir)
            except Exception as e:
                print(f"Error Parsing {filename}: {e}")
