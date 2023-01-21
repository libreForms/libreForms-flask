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
from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user
from markupsafe import Markup

# import custom packages from the current repository
import libreforms
from app.views.forms import form_menu
from app.views.auth import login_required
from app.models import Report
from app import config, log, mongodb, mailer, config, db


# and finally, import other packages
import os
from datetime import datetime
import pandas as pd


def get_list_of_reports(id=current_user.id, db=db):
    with db.engine.connect() as conn:
        return db.session.query(Report).filter(user_id=id).all()


# this method is based heavily on our approach in app.signing.write_key_to_db.
def write_report_to_db(name=None, filters=None, frequency=None, active=1, start_at=None, end_at=None, id=current_user.id, db=db, current_user=current_user):
    try:
        new_report =  Report(
            user_id = id,
            name = name,
            filters = filters,
            frequency = frequency,
            active = active,
            timestamp = datetime.datetime.timestamp(datetime.datetime.now()),
            start_at = start_at,
            end_at = end_at,)

        db.session.add(new_report)
        db.session.commit()
        log.info(f'{current_user.username.upper()} - successfully generated report: {name}.')

        return True

    except Exception as e:
        log.warning(f'{current_user.username.upper()} - failed to generate report: {e}.')
        return False


bp = Blueprint('reports', __name__, url_prefix='/reports')

# show list of current reports, and interface to create new ones
@bp.route(f'/', methods=['GET', 'POST'])
@login_required
def reports_home():

    # generate a list of reports, and render a list of links to these here. 
    # dim those that are inactive

    return render_template('reports/reports_home.html', 
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            name="Reports",
            type="reports",
            config=config,
            user=current_user,
        ) 



@bp.route(f'/create', methods=['GET', 'POST'])
@login_required
def create_reports():
    pass # create a new report

@bp.route(f'/<report_id>', methods=['GET', 'POST'])
@login_required
def manage_reports(report_id):
    pass # modify existing report


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

