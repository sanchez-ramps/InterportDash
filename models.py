import datetime
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

load_dotenv()

odoo_url = os.environ.get('ODOO_URL')

db = SQLAlchemy()


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50))


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note = db.Column(db.String(512))


class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50))


class ReceiptLine(db.Model):
    __tablename__ = 'receipt_line'
    id = db.Column(db.Integer, primary_key=True)
    pieces = db.Column(db.Integer)
    package_type = db.Column(db.String(50))
    piece_description = db.Column(db.String(100))
    dimensions = db.Column(db.String(50))
    weight = db.Column(db.Float)
    volume = db.Column(db.Float)
    hazardous = db.Column(db.Boolean)
    bonded_type = db.Column(db.String(50))
    warehouse_receipt_id = db.Column(
        db.Integer, db.ForeignKey('warehouse_receipt.id'))
    warehouse_receipt = db.relationship(
        'WarehouseReceipt', backref='receipt_lines')


class WarehouseReceipt(db.Model):
    __tablename__ = 'warehouse_receipt'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50))
    number = db.Column(db.String(50))
    created_date = db.Column(db.Date)
    pro_number = db.Column(db.String(50))
    tracking_number = db.Column(db.String(50))
    shipper_id = db.Column(db.Integer, db.ForeignKey('contact.id'))
    consignee_id = db.Column(db.Integer, db.ForeignKey('contact.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('contact.id'))
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'))
    purchase_order_id = db.Column(
        db.Integer, db.ForeignKey('purchase_order.id'))
    carrier_id = db.Column(db.Integer, db.ForeignKey('contact.id'))
    created_by_id = db.Column(db.Integer, db.ForeignKey('contact.id'))
    invoice = db.relationship('Invoice', backref='warehouse_receipt_statuses')
    purchase_order = db.relationship(
        'PurchaseOrder', backref='warehouse_receipt_statuses')
    note = db.relationship('Note', backref='warehouse_receipt_statuses')
    is_archived = db.Column(db.Boolean, default=False)

    @property
    def formatted_data(self):
        order_url = get_record_url(
            'purchase.request.order', self.laser_link.laser_order_id) if self.laser_link and self.laser_link.laser_order_id else None
        matched_date = self.laser_link.laser_order_id if self.laser_link and self.laser_link.link_date else None
        age = self.laser_link.age if self.laser_link and self.laser_link.link_date else None
        laser_id = self.laser_link.laser_order_id if self.laser_link and self.laser_link.link_date else None
        formatted_receipt = {
            'id': self.id,
            'status': self.status,
            'number': self.number,
            'created_by': self.created_by.contact_name if self.created_by else None,
            'created_date': self.created_date.strftime("%Y-%m-%d"),
            'shipper': self.shipper.contact_name if self.shipper else None,
            'supplier': self.supplier.contact_name if self.supplier else None,
            'consignee': self.consignee.contact_name if self.consignee else None,
            'receipt_lines': self.format_receipt_lines(),
            'note': self.note.note + "" if self.note else "Not Set",
            'invoice': self.invoice.invoice_number if self.invoice else None,
            'purchase_order': self.purchase_order.po_number if self.purchase_order else None,
            'carrier': self.carrier.contact_name if self.carrier else None,
            'laser_order': order_url,
            "matched_date": matched_date,
            "tracking_number": self.tracking_number + "" or "Not Set",
            "age": age,
            "laser_id": laser_id
        }

        return formatted_receipt

    def format_receipt_lines(self):
        formatted_lines = []
        for line in self.receipt_lines:
            formatted_line = {
                'pieces': line.pieces,
                'package_type': line.package_type,
                'piece_description': line.piece_description,
                'dimensions': line.dimensions,
                'weight': line.weight,
                'volume': line.volume,
                'hazardous': line.hazardous,
                'bonded_type': line.bonded_type
            }
            formatted_lines.append(formatted_line)
        return formatted_lines

    def display_formatted_data(self):
        formatted_string = f"Warehouse Receipt:\n" \
                           f"Status: {self.status}\n" \
                           f"Number: {self.number}\n" \
                           f"Created By: {self.created_by}\n" \
                           f"Created Date: {self.created_date}\n" \
                           f"Shipper: {self.shipper.contact_name if self.shipper else None}\n" \
                           f"Consignee: {self.consignee.contact_name if self.consignee else None}\n" \
                           f"ReceiptLine: {self.receipt_lines}\n" \
                           f"Note: {self.note}\n" \
                           f"Invoice: {self.invoice}\n" \
                           f"Purchase Order: {self.purchase_order}\n" \
                           f"Carrier: {self.carrier.contact_name}\n" \
                           f"Supplier: {self.supplier.contact_name if self.supplier else None}"
        return formatted_string


class ReceiptLaserLink(db.Model):
    __tablename__ = 'receipt_laser_link'
    id = db.Column(db.Integer, primary_key=True)
    link_type = db.Column(db.String(50))
    link_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_linked = db.Column(db.Boolean, default=False)
    laser_order_id = db.Column(db.Integer)
    warehouse_receipt_id = db.Column(
        db.Integer, db.ForeignKey('warehouse_receipt.id'), unique=True)
    warehouse_receipt = db.relationship(
        'WarehouseReceipt', backref=db.backref('laser_link', uselist=False))
    laser_attachment_id = db.Column(db.Integer)

    @property
    def age(self):
        return (datetime.datetime.utcnow() - self.link_date).days


class Contact(db.Model):
    __tablename__ = 'contact'
    id = db.Column(db.Integer, primary_key=True)
    contact_name = db.Column(db.String(100))
    warehouse_receipts_as_shipper = db.relationship(
        'WarehouseReceipt', backref='shipper', foreign_keys='WarehouseReceipt.shipper_id')
    warehouse_receipts_as_consignee = db.relationship(
        'WarehouseReceipt', backref='consignee', foreign_keys='WarehouseReceipt.consignee_id')
    warehouse_receipts_as_supplier = db.relationship(
        'WarehouseReceipt', backref='supplier', foreign_keys='WarehouseReceipt.supplier_id')
    warehouse_receipts_as_created_by = db.relationship(
        'WarehouseReceipt', backref='created_by', foreign_keys='WarehouseReceipt.created_by_id')
    warehouse_receipts_as_carrier = db.relationship(
        'WarehouseReceipt', backref='carrier', foreign_keys='WarehouseReceipt.carrier_id')


def get_or_create_contact(name, shipper=None):
    if name.lower() == "SAME AS SHIPPER".lower() and shipper:
        contact = shipper
    else:
        contact = Contact.query.filter_by(contact_name=name).first()
        if not contact:
            contact = Contact(contact_name=name)
    return contact


def get_or_create_warehouse_receipt(status, number, created_date, pro_number, tracking_number, new_receipts):
    warehouse_receipt = WarehouseReceipt.query.filter_by(number=number).first()
    if not warehouse_receipt:
        warehouse_receipt = WarehouseReceipt(number=number)
        new_receipts.append(number)

    warehouse_receipt.status = status
    warehouse_receipt.created_date = created_date
    warehouse_receipt.pro_number = pro_number
    warehouse_receipt.tracking_number = tracking_number

    return warehouse_receipt


def get_record_url(model, record_id):
    record_url = f'{odoo_url}/web#id={record_id}&model={model}'
    return record_url
