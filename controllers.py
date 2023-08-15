from models import ReceiptLaserLink, WarehouseReceipt, db
from flask import jsonify


def get_formatted_receipts(receipts):
    formatted_receipts = [receipt.formatted_data for receipt in receipts]
    
    return formatted_receipts
# Retrieve pending warehouse receipts
def get_pending_warehouse_receipts(req):
    warehouse_receipts = WarehouseReceipt.query.filter(~WarehouseReceipt.laser_link.has(ReceiptLaserLink.laser_order_id.isnot(None)),WarehouseReceipt.is_archived == False).all()    
    return get_formatted_receipts(warehouse_receipts)

def get_matched_warehouse_receipts(req):
    warehouse_receipts = WarehouseReceipt.query.filter(
        WarehouseReceipt.laser_link.has(ReceiptLaserLink.laser_order_id.isnot(None)),
        WarehouseReceipt.laser_link.has(ReceiptLaserLink.is_linked == False),
        WarehouseReceipt.is_archived == False
    ).all()
    return get_formatted_receipts(warehouse_receipts)

# Retrieve linked warehouse receipts
def get_linked_warehouse_receipts(req):
    warehouse_receipts = WarehouseReceipt.query.filter(WarehouseReceipt.laser_link.has(ReceiptLaserLink.is_linked == True), WarehouseReceipt.is_archived == False).all()
    return get_formatted_receipts(warehouse_receipts)
    
# Format the warehouse receipts and convert relational fields to strings
def format_warehouse_receipts(warehouse_receipts):
    formatted_receipts = []
    for receipt in warehouse_receipts:
        formatted_receipt = {
            'status': receipt.status,
            'number': receipt.number,
            'created_by': receipt.created_by.contact_name if receipt.created_by else 'N/A',
            'created_date': str(receipt.created_date),
            'shipper': receipt.shipper.contact_name if receipt.shipper else 'N/A',
            'consignee': receipt.consignee.contact_name if receipt.consignee else 'N/A',
            'receipt_lines': format_receipt_lines(receipt.receipt_lines),
            'note': receipt.note.note if receipt.note else 'N/A',
            'invoice': receipt.invoice.invoice_number if receipt.invoice else 'N/A',
            'purchase_order': receipt.purchase_order.po_number if receipt.purchase_order else 'N/A',
            'carrier': receipt.carrier.contact_name
        }
        formatted_receipts.append(formatted_receipt)
    return formatted_receipts


    

# Format the receipt lines and convert relational fields to strings
def format_receipt_lines(receipt_lines):
    formatted_lines = []
    for line in receipt_lines:
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

def archive_receipt(id):
    receipt = get_warehouse_receipt_by_id(id)
    receipt.is_archived = True
    print(receipt, receipt.is_archived)
    db.session.add(receipt)
    db.session.commit()
    return receipt

def get_warehouse_receipt_by_id(id):
    warehouse_receipt = WarehouseReceipt.query.filter(
            WarehouseReceipt.id == id
        ).first()
    return warehouse_receipt

