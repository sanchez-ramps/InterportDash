import datetime
from functools import wraps

from routes import routes

from extract import run_extract_data
from flask import Flask, jsonify, request, send_from_directory, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
import pysftp
import csv
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from controllers import *
from models import *
from odoo_api import create_order
# import odoo_api
# from process_file import get_file_attachment
# create the extension
# create the app
load_dotenv()
app = Flask(__name__,
            static_url_path='/',
            static_folder='static',
            )  # configure the SQLite database, relative to the app instance folder
scheduler = BackgroundScheduler()
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    'SQLALCHEMY_DATABASE_URI')
# initialize the app with the extension
db.init_app(app)
migrate = Migrate(app, db)



app.register_blueprint(routes)


@scheduler.scheduled_job('interval', minutes=60)
def cron_job():
    print("This is a cron job that runs every 120 minutes.")
    with app.app_context():
        run_extract_data()

scheduler.start()


# sanity check route
@app.route('/ping', methods=['GET'])
def ping_pong():
    return jsonify('pong!')


@app.route('/', methods=['GET'])
def serve_static_files():
    return send_from_directory('static', 'index.html')


@app.route('/dashboard', methods=['GET'])
def dashboard():
    return redirect(url_for('serve_static_files'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
    # app.run(port=8000)
