from functools import wraps
import jwt
import datetime
import os
from flask import Blueprint, request, jsonify, session
from dotenv import load_dotenv
load_dotenv()
from flask_cors import CORS

maxAge = 60 * 60 * 24 * 3
jwt_secret = os.environ.get('JWT_SECRET')

def decode_jwt(jwt_token):
    return jwt.decode(jwt_token, jwt_secret, algorithms=['HS256'])

def generate_jwt(user_id, expiration_time=24):
    # Set the expiration time for the token
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=expiration_time)

    # Create the token payload with the user ID and expiration time
    payload = {
        'user_id': user_id,
        'exp': expires_at
    }

    # Generate the token using the secret key
    token = jwt.encode(payload, jwt_secret, algorithm='HS256')
    return token

def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' in session:
            user_id = session['user_id']
            return func(request, user_id, *args, **kwargs)
        else:
            return jsonify({'error': 'User is not authenticated'}), 401

    return wrapper


def set_cors(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:8080')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add(
        'Access-Control-Allow-Methods', '*')
    return response



def preflight(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method == 'OPTIONS':
            response = jsonify({"message":"Preflight Success"})
            response = set_cors(response)
            return response
        return func(*args, **kwargs)
    return wrapper