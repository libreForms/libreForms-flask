# import flask-related packages
from flask import Blueprint, render_template, request
from flask_login import current_user
from markupsafe import Markup

# import custom packages from the current repository
import libreforms as libreforms
import mongodb
from app.auth import login_required
from app.forms import parse_options
from app import display, log

# and finally, import other packages
import os
import pandas as pd


# read database password file, if it exists
if os.path.exists ("mongodb_pw"):
    with open("mongodb_pw", "r+") as f:
        mongodb_pw = f.read().strip()
else:  
    mongodb_pw=None


# initialize mongodb database
mongodb = mongodb.MongoDB(mongodb_pw)


bp = Blueprint('tables', __name__, url_prefix='/tables')


@bp.route(f'/')
@login_required
def tables_home():
    return render_template('app/tables.html', 
            msg="Select a table from the left-hand menu.",
            name="Table",
            type="tables",
            menu=[x for x in libreforms.forms.keys()],
            display=display,
            user=current_user,
        ) 

# this creates the route to each of the tables
@bp.route(f'/<form_name>', methods=['GET', 'POST'])
@login_required
def tables(form_name): 

    try:
        pd.set_option('display.max_colwidth', 0)
        data = mongodb.read_documents_from_collection(form_name)
        df = pd.DataFrame(list(data))

        if len(df.index) < 1:
            return render_template('app/tables.html', 
                form_not_found=True,
                msg="This form has not received any submissions.",
                name="404",
                type="tables",
                menu=[x for x in libreforms.forms.keys()],
                display=display,
                user=current_user,
            )

        df.drop(columns=["_id"], inplace=True)
        
        # here we allow the user to select fields they want to use, 
        # overriding the default view-all.
        # warning, this may be buggy

        for col in df.columns:
            if request.args.get(col):
                # prevent type-mismatch by casting both fields as strings
                df = df.loc[df[col].astype("string") == str(request.args.get(col))] 

        df.columns = [x.replace("_", " ") for x in df.columns]
    except Exception as e:
        df = pd.DataFrame(columns=["Error"], data=[{"Error":e}])

    return render_template('app/tables.html',
        table=Markup(df.to_html(index=False)),
        type="tables",
        name=form_name,
        is_table=True,
        options=parse_options(form=form_name),
        menu=[x for x in libreforms.forms.keys()],
        display=display,
        user=current_user,
    )