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
# from odoo_api import create_order
import reports
import process_file
import odoo_api
# from process_file import get_file_attachment
# create the extension
# create the app
load_dotenv()
app = Flask(__name__,
            static_url_path='/',
            static_folder='static',
            )  # configure the SQLite database, relative to the app instance folder
scheduler = BackgroundScheduler()
db_uri = os.environ.get(
    'SQLALCHEMY_DATABASE_URI')

if (os.environ.get('ENVIRONMENT') == 'development'):
    db_uri = os.environ.get('DEVELOPMENT_DATABASE_URI')
app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
# initialize the app with the extension
db.init_app(app)
migrate = Migrate(app, db)


app.register_blueprint(routes)


@scheduler.scheduled_job('interval', minutes=10)
def cron_job():
    print("APPLICATION RUNNING CRON STARTED")
    with app.app_context():
        run_extract_data()


# @scheduler.scheduled_job('interval', minutes=1)
def send_mail():
    with app.app_context():
        on_hand_list = [
            {
                'local_contact_name': 'Bryden PI Ltd',
                'odoo_contact_name': 'Bryden PI Ltd',
            }
        ]
        for config in on_hand_list:
            today = datetime.date.today()
            formatted_date = today.strftime("%d-%m-%Y")
            local_contact_name = config.get('local_contact_name', '')
            odoo_contact_name = config.get('odoo_contact_name', '')
            records = get_warehouse_receipts_by_date(today, local_contact_name)
            partners = odoo_api.get_partners_by_name(odoo_contact_name)
            partner = None
            title = f'{local_contact_name} On Hand Report  {formatted_date}'
            if (len(partners)):
                partner = partners[0]
            print(partners)
            if (partner):
                report = reports.OnHandReport()
                report.set_records(records)
                workbook = report.generate_report()
                attachment_data = process_file.attachment_from_workbook(
                    workbook, f'{title}.xlsx')
                attachment_id = odoo_api.create_attachment_record(
                    attachment_data)
                mail_id = odoo_api.create_email(title, 'itrd@rampslogistics.com', partner.get(
                    'email'), title, [attachment_id])
                print(mail_id)
                odoo_api.send_email([mail_id])

                print(attachment_id)


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
    print('APPLICATION STARTED')
    app.run(host='0.0.0.0', port=8000)
    # app.run(port=8000)
