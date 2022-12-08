""" 
tables.py: implementation of views for table-views of forms



"""

__name__ = "app.tables"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.0.1"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


# import flask-related packages
from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user
from markupsafe import Markup

# import custom packages from the current repository
import libreforms as libreforms
from app.auth import login_required
from app.forms import parse_options, checkGroup, checkTableGroup, form_menu
from app.submissions import set_digital_signature
from app import display, log, mongodb



# and finally, import other packages
import os
import pandas as pd

bp = Blueprint('tables', __name__, url_prefix='/tables')


@bp.route(f'/')
@login_required
def tables_home():
    return render_template('app/tables.html', 
            msg="Select a table from the left-hand menu.",
            name="Table",
            type="tables",
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            menu=form_menu(checkTableGroup),
            display=display,
            user=current_user,
        ) 

# this creates the route to each of the tables
@bp.route(f'/<form_name>', methods=['GET', 'POST'])
@login_required
def tables(form_name): 

    if form_name not in libreforms.forms.keys():
        flash('This form does not exist.')
        return redirect(url_for('tables.tables_home'))

    if not checkGroup(group=current_user.group, struct=parse_options(form_name)['_table']):
        flash(f'You do not have access to this dashboard.')
        return redirect(url_for('tables.tables_home'))


    try:
        # pd.set_option('display.max_colwidth', 0)
        data = mongodb.read_documents_from_collection(form_name)
        df = pd.DataFrame(list(data))

        # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
        if 'Signature' in df.columns:
            if parse_options(form_name)['_digitally_sign']:
                df['Signature'] = df.apply(lambda row: set_digital_signature(username=row['Reporter'],encrypted_string=row['Signature'],return_markup=False), axis=1)
            else:
                df.drop(columns=['Signature'], inplace=True)


        if len(df.index) < 1:
            flash('This form has not received any submissions.')
            return redirect(url_for('tables.tables_home'))


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
        flash(f'This form does not exist. {e}')
        return redirect(url_for('tables.tables_home'))


    # set the max column width
    # pd.set_option('display.max_colwidth', 10)


    return render_template('app/tables.html',
        table=Markup(df.to_html(index=False, classes=f"table {'text-dark' if not (display['dark_mode'] or current_user.theme == 'dark') else ''}")),
        # table=df,
        type="tables",
        name=form_name,
        is_table=True,
        notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
        options=parse_options(form=form_name),
        menu=form_menu(checkTableGroup),
        display=display,
        user=current_user,
    )