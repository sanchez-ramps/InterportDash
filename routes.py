from auth import generate_jwt, decode_jwt, preflight, set_cors
import dashboard_config
from controllers import *
import controllers
from flask import Flask, request, jsonify, Blueprint, session, make_response, render_template, send_from_directory, Response
import jwt
from odoo_api import search_employee_by_uid, authenticate as odoo_auth, create_order as odoo_create_order, update_order as odoo_update_order, get_laser_orders, update_receipt_laser_id, append_order_num, post_create_order
import requests
from flask_cors import cross_origin, CORS
from urllib.parse import urlparse


max_age = 60 * 60 * 24 * 3
routes = Blueprint('routes', __name__)
CORS(routes, resources={
     r"/*": {"origins": "http://localhost:8080"}}, supports_credentials="true")
origin = "http://localhost:8080,http://192.168.1.182:8100,https://fc50-181-118-42-7.ngrok-free.app"



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
    results = [append_order_num(result) for result in results]
    return jsonify(results)


@routes.route('/consignees', methods=['GET'])
@cross_origin(origin, supports_credentials="true")
def get_consignees():
    # try:
    # Call the controller function
    results = controllers.get_consignees(request)
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
        if (receipt.is_archived):
            successful_archives.append(id)

    return jsonify({"ids": successful_archives}), 200


@routes.route('/create-order', methods=['POST', 'OPTIONS'])
@cross_origin(origin, supports_credentials="true")
def create_order():
    id = request.json.get('id')

    res = odoo_create_order(id)

    if res["order"]:
        post_create_order(res.get('order'), res.get('receipt'))
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


@routes.route('/laser-login', methods=['POST', 'OPTIONS'])
@cross_origin(origin)
def laser_login():
    username = request.json.get('login')
    password = request.json.get('password')
    print([username, password])
    session_url = f'http://localhost:8040/ramps-base/login'
    data = {
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
            'login': username,
            'password': password,
        }
    }
    session_response = requests.post(session_url, json=data)
    session_data = session_response.json()
    session_id = None
    if session_data.get('result') and session_response.cookies.get('session_id'):
        session_id = session_response.cookies['session_id']
    else:
        print(f'Error: Failed to authenticate - {session_data.get("error")}')
        return None
    return jsonify({'session_id': session_id})


@routes.route('/api/<path:endpoint>', methods=['POST', 'OPTIONS'])
@cross_origin(origin, supports_credentials="true")
def api(endpoint):
    # Construct the Odoo URL dynamically based on the additional path
    odoo_url = f'http://161.0.153.215:8040/{endpoint}'

    # Get data from the Vue app
    data = request.get_json()

    # Include cookies from the original request
    cookies = request.cookies

    # Make a request to the Odoo web controller
    odoo_response = requests.post(odoo_url, json=data, cookies=cookies)
    request_origin = request.headers.get('Origin')
    parsed_url = urlparse(request_origin)
    

    # Return the exact response from Odoo, including data and cookies
    if( 'json' in odoo_response.headers['Content-Type']):
        response = jsonify(odoo_response.json())
    else:
        response = Response(
            response=odoo_response.content,
            status=odoo_response.status_code,
            content_type=odoo_response.headers['Content-Type'],  
        )
    print(parsed_url.netloc)
    # Set any additional cookies from Odoo in the response to the Vue app
    for key, value in odoo_response.cookies.items():
        response.set_cookie(key, value, samesite='None', max_age=7776000, secure=True)

    return response

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
