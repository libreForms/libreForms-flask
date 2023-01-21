""" 
reports.py: report configuration views and logic


"""

__name__ = "app.views.reports"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# import flask-related packages
from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import current_user
from markupsafe import Markup

# import custom packages from the current repository
import libreforms
from app.views.forms import form_menu, checkFormGroup
from app.views.auth import login_required
from app.signing import generate_key
from app.models import Report
from app import config, log, mongodb, mailer, config, db


# and finally, import other packages
import os
from datetime import datetime
import pandas as pd


def get_list_of_users_reports(id=None, db=db):
    with db.engine.connect() as conn:
        return db.session.query(Report).filter(user_id=id).all()


# this method is based heavily on our approach in app.signing.write_key_to_db.
def write_report_to_db(name=None, form_name=None, filters=None, frequency=None, active=1, start_at=None, end_at=None, id=None, db=db, current_user=None):
    
    #  here we are generating a random string to use as the key of the
    # new report... but first we need to verify it doesn't already exist. 
    while True:
        report_id = generate_key(length=config['signing_key_length'])
        if not Report.query.filter_by(report_id=report_id).first(): break
   
    try:
        new_report =  Report(
                        report_id = report_id,
                        user_id = id,
                        name = name,
                        form_name = form_name,
                        filters = filters,
                        frequency = frequency,
                        active = active,
                        timestamp = datetime.timestamp(datetime.now()),
                        start_at = start_at,
                        end_at = end_at,)
 
        db.session.add(new_report)
        db.session.commit()
        log.info(f'{current_user.username.upper()} - successfully generated report {new_report.report_id}: {name}.')

        # we return the report_id after the commit is done. For more on how commits 
        # work and return committed_id, see https://stackoverflow.com/a/4202016/13301284.
        # return new_report.report_id
        return report_id 

    except Exception as e:
        log.warning(f'{current_user.username.upper()} - failed to generate report: {e}.')
        return False


bp = Blueprint('reports', __name__, url_prefix='/reports')

# show list of current reports, and interface to create new ones
@bp.route(f'/', methods=['GET', 'POST'])
@login_required
def reports():

    # generate a list of reports, and render a list of links to these here. 
    # dim those that are inactive

    return render_template('reports/reports_home.html', 
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            name="Reports",
            type="reports",
            config=config,
            user=current_user,
            menu=form_menu(checkFormGroup),
        ) 



@bp.route(f'/<form_name>/create', methods=['GET', 'POST'])
@login_required
def create_reports(form_name):

    if form_name not in libreforms.forms.keys():
        return abort(404)


    if request.method == 'POST':
        # print(request.form)
        user_id = current_user.get_id()
        name = request.form['name']
        filters = request.form['filters'] 
        frequency = request.form['frequency'] 
        start_at = datetime.strptime(request.form['start_at'], "%Y-%m-%d").timestamp() if request.form['start_at'] != '' else 0
        end_at = datetime.strptime(request.form['end_at'], "%Y-%m-%d").timestamp() if request.form['end_at'] != '' else 0
        

        report_id = write_report_to_db( name=name, 
                                        form_name=form_name, 
                                        filters=filters, frequency=frequency, 
                                        active=1, start_at=start_at, end_at=end_at, 
                                        id=user_id, current_user=current_user)
        
        # print(report_id)

        return redirect(url_for('reports.view_report', report_id=str(report_id)))

    return render_template('reports/create_report.html', 
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            name=f"Create {form_name} report",
            type="reports",
            config=config,
            user=current_user,
            menu=form_menu(checkFormGroup),
        ) 



@bp.route(f'/<report_id>', methods=['GET', 'POST'])
@login_required
def view_report(report_id):
    return report_id


@bp.route(f'/<report_id>/activate', methods=['GET', 'POST'])
@login_required
def activate_report(report_id):
    pass # activate existing report


@bp.route(f'/<report_id>/deactivate', methods=['GET', 'POST'])
@login_required
def deactivate_report(report_id):
    pass # deactivate existing report

@bp.route(f'/<report_id>/send', methods=['GET', 'POST'])
@login_required
def send_report(report_id):
    pass # send existing report now

