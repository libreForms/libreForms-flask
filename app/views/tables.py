""" 
tables.py: implementation of views for table-views of forms



"""

__name__ = "app.views.tables"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


# import flask-related packages
from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for, send_from_directory
from flask_login import current_user
from markupsafe import Markup

# import custom packages from the current repository
import libreforms as libreforms
from app.views.auth import login_required
from app.views.forms import propagate_form_configs, checkGroup, checkTableGroup, form_menu
from app.views.submissions import set_digital_signature
from app import config, log, mongodb



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
            config=config,
            user=current_user,
        ) 

# this creates the route to each of the tables
@bp.route(f'/<form_name>', methods=['GET', 'POST'])
@login_required
def tables(form_name): 

    if form_name not in libreforms.forms.keys():
        flash('This form does not exist.')
        return redirect(url_for('tables.tables_home'))

    if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)['_table']):
        flash(f'You do not have access to this dashboard.')
        return redirect(url_for('tables.tables_home'))


    try:
        data = mongodb.read_documents_from_collection(form_name)
        df = pd.DataFrame(list(data))

        # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
        if 'Signature' in df.columns:
            if propagate_form_configs(form_name)['_digitally_sign']:
                df['Signature'] = df.apply(lambda row: set_digital_signature(username=row['Owner'],encrypted_string=row['Signature'],return_markup=False), axis=1)
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


    return render_template('app/tables.html',
        table=Markup(df.to_html(index=False, classes=f"table {'text-dark' if not (config['dark_mode'] or current_user.theme == 'dark') else ''}")),
        # table=df,
        type="tables",
        name=form_name,
        is_table=True,
        notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
        options=propagate_form_configs(form=form_name),
        menu=form_menu(checkTableGroup),
        config=config,
        filename=f'{form_name.lower().replace(" ","")}.csv', #if propagate_form_configs(form_name)['_allow_csv_templates'] else False,
        user=current_user,
    )


# this is the download link for files in the temp directory
@bp.route('/download/<path:filename>')
@login_required
def download_file(filename):

    form_name = filename.replace('.csv', '')

    if form_name not in libreforms.forms.keys():
        flash('This form does not exist.')
        return redirect(url_for('tables.tables_home'))

    if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)['_table']):
        flash(f'You do not have access to this dashboard.')
        return redirect(url_for('tables.tables_home'))


    try:
        data = mongodb.read_documents_from_collection(form_name)
        df = pd.DataFrame(list(data))

        # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
        if 'Signature' in df.columns:
            if propagate_form_configs(form_name)['_digitally_sign']:
                df['Signature'] = df.apply(lambda row: set_digital_signature(username=row['Owner'],encrypted_string=row['Signature'],return_markup=False), axis=1)
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

    # here we employ a context-bound temp directory to stage this file for download, see
    # discussion in app.tmpfiles and https://github.com/signebedi/libreForms/issues/169.
    from app.tmpfiles import temporary_directory
    with temporary_directory() as tempfile_path:

        fp = os.path.join(tempfile_path, filename)
        df.to_csv(fp, index=False)

        return send_from_directory(tempfile_path,
                                filename, as_attachment=True)




            # data = mongodb.read_documents_from_collection(form_name)
            # df = pd.DataFrame(list(data))
            # df.drop(columns=["_id"], inplace=True)
            
            # # here we allow the user to select fields they want to use, 
            # # overriding the default view-all.
            # # warning, this may be buggy

            # for col in df.columns:
            #     if request.args.get(col):
            #         # prevent type-mismatch by casting both fields as strings
            #         df = df.loc[df[col].astype("string") == str(request.args.get(col))] 
