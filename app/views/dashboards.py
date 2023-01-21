""" 
dashboards.py: implementation of views for dashboard rendering of forms



"""

__name__ = "app.views.dashboards"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.3.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# import flask-related packages
from flask import current_app, Blueprint, render_template, request, redirect, flash, url_for
from flask_login import current_user

# import custom packages from the current repository
import libreforms
from app.views.auth import login_required
from app.views.forms import propagate_form_configs, checkGroup, checkDashboardGroup, form_menu
from app import config, log, mongodb
from app.models import db



# and finally, import other packages
import os, json
import plotly
import plotly.express as px
import pandas as pd



bp = Blueprint('dashboards', __name__, url_prefix='/dashboards')

# define a home route
@bp.route('/')
@login_required
def dashboards_home():
    return render_template('app/dashboards.html', 
            msg="Select a dashboard from the left-hand menu.",
            name="Dashboard",
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            type="dashboards",
            menu=form_menu(checkDashboardGroup),
            config=config,
            user=current_user,
        ) 


# this creates the route to each of the dashboards
@bp.route(f'/<form_name>')
@login_required
def dashboards(form_name):

    if form_name not in libreforms.forms.keys():
        flash('This form does not exist.')
        return redirect(url_for('dashboards.dashboards_home'))

    if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)['_dashboard']):
        flash(f'You do not have access to this dashboard.')
        return redirect(url_for('dashboards.dashboards_home'))

    if propagate_form_configs(form=form_name)["_dashboard"] == False:
        flash('Your system administrator has not enabled any dashboards for this form.')
        return redirect(url_for('dashboards.dashboards_home'))

    try:

        data = mongodb.read_documents_from_collection(form_name)
        df = pd.DataFrame(list(data))
        ref = libreforms.forms[form_name]["_dashboard"]['fields']

        # here we allow the user to specify the field they want to use, 
        # overriding the default y-axis field defined in libreforms/forms.
        # warning, this may be buggy

        # if request.args.get("y") and request.args.get("y") in form.keys(): # alternative if we want to verify the field exists
        y_context = request.args.get("y") if request.args.get("y") else ref['y']


        if len(df.index) < 1:
            flash('This form has not received any submissions.')
            return redirect(url_for('dashboards.dashboards_home'))

        theme = 'plotly_dark' if (config['dark_mode'] and \
            not current_user.theme == 'light') or current_user.theme == 'dark' else 'plotly_white'


        viz_type = libreforms.forms[form_name]["_dashboard"]['type']
        if viz_type == "scatter":
            fig = px.scatter(df, 
                        x=ref['x'], 
                        y=y_context, 
                        color=ref['color'],
                        template=theme)
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        elif viz_type == "bar":
            fig = px.histogram(df, 
                        x=ref['x'], 
                        y=y_context, 
                        barmode='group',
                        color=ref['color'],
                        template='plotly_dark')
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        elif viz_type == "histogram":
            fig = px.histogram(df, 
                        x=ref['x'], 
                        y=y_context, 
                        color=ref['color'],
                        template='plotly_dark')
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


        elif viz_type == "table":
            pass

        else: # default to line graph
            fig = px.line(df, 
                        x=ref['x'], 
                        y=y_context, 
                        color=ref['color'],
                        template='plotly_dark')
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


        return render_template('app/dashboards.html', 
            graphJSON=graphJSON,
            name=form_name,
            type="dashboards",
            site_name=config['site_name'],
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            menu=form_menu(checkDashboardGroup),
            options=propagate_form_configs(form=form_name),
            config=config,
            user=current_user,
        )
    except Exception as e: 
        
        log.warning(f"LIBREFORMS - {e}")
        
        flash('This dashboard does not exist.')
        return redirect(url_for('dashboards.dashboards_home'))


