""" 
dashboards.py: implementation of views for dashboard rendering of forms



"""

__name__ = "app.views.dashboards"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.0.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# import flask-related packages
from flask import current_app, Blueprint, render_template, request, redirect, flash, url_for
from flask_login import current_user

# import custom packages from the current repository
import libreforms
from app.views.auth import login_required
from app.views.forms import propagate_form_configs, checkGroup, checkDashboardGroup, form_menu, standard_view_kwargs
from app import config, log, mongodb
from app.models import db



# and finally, import other packages
import os, json, uuid, types
import plotly
import plotly.express as px
import pandas as pd



bp = Blueprint('dashboards', __name__, url_prefix='/dashboards')

# define a home route
@bp.route('/')
@login_required
def dashboards_home():
    return render_template('app/dashboards.html.jinja', 
            msg="Select a dashboard from the left-hand menu.",
            name='Dashboards',
            subtitle='Home',
            type="dashboards",
            menu=form_menu(checkDashboardGroup),
            **standard_view_kwargs(),
        ) 


# this creates the route to each of the dashboards
@bp.route(f'/<form_name>')
@login_required
def dashboards(form_name):

    if form_name not in libreforms.forms.keys():
        flash('This form does not exist.', "warning")
        return redirect(url_for('dashboards.dashboards_home'))

    if '_dashboard' not in libreforms.forms[form_name].keys():
        flash('Your system administrator has not enabled any dashboards for this form.', "info")
        return redirect(url_for('dashboards.dashboards_home'))

    # if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)['_dashboard']):
    #     flash(f'You do not have access to this dashboard.', "info")
    #     return redirect(url_for('dashboards.dashboards_home'))

    if propagate_form_configs(form=form_name)["_dashboard"] == False:
        flash('Your system administrator has not enabled any dashboards for this form.', "info")
        return redirect(url_for('dashboards.dashboards_home'))

    try:

        data = mongodb.read_documents_from_collection(form_name)
        df = pd.DataFrame(list(data))

        graphJSON = [] # here we create the list of figures we'll pass to the jinja template later
        all_dashboard_data = ref = libreforms.forms[form_name]["_dashboard"]

        # list-ify the dashboard passed, if it just a single dict, per 
        # https://github.com/libreForms/libreForms-flask/issues/409
        if isinstance(all_dashboard_data, dict):
            all_dashboard_data = [all_dashboard_data]

        for dashboard_data in all_dashboard_data:

            if not checkGroup(group=current_user.group, struct=dashboard_data):
                continue


            ref = dashboard_data['fields']
            viz_type = dashboard_data['type']

            # here we allow the user to specify the field they want to use, 
            # overriding the default y-axis field defined in libreforms/forms.
            # warning, this may be buggy

            # if request.args.get("y") and request.args.get("y") in form.keys(): # alternative if we want to verify the field exists
            # y_context = request.args.get("y") if request.args.get("y") else ref['y']

            if request.args.get("y") and viz_type != "bootstrap":
                y_context = request.args.get("y")
            # elif not isinstance(ref, types.FunctionType):
            elif viz_type == "bootstrap":
                pass
            else:
                y_context = ref['y']


            if len(df.index) < 1:
                flash('This form has not received any submissions.', "warning")
                return redirect(url_for('dashboards.dashboards_home'))

            theme = 'plotly_dark' if (config['dark_mode'] and \
                not current_user.theme == 'light') or current_user.theme == 'dark' else 'plotly_white'

            if viz_type == "scatter":
                fig = px.scatter(df, 
                            x=ref['x'], 
                            y=y_context, 
                            color=ref['color'],
                            template=theme)
                graphJSON.append(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

            elif viz_type == "bar":
                fig = px.histogram(df, 
                            x=ref['x'], 
                            y=y_context, 
                            barmode='group',
                            color=ref['color'],
                            template='plotly_dark')
                graphJSON.append(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

            elif viz_type == "histogram":
                fig = px.histogram(df, 
                            x=ref['x'], 
                            y=y_context, 
                            color=ref['color'],
                            template='plotly_dark')
                graphJSON.append(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))
            elif viz_type == "bootstrap":
                # we expect the `fields` sub-field (which is referenced as `ref` above) to store a callable that
                # returns a plotly object as json, see https://github.com/libreForms/libreForms-flask/issues/410
                graphJSON.append(ref(df)) 

            elif viz_type == "table":
                passref

            else: # default to line graph
                fig = px.line(df, 
                            x=ref['x'], 
                            y=y_context, 
                            color=ref['color'],
                            template='plotly_dark')
                graphJSON.append(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))


        return render_template('app/dashboards.html.jinja', 
            graphJSON=graphJSON,
            name='Dashboards',
            subtitle=form_name,
            type="dashboards",
            menu=form_menu(checkDashboardGroup),
            options=propagate_form_configs(form=form_name),
            **standard_view_kwargs(),
        )

    except Exception as e: 
        
        transaction_id = str(uuid.uuid1())
        log.warning(f"LIBREFORMS - {e}", extra={'transaction_id': transaction_id})
        flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ", 'warning')
        
        return redirect(url_for('dashboards.dashboards_home'))
