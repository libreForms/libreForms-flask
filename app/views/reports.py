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


def get_list_of_users_reports(id=None, db=db, **kwargs):
    with db.engine.connect() as conn:
        return db.session.query(Report).filter_by(user_id=id,**kwargs).all()


# this method is based heavily on our approach in app.signing.write_key_to_db.
def write_report_to_db(name=None, form_name=None, filters=None, frequency=None, active=1, 
                        start_at_human_readable=None, end_at_human_readable=None, 
                        start_at=None, end_at=None, id=None, db=db, current_user=None):
    
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
                        timestamp_human_readable = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                        start_at = start_at,
                        end_at = end_at,
                        start_at_human_readable=start_at_human_readable,
                        end_at_human_readable=end_at_human_readable,)
 
        db.session.add(new_report)
        db.session.commit()
        log.info(f'{current_user.username.upper()} - successfully generated report {new_report.report_id}: {name}.')

        # we return the report_id after the commit is done. For more on how commits 
        # work and return committed_id, see https://stackoverflow.com/a/4202016/13301284.
        # return new_report.report_id
        return report_id 

    except Exception as e:
        flash(f'Could not create report. {e} ')
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
        start_at_human_readable = request.form['start_at'] if request.form['start_at'] else datetime.now().strftime("%Y-%m-%d")
        end_at_human_readable = request.form['end_at'] if request.form['end_at'] else ''
        start_at = datetime.strptime(request.form['start_at'], "%Y-%m-%d").timestamp() if request.form['start_at'] != '' else datetime.timestamp(datetime.now())
        end_at = datetime.strptime(request.form['end_at'], "%Y-%m-%d").timestamp() if request.form['end_at'] != '' else 0
        

        report_id = write_report_to_db( name=name, 
                                        form_name=form_name, 
                                        filters=filters, frequency=frequency,
                                        start_at_human_readable=start_at_human_readable,
                                        end_at_human_readable=end_at_human_readable, 
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


@bp.route(f'/modify/<report_id>', methods=['GET', 'POST'])
@login_required
def modify_report(report_id):

    # here we collect the user's reports but introduce the kwarg report_id to 
    # ensure we are only querying for the current report_id
    reports = get_list_of_users_reports(id=current_user.id, report_id=report_id)
    # print(reports)

    # then, we assert that the length of of the list this generates is greater than 
    # one, or else return a 404 - as there is no record for this report.
    if len(reports) < 1:
        return abort(404)

    report = reports[0]
    
    if request.method == 'POST':
        # print(request.form)
        user_id = current_user.get_id()
        name = request.form['name']
        filters = request.form['filters'] 
        frequency = request.form['frequency'] 
        start_at_human_readable = request.form['start_at'] if request.form['start_at'] else datetime.now().strftime("%Y-%m-%d")
        end_at_human_readable = request.form['end_at'] if request.form['end_at'] else ''
        start_at = datetime.strptime(request.form['start_at'], "%Y-%m-%d").timestamp() if request.form['start_at'] != '' else datetime.timestamp(datetime.now())
        end_at = datetime.strptime(request.form['end_at'], "%Y-%m-%d").timestamp() if request.form['end_at'] != '' else 0

    
        try:

            # we update the values before committing them
            report.name = name 
            report.filters = filters 
            report.frequency = frequency 
            report.start_at = start_at 
            report.end_at = end_at 
            report.start_at_human_readable = start_at_human_readable 
            report.end_at_human_readable = end_at_human_readable 
            report.timestamp_human_readable = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") 
            report.timestamp = datetime.timestamp(datetime.now()) 


            db.session.commit()

            log.info(f'{current_user.username.upper()} - successfully modified report {report.report_id}: {name}.')

        except Exception as e:
            flash(f'Could not modify report. {e} ')
            log.warning(f'{current_user.username.upper()} - failed to update report {report.report_id}: {e}.')

        return redirect(url_for('reports.view_report', report_id=str(report_id)))


    # now we render the create_report template, but pass the report object,
    # which will be used to populate the fields with their previous values
    return render_template('reports/create_report.html', 
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            name=f"Modify report",
            type="reports",
            config=config,
            user=current_user,
            report=report,
            menu=form_menu(checkFormGroup),
        ) 




@bp.route(f'/view/<report_id>', methods=['GET', 'POST'])
@login_required
def view_report(report_id):

    # here we collect the user's reports but introduce the kwarg report_id to 
    # ensure we are only querying for the current report_id
    reports = get_list_of_users_reports(id=current_user.id, report_id=report_id)
    # print(reports)

    # then, we assert that the length of of the list this generates is greater than 
    # one, or else return a 404 - as there is no record for this report.
    if len(reports) < 1:
        return abort(404)

    report = reports[0]

    # print(Report.__table__.columns)

    # now we render the view_report template, but pass the report object,
    # which will be used to populate the fields with their proper values
    return render_template('reports/view_report.html', 
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            name=f"View Report",
            type="reports",
            config=config,
            user=current_user,
            report=report,
            menu=form_menu(checkFormGroup),
        ) 

@bp.route(f'/activate/<report_id>', methods=['GET', 'POST'])
@login_required
def activate_report(report_id):
    # here we collect the user's reports but introduce the kwarg report_id to 
    # ensure we are only querying for the current report_id
    reports = get_list_of_users_reports(id=current_user.id, report_id=report_id)
    # print(reports)

    # then, we assert that the length of of the list this generates is greater than 
    # one, or else return a 404 - as there is no record for this report.
    if len(reports) < 1:
        return abort(404)

    report = reports[0]
    
    if report.active == True:
        flash (f'Report is already active. ')
        return redirect(url_for('reports.view_report', report_id=str(report_id)))

    report.active = 1 
    db.session.commit()

    flash (f'Report successfully activated. ')
    return redirect(url_for('reports.view_report', report_id=str(report_id)))


@bp.route(f'/deactivate/<report_id>', methods=['GET', 'POST'])
@login_required
def deactivate_report(report_id):
    # here we collect the user's reports but introduce the kwarg report_id to 
    # ensure we are only querying for the current report_id
    reports = get_list_of_users_reports(id=current_user.id, report_id=report_id)
    # print(reports)

    # then, we assert that the length of of the list this generates is greater than 
    # one, or else return a 404 - as there is no record for this report.
    if len(reports) < 1:
        return abort(404)

    report = reports[0]
    
    if report.active == False:
        flash (f'Report is already inactive. ')
        return redirect(url_for('reports.view_report', report_id=str(report_id)))

    report.active = 0 
    db.session.commit()

    flash (f'Report successfully deactivated. ')
    return redirect(url_for('reports.view_report', report_id=str(report_id)))

@bp.route(f'/<report_id>/send', methods=['GET', 'POST'])
@login_required
def send_report(report_id):
    # here we collect the user's reports but introduce the kwarg report_id to 
    # ensure we are only querying for the current report_id
    reports = get_list_of_users_reports(id=current_user.id, report_id=report_id)
    # print(reports)

    # then, we assert that the length of of the list this generates is greater than 
    # one, or else return a 404 - as there is no record for this report.
    if len(reports) < 1:
        return abort(404)

    report = reports[0]

    # placeholder for app.reporting send_async

    flash (f'Report successfully sent. ')
    return redirect(url_for('reports.view_report', report_id=str(report_id)))
