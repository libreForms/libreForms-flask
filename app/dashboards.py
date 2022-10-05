# import flask-related packages
from flask import Blueprint, render_template, request
from flask_login import current_user

# import custom packages from the current repository
import libreforms
import mongodb
from app.auth import login_required
from app.forms import parse_options
from app import display, log

# and finally, import other packages
import os, json
import plotly
import plotly.express as px
import pandas as pd



# read database password file, if it exists
if os.path.exists ("mongodb_creds"):
    with open("mongodb_creds", "r+") as f:
        mongodb_creds = f.read().strip()
else:  
    mongodb_creds=None
# initialize mongodb database
mongodb = mongodb.MongoDB(mongodb_creds)


bp = Blueprint('dashboards', __name__, url_prefix='/dashboards')

# define a home route
@bp.route('/')
@login_required
def dashboards_home():
    return render_template('app/dashboards.html', 
            msg="Select a dashboard from the left-hand menu.",
            name="Dashboard",
            type="dashboards",
            menu=[x for x in libreforms.forms.keys()],
            display=display,
            user=current_user,
        ) 


# this creates the route to each of the dashboards
@bp.route(f'/<form_name>')
@login_required
def dashboards(form_name):

    if form_name not in libreforms.forms.keys():
        return render_template('app/dashboards.html', 
            form_not_found=True,
            msg="",
            name="404",
            type="dashboards",
            menu=[x for x in libreforms.forms.keys()],
            display=display,
            user=current_user,
        )



    if parse_options(form=form_name)["_dashboard"] == False:
        return render_template('app/dashboards.html', 
            form_not_found=True,
            msg="No dashboard has been configured for this form.",
            name="404",
            type="dashboards",
            menu=[x for x in libreforms.forms.keys()],
            display=display,
            user=current_user,
        )

    
    data = mongodb.read_documents_from_collection(form_name)
    df = pd.DataFrame(list(data))
    ref = libreforms.forms[form_name]["_dashboard"]['fields']

    # here we allow the user to specify the field they want to use, 
    # overriding the default y-axis field defined in libreforms/forms.
    # warning, this may be buggy

    # if request.args.get("y") and request.args.get("y") in form.keys(): # alternative if we want to verify the field exists
    y_context = request.args.get("y") if request.args.get("y") else ref['y']


    if len(df.index) < 1:
        return render_template('app/dashboards.html', 
            form_not_found=True,
            msg="This form has not received any submissions.",
            name="404",
            type="dashboards",
            menu=[x for x in libreforms.forms.keys()],
            display=display,
            user=current_user,
        )

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
        menu=[x for x in libreforms.forms.keys()],
        options=parse_options(form=form_name),
        display=display,
        user=current_user,
    )





