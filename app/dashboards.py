# import flask-related packages
from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_login import current_user

# import custom packages from the current repository
import libreforms
from app.auth import login_required
from app.forms import parse_options, checkGroup, checkDashboardGroup, form_menu
from app import display, log, mongodb

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
            type="dashboards",
            menu=form_menu(checkDashboardGroup),
            display=display,
            user=current_user,
        ) 


# this creates the route to each of the dashboards
@bp.route(f'/<form_name>')
@login_required
def dashboards(form_name):

    if form_name not in libreforms.forms.keys():
        flash('This form does not exist.')
        return redirect(url_for('dashboards.dashboards_home'))

    if not checkGroup(group=current_user.group, struct=parse_options(form_name)['_dashboard']):
        flash(f'You do not have access to this dashboard.')
        return redirect(url_for('dashboards.dashboards_home'))

    if parse_options(form=form_name)["_dashboard"] == False:
        flash('Your system administrator has not enabled any dashboards for this form.')
        return redirect(url_for('dashboards.dashboards_home'))

    
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

    viz_type = libreforms.forms[form_name]["_dashboard"]['type']
    if viz_type == "scatter":
        fig = px.scatter(df, 
                    x=ref['x'], 
                    y=y_context, 
                    color=ref['color'],
                    template='plotly_dark')
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
        site_name=display['site_name'],
        menu=form_menu(checkDashboardGroup),
        options=parse_options(form=form_name),
        display=display,
        user=current_user,
    )





