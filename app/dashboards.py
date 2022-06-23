from flask import Flask, Blueprint, g, flash, render_template, url_for, request, redirect, jsonify, session
import os, re, datetime, json, functools
import plotly
import plotly.express as px
import pandas as pd
import libreforms as form_src
import mongodb
from webargs import fields, flaskparser, ValidationError
from pymongo import MongoClient
from app.db import get_db
from app.auth import login_required
from app.forms import parse_form_fields, progagate_forms, parse_options
from app import display

# read database password file, if it exists
if os.path.exists ("mongodb_pw"):
    with open("mongodb_pw", "r+") as f:
        mongodb_pw = f.read().strip()
else:  
    mongodb_pw=None
# initialize mongodb database
mongodb = mongodb.MongoDB(mongodb_pw)


bp = Blueprint('dashboards', __name__, url_prefix='/dashboards')

# define a home route
@bp.route('/')
@login_required
def dashboards_home():
    return render_template('app/index.html', 
            homepage_msg="Select a dashboard from the left-hand menu.",
            name="Dashboard",
            type="dashboards.dashboards",
            menu=[x for x in form_src.forms.keys()],
            display=display,
        ) 


# this creates the route to each of the dashboards
@bp.route(f'/dashboards/<form_name>')
@login_required
def dashboards(form_name):

    if form_name not in form_src.forms.keys():
        return render_template('app/index.html', 
            form_not_found=True,
            msg="",
            name="404",
            type="dashboards.dashboards",
            menu=[x for x in form_src.forms.keys()],
            display=display,
        )



    if parse_options(form=form_name)["_dashboard"] == False:
        return render_template('app/index.html', 
            form_not_found=True,
            msg="No dashboard has been configured for this form.",
            name="404",
            type="dashboards.dashboards",
            menu=[x for x in form_src.forms.keys()],
            display=display,
        )

    
    data = mongodb.read_documents_from_collection(form_name)
    df = pd.DataFrame(list(data))
    ref = form_src.forms[form_name]["_dashboard"]['fields']

    # here we allow the user to specify the field they want to use, 
    # overriding the default y-axis field defined in libreforms/forms.
    # warning, this may be buggy

    # if request.args.get("y") and request.args.get("y") in form.keys(): # alternative if we want to verify the field exists
    y_context = request.args.get("y") if request.args.get("y") else ref['y']

    fig = px.line(df, 
                x=ref['x'], 
                y=y_context, 
                color=ref['color'])
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('app/index.html', 
        graphJSON=graphJSON,
        name=form_name,
        type="dashboards.dashboards",
        site_name=display['site_name'],
        menu=[x for x in form_src.forms.keys()],
        options=parse_options(form=form_name),
        display=display,
    )





