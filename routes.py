from auth import generate_jwt, decode_jwt, preflight, set_cors
import dashboard_config
from controllers import *
from flask import Flask, request, jsonify, Blueprint, session, make_response, render_template, send_from_directory
import jwt
from odoo_api import search_employee_by_uid, authenticate as odoo_auth, create_order as odoo_create_order, update_order as odoo_update_order, get_laser_orders, update_receipt_laser_id, append_order_num
from flask_cors import cross_origin, CORS


max_age = 60 * 60 * 24 * 3
routes = Blueprint('routes', __name__)
CORS(routes, resources={r"/*": {"origins": "http://localhost:8080"}}, supports_credentials="true")
origin = "http://localhost:8080"


@routes.route('/laser-orders', methods=['GET'])
@cross_origin(origin, supports_credentials="true")
def laser_orders():
    orders = get_laser_orders()
    print(orders)
    return jsonify(orders)

@routes.route('/update-receipt-by-order', methods=['POST', "OPTIONS"])
@cross_origin(origin, supports_credentials="true")
def update_receipt_by_order():
    order = request.json.get('order')
    receipt = request.json.get('receipt')
    update_receipt_laser_id(receipt["id"], order["id"])
    res = odoo_update_order(receipt["id"])
    print(res)
    if res["order"]:
        return jsonify(res)
    else:
        return jsonify(res), 401



@routes.route('/matched-warehouse-receipts', methods=['GET'])
@cross_origin(origin, supports_credentials="true")
def matched_warehouse_receipts():
    # try:
        # Call the controller function

        results = get_matched_warehouse_receipts(request)
        results = [append_order_num(result) for result in results]
        print(results)
        return jsonify(results)
    # except Exception as e:
    #     return jsonify(error='An error occurred'), 400

@routes.route('/linked-warehouse-receipts', methods=['GET'])
@cross_origin(origin, supports_credentials="true")
def linked_warehouse_receipts():
    # try:
        # Call the controller function
        results = get_linked_warehouse_receipts(request)
        print(results)
        return jsonify(results)
    # except Exception as e:
    #     return jsonify(error='An error occurred'), 400

# Route for retrieving pending warehouse receipts


@routes.route('/pending-warehouse-receipts', methods=['GET'])
@cross_origin(origin, supports_credentials="true")
def pending_warehouse_receipts():
    # try:
        # Call the controller function
        pending_receipts = get_pending_warehouse_receipts(request)

        # Get the value of the 'fields' query parameter
        fields = request.args.get('fields')
        # Parse the 'fields' parameter as a list of fields
        fields_list = fields.strip('[]').split(',')
        # Filter the fields based on 'fields_list'
        # filtered_receipts = [{field: receipt[field] for field in fields_list} for receipt in pending_receipts]
        print(pending_receipts)
        return jsonify(pending_receipts)
    # except Exception as e:
    #     return jsonify(error='An error occurred')


@routes.route('/menu', methods=['GET'])
@cross_origin(origin, supports_credentials="true")
def get_data():
    return jsonify(dashboard_config.menu_items)

# Authentication route
@routes.route('/archive-receipt', methods=['POST', 'OPTIONS'])
@cross_origin(origin, supports_credentials="true")
def archive_receipt_route():
    id = request.json.get('id')
    receipt = archive_receipt(id)
    res = receipt.formatted_data
    if receipt.is_archived:
        return jsonify(res)
    else:
        return jsonify(res), 401

# Authentication route
@routes.route('/archive-receipts', methods=['POST', 'OPTIONS'])
@cross_origin(origin, supports_credentials="true")
def archive_receipts_route():
    print(request.json)
    successful_archives = []
    for id in request.json:
            receipt = archive_receipt(id)
            print(receipt.is_archived)
            if(receipt.is_archived):
                successful_archives.append(id)
        

    return jsonify({"ids":successful_archives}), 200
    


@routes.route('/create-order', methods=['POST', 'OPTIONS'])
@cross_origin(origin, supports_credentials="true")
def create_order():
    id = request.json.get('id')
    
    res = odoo_create_order(id)

    if res["order"]:
        return jsonify(res)

    else:
        return jsonify(res), 401

@routes.route('/update-order', methods=['POST', 'OPTIONS'])
@cross_origin(origin, supports_credentials="true")
def update_order():
    id = request.json.get('id')
    res = odoo_update_order(id)
    print(res)
    if res["order"]:
        return jsonify(res)
    else:
        return jsonify(res), 401

@routes.route('/login', methods=['POST', 'OPTIONS'])
@cross_origin(origin, supports_credentials="true")
def authenticate_user():
    username = request.json.get('username')
    password = request.json.get('password')
    # Perform authentication with Odoo
    user_id = odoo_auth(username, password)
    if user_id:
        # Store the user ID in the session
        user_jwt = generate_jwt(user_id)
        employee = {
            'userID': user_id,
            'company': "",
            'role': "",
            'correctPassword': True if user_id else False,
            'correctUsername': True if user_id else False
        }
        # employee = search_employee_by_uid(user_id)
        response = make_response(jsonify(employee))
        response.set_cookie('JWT', user_jwt, max_age=max_age * 1000,
                            secure=True, httponly=False, samesite='None')
        return response
    else:
        return jsonify({'correctUsername': False, 'correctPassword': False}), 401



@routes.route('/logout', methods=['GET'])
@cross_origin(origin, supports_credentials="true")
def logout():
    # Set JWT token to an empty string, effectively logging the user out
    response = make_response(jsonify({}))
    response.set_cookie('JWT', '', max_age=1, secure=True,
                        httponly=False, samesite='None')
    return response


@routes.route('/check-login', methods=['GET'])
@cross_origin(origin, supports_credentials="true")
def check_login():
    jwt_token = request.cookies.get('JWT')
    try:
        # Verify the JWT token and retrieve the user ID
        payload = decode_jwt(jwt_token)
        user_id = payload['user_id']
        # Retrieve the user from the database based on the user ID
        employee = search_employee_by_uid(user_id)

        if employee:
            # Return the user information
            return jsonify({
                'jwtValid': True,
                'user': employee
            })

    except jwt.ExpiredSignatureError:
        # JWT token has expired
        pass
    except (jwt.DecodeError, jwt.InvalidTokenError):
        # JWT token is invalid
        pass

    # If the JWT token is not valid or expired, return an error
    return jsonify({'jwtValid': False}), 401
