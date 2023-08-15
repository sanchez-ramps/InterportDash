from controllers import get_warehouse_receipt_by_id
from dotenv import load_dotenv
import xmlrpc.client
import base64
import tempfile
import json
import zlib
import os
import mimetypes
from models import *
load_dotenv()

odoo_url = os.environ.get('ODOO_URL')

odoo_db = os.environ.get('ODOO_DB')  # database name here

odoo_username = os.environ.get('ODOO_USERNAME')

odoo_password = os.environ.get('ODOO_PASSWORD')
proxy_url = '{}/xmlrpc/2/common'.format(odoo_url)
common = xmlrpc.client.ServerProxy(proxy_url)

uid = common.authenticate(odoo_db, odoo_username, odoo_password, {})


odoo_models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(odoo_url))
odoo_models.execute_kw(odoo_db, uid, odoo_password, 'res.partner',
                       'check_access_rights', ['read'], {'raise_exception': False})


def authenticate(username, password):
    uid = common.authenticate(odoo_db, username, password, {})
    return uid


def search_order_by_po(po_number):
    query = [[['pro_po_number', '=', po_number],]]
    orders = search_orders(query)
    return orders


def search_order_by_supplier_invoice(invoice_number):

    query = [[('supplier_invoice.supplier_invoice_number', '=', invoice_number),]]
    orders = search_orders(query)
    print(orders, "Supplier Invoice: ", invoice_number)
    return orders
    # odoo_models.execute_kw(odoo_db, uid, odoo_password, 'supplier.invoice', 'write', [[shipments[index]['id']], {'serial_number': serial_num_string, 'part_number': part_num_string}])
    # return slb_brokerage_shipments


def search_order_by_id(id):
    query = [[['id', '=', id],]]
    orders = search_orders(query)
    return orders[0] if len(orders) else None


def search_orders(query, fields=['warehouse_receipt_num', 'date_delivered_to_warehouse', 'warehouse_receipt_attachment', "supplier_invoice", "glu_cargo_lines", "pro_trucker_company", "pro_ref_num"]):
    orders = odoo_models.execute_kw(
        odoo_db,
        uid,
        odoo_password,
        'purchase.request.order',
        'search_read', query,
        {
            'fields': fields,
        }
    )
    return orders


def get_or_create_supplier_invoice(invoice_number):
    # Save the attachment record in Odoo
    supplier_invoice_ids = odoo_models.execute_kw(
        odoo_db,
        uid,
        odoo_password,
        'supplier.invoice',
        'search_read', [[
            ('supplier_invoice_number', '=', invoice_number),
        ]],
        {
            'limit': 1,
        }
    )
    supplier_invoice_id = None
    if (len(supplier_invoice_ids)):
        supplier_invoice_id = supplier_invoice_ids[0]["id"]
    if not supplier_invoice_id:
        supplier_invoice_id = odoo_models.execute_kw(
            odoo_db, uid, odoo_password, 'supplier.invoice', 'create', [{"supplier_invoice_number": invoice_number}])
    return supplier_invoice_id


def create_cargo_lines(lines):
    # Save the attachment record in Odoo
    line_ids = []
    for line in lines:
        # Split the string using 'x' as the delimiter
        dimensions_list = line.dimensions.split('x')

        # Extract width, length, and height values from the list
        width = int(dimensions_list[0])
        length = int(dimensions_list[1])
        height = int(dimensions_list[2])

        line_fields = {
            "cargo_length": length,
            "cargo_width": width,
            "cargo_height": height,
            "cargo_quantity": line.pieces,
            "cargo_weight": line.weight,
        }

        supplier_invoice_ids = odoo_models.execute_kw(
            odoo_db,
            uid,
            odoo_password,
            'quotation.package',
            'search', [[
                ('name', '=', line.package_type),
            ]],
            {
                'limit': 1,
            }
        )
        if (len(supplier_invoice_ids)):
            line_fields["cargo_package_type"] = supplier_invoice_ids[0]
        line_id = odoo_models.execute_kw(
            odoo_db, uid, odoo_password, 'glu.cargo.line', 'create', [line_fields])
        line_ids.append(line_id)
    return line_ids


def create_attachment_record(attachment):
    # Save the attachment record in Odoo
    attachment_ids = odoo_models.execute_kw(
        odoo_db,
        uid,
        odoo_password,
        'ir.attachment',
        'search_read', [[
            ('name', '=', attachment["name"]),
        ]],
        {
            'limit': 1,
        }
    )
    attachment_id = None
    if (len(attachment_ids)):
        attachment_id = attachment_ids[0]["id"]
    if not attachment_id:
        attachment_id = odoo_models.execute_kw(
            odoo_db, uid, odoo_password, 'ir.attachment', 'create', [attachment])

    return attachment_id


def get_update_order_fields(warehouse_receipt, order=None):
    fields_to_update = {
        'warehouse_receipt_num': warehouse_receipt.number,
        'date_delivered_to_warehouse': warehouse_receipt.created_date.strftime('%Y-%m-%d'),
    }
    if ((order and not order['warehouse_receipt_attachment']) or order == None):
        fields_to_update['warehouse_receipt_attachment'] = [
            (4, warehouse_receipt.laser_link.laser_attachment_id)]
    if (not order["glu_cargo_lines"]):
        line_ids = create_cargo_lines(warehouse_receipt.receipt_lines)
        fields_to_update["glu_cargo_lines"] = [(6, 0, line_ids)]
    if (not order["pro_trucker_company"]):
        fields_to_update["pro_trucker_company"] = "supplier"
    return fields_to_update





def update_order_fields(order, warehouse_receipt):
    fields_to_update = get_update_order_fields(warehouse_receipt, order)
    print(fields_to_update)
    odoo_models.execute_kw(
        odoo_db,
        uid,
        odoo_password,
        'purchase.request.order',
        'write',
        [[order['id']], fields_to_update]
    )
    warehouse_receipt.laser_link.laser_order_id = order['id']
    warehouse_receipt.laser_link.is_linked = True
    warehouse_receipt.laser_link.link_date = datetime.datetime.utcnow()
    return order['id']


def search_employee_by_uid(user_id):
    employee = odoo_models.execute_kw(
        odoo_db,
        uid,
        odoo_password,
        'hr.employee',
        'search_read', [[
            ('user_id', '=', user_id),
        ]],
        {
            # Include the fields 'company_id' and 'job_id'
            'fields': ['name', 'company_id', 'job_id'],
            'limit': 1,
        }
    )
    if employee:

        result = {
            'userID': user_id,
            'correctPassword': True if employee else False,
            'correctUsername': True if employee else False
        }

        fields = [
            {
                "odoo_field": "job_id",
                "employee_field": "position",
                "odoo_model": "hr.job"
            },
            {
                "odoo_field": "company_id",
                "employee_field": "role",
                "odoo_model": "hr.department"
            }
        ]

        for field in fields:
            odoo_field = field["odoo_field"]
            odoo_model = field["odoo_model"]
            employee_field = field["employee_field"]
            if (employee[0][odoo_field]):
                id = employee[0][odoo_field][0]
                if (id):
                    record = odoo_models.execute_kw(
                        odoo_db,
                        uid,
                        odoo_password,
                        odoo_model,
                        'read', [id],
                        {'fields': ['name']}
                    )
                    if record:
                        result[employee_field] = record[0]["name"]

    return result


def get_record_url(model, record_id):
    record_url = f'{odoo_url}/web#id={record_id}&model={model}'
    return record_url

def update_receipt_laser_id(warehouse_receipt_id, laser_id):
    receipt = get_warehouse_receipt_by_id(warehouse_receipt_id)
    receipt.laser_link.laser_order_id = laser_id
    db.session.commit()


def update_order(warehouse_receipt_id):
    receipt = get_warehouse_receipt_by_id(warehouse_receipt_id)
    order_id = receipt.laser_link.laser_order_id
    order = search_order_by_id(order_id)
    update_order_fields(order, receipt)
    receipt.laser_link.is_linked = True
    db.session.commit()
    order_url = get_record_url(
            'purchase.request.order', order_id)
    res = {"order": order_id,
               "message": "Updated Model", "order_url": order_url}
    return res



def create_order(id):
    # Retrieve the warehouse receipt from the Flask database based on the receipt number
    res = {"order": None, "message": ""}
    warehouse_receipt = get_warehouse_receipt_by_id(id)
    update_order = update_link(warehouse_receipt)
    if(update_order):
        return {"order": update_order, "message": "Order Existed. Updates Made"}
    query = [[['warehouse_receipt_num', '=', warehouse_receipt.number],]]
    laser_receipts = search_orders(query)
    if (len(laser_receipts)):
        warehouse_receipt.laser_link.laser_order_id = laser_receipts[0]["id"]
        db.session.commit()
        res["message"] = "A laser PRO already exists"
        return res

    fields = {}
    # Search for the related records and assign their IDs
    shipper_ids = odoo_models.execute_kw(
        odoo_db, uid, odoo_password, 'res.partner', 'search',
        [[['name', 'ilike', warehouse_receipt.shipper.contact_name]]]
    )
    shipper_id = None
    if (len(shipper_ids)):
        shipper_id = shipper_ids[0]
    else:
        res["message"] = "Supplier/Vendor Not Found, Create a Laser Record for Supplier"
        return res
    consignee_ids = odoo_models.execute_kw(
        odoo_db, uid, odoo_password, 'res.partner', 'search',
        [[['name', 'ilike', warehouse_receipt.consignee.contact_name]]]
    )

    consignee_id = None
    if (len(consignee_ids)):
        consignee_id = consignee_ids[0]
    else:
        res["message"] = "Consignee Not Found, Create a Laser Record for Consignee"
        return res

    if (warehouse_receipt.purchase_order):
        fields["pro_po_number"] = warehouse_receipt.purchase_order.po_number
    if (warehouse_receipt.invoice):
        supplier_invoice_id = get_or_create_supplier_invoice(
            warehouse_receipt.invoice.invoice_number)
        fields["supplier_invoice"] = [(4, supplier_invoice_id)]
    line_ids = create_cargo_lines(warehouse_receipt.receipt_lines)
    fields["glu_cargo_lines"] = [(6, 0, line_ids)]
    # Create the PurchaseRequestOrder record via Odoo RPC
    fields["pro_shipper"] = shipper_id
    fields["pro_consignee"] = consignee_id
    fields["pro_direction"] = "import"
    fields["pro_trucker_company"] = "supplier"
    purchase_request_order_id = odoo_models.execute_kw(
        odoo_db, uid, odoo_password, 'purchase.request.order', 'create',
        [fields]
    )
    if (purchase_request_order_id):
        order = search_order_by_id(purchase_request_order_id)
        update_order_fields(order, warehouse_receipt)
        warehouse_receipt.laser_link.laser_order_id = purchase_request_order_id
        warehouse_receipt.laser_link.link_type = "manual"
        warehouse_receipt.laser_link.is_linked
        db.session.add(warehouse_receipt)
        db.session.commit()
        order_url = get_record_url(
            'purchase.request.order', purchase_request_order_id)
        res = {"order": purchase_request_order_id,
               "message": "Created Model", "order_url": order_url}
    return res
    # if purchase_request_order_id:
    #     # Create the cargo lines from the receipt lines and link them to the PurchaseRequest
    #     receipt_lines = warehouse_receipt.receipt_lines # Implement this function to retrieve receipt lines
    #     cargo_line_data = []
    #     for line in receipt_lines:
    #         cargo_line_data.append({
    #             'order_id': purchase_request_order_id,
    #             'product_id': product_id,
    #             'product_qty': line['quantity'],
    #             # Include other cargo line fields and their corresponding values based on the receipt line structure
    #         })

    #     cargo_line_ids = models.execute_kw(
    #         db, uid, password, 'purchase.request.order.line', 'create',
    #         cargo_line_data
    #     )

    #     if cargo_line_ids:
    #         return f"PurchaseRequestOrder created with ID: {purchase_request_order_id}"
    #     else:
    #         return "Failed to create cargo lines"
    # else:
    #     return "Failed to create PurchaseRequestOrder"


def update_link(receipt):
    orders = []
    invoice_number = receipt.invoice.invoice_number if receipt.invoice else None
    po_number = receipt.purchase_order.po_number if receipt.purchase_order else None
    if invoice_number:
        orders += search_order_by_supplier_invoice(invoice_number)
    if po_number:
        orders += search_order_by_po(po_number)

    if (not len(orders)):
        return None
    
    for order in orders:
        update_order_fields(order, receipt)
        receipt.laser_link.link_type = "manual"
        return order
 
def format_pending_order_fields(order):
    order['pro_mode_of_transport'] = order.get('pro_mode_of_transport', '') or ''
    order['pro_shipper'] = order.get('pro_shipper', [''])[1] if order.get('pro_shipper') else ''
    order['pro_consignee'] = order.get('pro_consignee', [''])[1] if order.get('pro_consignee') else ''

    order['pro_po_number'] = order.get('pro_po_number', '') or ''
    order['pro_ref_num'] = order.get('pro_ref_num', '') or ''
    order['supplier_promise_date'] = order.get('supplier_promise_date', '') or ''
    return order

def get_laser_orders():
    query = [[['pro_direction', '=', 'import'],['state', 'in', ['order', "trucking"]],]]
    fields = ["pro_mode_of_transport", "pro_shipper", "pro_po_number", "pro_ref_num", "supplier_promise_date", "pro_consignee"]

    orders = search_orders(query, fields=fields)
    formatted_orders = list(map(format_pending_order_fields, orders))
    return formatted_orders

def append_order_num(formatted_receipt):
    laser_id = formatted_receipt["laser_id"]
    order_num = None
    if(laser_id):
       order = search_order_by_id(laser_id)
       if(order):
           order_num = order["pro_ref_num"]
    formatted_receipt["order_num"] = order_num
    return formatted_receipt
    

