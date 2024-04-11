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
# import pdfkit
from process_file import get_file_attachment_from_bytes
load_dotenv()
# config = pdfkit.configuration(wkhtmltopdf="C:\Program Files\wkhtmltopdf\\bin\wkhtmltopdf.exe")

odoo_db = os.environ.get('ODOO_DB')  # database name here

odoo_username = os.environ.get('ODOO_USERNAME')

odoo_password = os.environ.get('ODOO_PASSWORD')
proxy_url = '{}/xmlrpc/2/common'.format(odoo_url)
print(proxy_url)
common = xmlrpc.client.ServerProxy(proxy_url)

uid = common.authenticate(odoo_db, odoo_username, odoo_password, {})


odoo_models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(odoo_url))
odoo_models.execute_kw(odoo_db, uid, odoo_password, 'res.partner',
                       'check_access_rights', ['read'], {'raise_exception': False})


def authenticate(username, password):
    uid = common.authenticate(odoo_db, username, password, {})
    return uid


def search_order_by_po(po_number):
    query = [[['pro_po_number', '=', po_number], ['warehouse_receipt_num', '=', False]]]
    orders = search_orders(query)
    return orders


def search_order_by_supplier_invoice(invoice_number):

    query = [[('supplier_invoice.supplier_invoice_number', '=', invoice_number), ['warehouse_receipt_num', '=', False]]]
    orders = search_orders(query)
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
        width = float(dimensions_list[0])
        length = float(dimensions_list[1])
        height = float(dimensions_list[2])

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


def create_attachment_record(attachment, force=False):
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
    if not attachment_id or force:
        attachment_id = odoo_models.execute_kw(
            odoo_db, uid, odoo_password, 'ir.attachment', 'create', [attachment])

    return attachment_id


def get_update_order_fields(warehouse_receipt, order=None):
    """
    The function `get_update_order_fields` takes a warehouse receipt and an order as input and returns a
    dictionary of fields to update in the order based on the warehouse receipt.
    
    :param warehouse_receipt: The warehouse_receipt parameter is an object that represents a warehouse
    receipt. It has the following attributes:
    :param order: The "order" parameter is a dictionary that contains information about an order. It may
    have the following keys:
    :return: a dictionary called `fields_to_update` which contains the fields and their corresponding
    values that need to be updated in an order.
    """
    fields_to_update = {
        'warehouse_receipt_num': warehouse_receipt.number,
        'date_delivered_to_warehouse': warehouse_receipt.created_date.strftime('%Y-%m-%d'),
    }
    attachment_id = warehouse_receipt.laser_link.laser_attachment_id
    # magic_pdf = create_magic_link_pdf(warehouse_receipt)
    # if(magic_pdf):
    #     magic_attachment = get_file_attachment_from_bytes(magic_pdf, f"WHR {warehouse_receipt.number}.pdf")
    #     magic_pdf_id = create_attachment_record(magic_attachment)
    #     attachment_id = magic_pdf_id
    if ((order and not order['warehouse_receipt_attachment']) or order == None):
        fields_to_update['warehouse_receipt_attachment'] = [
            (4, attachment_id)]
    if (not order["glu_cargo_lines"]):
        line_ids = create_cargo_lines(warehouse_receipt.receipt_lines)
        fields_to_update["glu_cargo_lines"] = [(6, 0, line_ids)]
    if (not order["pro_trucker_company"]):
        fields_to_update["pro_trucker_company"] = "supplier"
    warehouse_receipt.laser_link.laser_attachment_id = attachment_id
    return fields_to_update

# def create_magic_link_pdf(warehouse_receipt):
#     """
#     The function `create_magic_link_pdf` generates a PDF file from a given warehouse receipt's magic
#     link.
    
#     :param warehouse_receipt: The parameter `warehouse_receipt` is an object that represents a warehouse
#     receipt. It likely contains information such as the receipt number, date, items stored in the
#     warehouse, and possibly a magic link
#     :return: a PDF file generated from the magic link provided in the warehouse receipt.
#     """
#     if(warehouse_receipt.magic_link):
#         pdf = pdfkit.from_url(warehouse_receipt.magic_link, configuration=config)
#         return pdf




def update_order_fields(order, warehouse_receipt):
    """
    The function updates the fields of an order in an Odoo database based on a warehouse receipt and
    returns the ID of the updated order.
    
    :param order: The "order" parameter is a dictionary that represents an order in the system. It
    contains various fields and their corresponding values
    :param warehouse_receipt: The warehouse_receipt parameter is an object representing a warehouse
    receipt. It likely contains information such as the receipt number, items received, quantities, and
    other relevant details
    :return: the 'id' field of the updated order.
    """
    fields_to_update = get_update_order_fields(warehouse_receipt, order)
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
    """
    The function `search_employee_by_uid` searches for an employee in the Odoo database based on their
    user ID and retrieves additional information such as their name, company, and job position.
    
    :param user_id: The user_id parameter is the unique identifier of the user for whom you want to
    search the employee information
    :return: a dictionary containing information about the employee with the given user ID. The
    dictionary includes the following keys:
    """
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
    """
    The function `update_order` updates an order in a warehouse receipt and returns a response with the
    updated order ID and a message.
    
    :param warehouse_receipt_id: The ID of the warehouse receipt that needs to be updated
    :return: a dictionary with the following keys and values:
    - "order": the order_id
    - "message": "Updated Model"
    - "order_url": the URL of the order record
    """
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



def create_order(id, requires_review=False):
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
        res["message"] = "A laser ORD already exists"
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
        pass
        # res["message"] = "Supplier/Vendor Not Found, Create a Laser Record for Supplier"
        # return res
    consignee_ids = odoo_models.execute_kw(
        odoo_db, uid, odoo_password, 'res.partner', 'search',
        [[['name', 'ilike', warehouse_receipt.consignee.contact_name]]]
    )

    consignee_id = None
    if (len(consignee_ids)):
        consignee_id = consignee_ids[0]
    else:
        pass
        # res["message"] = "Consignee Not Found, Create a Laser Record for Consignee"
        # return res

    if (warehouse_receipt.purchase_order):
        fields["pro_po_number"] = warehouse_receipt.purchase_order.po_number
    if (warehouse_receipt.invoice):
        supplier_invoice_id = get_or_create_supplier_invoice(
            warehouse_receipt.invoice.invoice_number)
        fields["supplier_invoice"] = [(4, supplier_invoice_id)]
    line_ids = create_cargo_lines(warehouse_receipt.receipt_lines)
    fields["glu_cargo_lines"] = [(6, 0, line_ids)]
    # Create the PurchaseRequestOrder record via Odoo RPC
    if(shipper_id):
        fields["pro_shipper"] = shipper_id
    if(consignee_id):
        fields["pro_consignee"] = consignee_id
    fields["pro_direction"] = "import"
    fields["pro_trucker_company"] = "supplier"
    fields["warehouse_receipt_num"] = warehouse_receipt.number
    fields["date_delivered_to_warehouse"] =  warehouse_receipt.created_date.strftime('%Y-%m-%d')
    if(warehouse_receipt.magic_link):
        fields["magic_link"] = warehouse_receipt.magic_link
    fields["state"] = 'warehouse'
    fields["requires_review"] = requires_review
    purchase_request_order_id = odoo_models.execute_kw(
        odoo_db, uid, odoo_password, 'purchase.request.order', 'create',
        [fields]
    )
    if (purchase_request_order_id):
        order_url = get_record_url('purchase.request.order', purchase_request_order_id)
        warehouse_receipt.laser_link.laser_order_id = purchase_request_order_id
        warehouse_receipt.laser_link.link_type = "manual"
        warehouse_receipt.laser_link.is_linked
        db.session.add(warehouse_receipt)
        db.session.commit()
        res = {"order": purchase_request_order_id, "message": "Created Model", "order_url": order_url, "receipt": warehouse_receipt}
    return res

def post_create_order(purchase_request_order_id, warehouse_receipt):
    if (purchase_request_order_id):
        order = search_order_by_id(purchase_request_order_id)
        update_order_fields(order, warehouse_receipt)        

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

def get_partners_by_name(name):
    partners = odoo_models.execute_kw(
            odoo_db,
            uid,
            odoo_password,
            'res.partner',
            'search_read', [[
                ('name', '=', name),
            ]],
            {
                'fields': ['name', 'email'],

            }
        )
    return partners

def create_email(subject, email_from, email_to, body_html, attachment_ids=None):
    if attachment_ids is None:
        attachment_ids = []
    values = {
    'subject': subject,
    'email_from': email_from,
    'email_to': email_to,
    'body_html': body_html,
    'attachment_ids': [(6, 0, attachment_ids)],  # Attachments
    }
    mail_id = odoo_models.execute_kw(odoo_db, uid, odoo_password, 'mail.mail', 'create', [values])
    print(values, mail_id)
    return mail_id

def send_email(mail_ids):
    print(mail_ids)
    odoo_models.execute_kw(odoo_db, uid, odoo_password, 'mail.mail', 'send', [mail_ids])



