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

from datetime import datetime
from app import log, mailer, config


# import flask-related packages
from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user
from markupsafe import Markup

# import custom packages from the current repository
import libreforms as libreforms
from app.views.forms import form_menu
from app.views.auth import login_required
from app import config, log, mongodb

# and finally, import other packages
import os
import pandas as pd



bp = Blueprint('reports', __name__, url_prefix='/reports')

# show list of current reports, and interface to create new ones
@bp.route(f'/', methods=['GET', 'POST'])
@login_required
def reports():

    # generate a list of reports, and render a list of links to these here. 
    # dim those that are inactive

    return render_template('app/reports.html', 
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

