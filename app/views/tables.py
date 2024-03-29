""" 
tables.py: implementation of views for table-views of forms



"""

__name__ = "app.views.tables"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.2.0"
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
from app.views.forms import propagate_form_configs, checkGroup, checkTableGroup, form_menu, standard_view_kwargs
from app.views.submissions import set_digital_signature
from app.models import User
from app import config, log, mongodb, db
from app.decorators import required_login_and_password_reset


# and finally, import other packages
import os
import pandas as pd

# pd.set_option('display.max_colwidth', 30)

bp = Blueprint('tables', __name__, url_prefix='/tables')


@bp.route(f'/')
@required_login_and_password_reset
def tables_home():
    return render_template('app/tables.html.jinja', 
            msg="Select a table from the left-hand menu.",
            name='Tables',
            subtitle="Home",
            type="tables",
            menu=form_menu(checkTableGroup),
            **standard_view_kwargs(),
        ) 

# this creates the route to each of the tables
@bp.route(f'/<form_name>', methods=['GET', 'POST'])
@required_login_and_password_reset
def tables(form_name): 

    if form_name not in libreforms.forms.keys():
        flash('This form does not exist.', "warning")
        return redirect(url_for('tables.tables_home'))

    if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)['_table']):
        flash(f'You do not have access to this dashboard.', "warning")
        return redirect(url_for('tables.tables_home'))


    try:
        data = mongodb.read_documents_from_collection(form_name)
        df = pd.DataFrame(list(data))

        # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
        if mongodb.metadata_field_names['signature'] in df.columns:
            if propagate_form_configs(form_name)['_digitally_sign']:
                df[mongodb.metadata_field_names['signature']] = df.apply(lambda row: set_digital_signature(username=row[mongodb.metadata_field_names['owner']],encrypted_string=row[mongodb.metadata_field_names['signature']],
                    base_string=config['signature_key'],
                    return_markup=False), axis=1)
            else:
                df.drop(columns=[mongodb.metadata_field_names['signature']], inplace=True)
                

        if all(x in df.columns for x in [mongodb.metadata_field_names['approval'],mongodb.metadata_field_names['approver'], mongodb.metadata_field_names['approver_comment']]):
            if propagate_form_configs(form_name)['_digitally_sign']:


                df[mongodb.metadata_field_names['approval']] = df.apply(lambda row: set_digital_signature(
                    username= db.session.query(User).filter(getattr(User, config['visible_signature_field'])==row[mongodb.metadata_field_names['approver']]).first(),
                    encrypted_string=row[mongodb.metadata_field_names['signature']],
                    base_string=config['approval_key'],
                    fallback_string=config['disapproval_key'],
                    return_markup=False), axis=1)
            else:
                df.drop(columns=[mongodb.metadata_field_names['approval'],mongodb.metadata_field_names['approver'], mongodb.metadata_field_names['approver_comment']], inplace=True)
        else:
            [ df.drop(columns=[x], inplace=True) for x in [mongodb.metadata_field_names['approval'],mongodb.metadata_field_names['approver'], mongodb.metadata_field_names['approver_comment']] if x in df.columns]



        if len(df.index) < 1:
            flash('This form has not received any submissions.', "warning")
            return redirect(url_for('tables.tables_home'))

        # prior to dropping the metadata fields, we generate hyperlinks to each individual
        # form, see https://github.com/libreForms/libreForms-flask/issues/243. Luckily, we
        # don't need to deal with submissions.gen_hyperlink because pandas dataframes allow
        # you to render links when you generate the table as html using render_link, see
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_html.html. 
        # df['Hyperlink'] = df.apply(lambda row: f"{config['domain']}/submissions/{form_name}/{row._id}", axis=1)
        df['Hyperlink'] = df.apply(lambda row: config['domain']+url_for('submissions.render_document', form_name=form_name, document_id=row['_id']), axis=1)


        # drop `meta` fields from user vis
        # [ df.drop(columns=[x], inplace=True) for x in [mongodb.metadata_field_names['journal'], mongodb.metadata_field_names['metadata'], '_id'] if x in df.columns]
        [ df.drop(columns=[x], inplace=True) for x in mongodb.metadata_fields(exclude_id=True, ignore_fields=['owner', 'reporter', 'timestamp',]) if x in df.columns]

        # here we allow the user to select fields they want to use, 
        # overriding the default view-all.
        # warning, this may be buggy

        for col in df.columns:
            if request.args.get(col):
                # prevent type-mismatch by casting both fields as strings
                df = df.loc[df[col].astype("string") == str(request.args.get(col))] 

        # sort values using timestamp field (last edit time) by default, newest
        # on top, see https://github.com/libreForms/libreForms-flask/issues/336.
        df.sort_values(by=mongodb.metadata_field_names['timestamp'], inplace=True, ignore_index=True, ascending=False)

        df.columns = [x.replace("_", " ") for x in df.columns]

    except Exception as e: 
        # log.warning(f"LIBREFORMS - {e}")
        # flash(f'This form does not exist. {e}', "warning")
        transaction_id = str(uuid.uuid1())
        log.warning(f"{current_user.username.upper()} - {e}", extra={'transaction_id': transaction_id})
        flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ", 'warning')

        return redirect(url_for('tables.tables_home'))
    

    def clip_string(s):
        if isinstance(s, str) and len(s) > 150:
            return s[:150] + "..."
        else:
            return s

    df = df.applymap(clip_string)

    print(df.columns)


    return render_template('app/tables.html.jinja',
        table=df,
        type="tables",
        name='Tables',
        subtitle=form_name,
        is_table=True,
        options=propagate_form_configs(form=form_name),
        menu=form_menu(checkTableGroup),
        filename=f'{form_name.lower().replace(" ","")}.csv', #if propagate_form_configs(form_name)['_allow_csv_templates'] else False,
        **standard_view_kwargs(),
    )


# this is the download link for files in the temp directory
@bp.route('/download/<path:filename>')
@required_login_and_password_reset
def download_file(filename):

    form_name = filename.replace('.csv', '')

    if form_name not in libreforms.forms.keys():
        flash('This form does not exist.', "warning")
        return redirect(url_for('tables.tables_home'))

    if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)['_table']):
        flash(f'You do not have access to this dashboard.', "warning")
        return redirect(url_for('tables.tables_home'))


    try:
        data = mongodb.read_documents_from_collection(form_name)
        df = pd.DataFrame(list(data))

        # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
        if mongodb.metadata_field_names['signature'] in df.columns:
            if propagate_form_configs(form_name)['_digitally_sign']:
                df[mongodb.metadata_field_names['signature']] = df.apply(lambda row: set_digital_signature(username=row[mongodb.metadata_field_names['owner']],encrypted_string=row[mongodb.metadata_field_names['signature']],
                base_string=config['signature_key'],
                return_markup=False), axis=1)

            else:
                df.drop(columns=[mongodb.metadata_field_names['signature']], inplace=True)

        if all(x in df.columns for x in [mongodb.metadata_field_names['approval'],mongodb.metadata_field_names['approver'], mongodb.metadata_field_names['approver_comment']]):
            if propagate_form_configs(form_name)['_digitally_sign']:


                df[mongodb.metadata_field_names['approval']] = df.apply(lambda row: set_digital_signature(
                    username= db.session.query(User).filter(getattr(User, config['visible_signature_field'])==row[mongodb.metadata_field_names['approver']]).first(),
                    encrypted_string=row[mongodb.metadata_field_names['signature']],
                    base_string=config['approval_key'],
                    fallback_string=config['disapproval_key'],
                    return_markup=False), axis=1)
            else:
                df.drop(columns=[mongodb.metadata_field_names['approval'], mongodb.metadata_field_names['approver'], mongodb.metadata_field_names['approver_comment']], inplace=True)
        else:
            [ df.drop(columns=[x], inplace=True) for x in [mongodb.metadata_field_names['approval'], mongodb.metadata_field_names['approver'], mongodb.metadata_field_names['approver_comment']] if x in df.columns]

        if len(df.index) < 1:
            flash('This form has not received any submissions.', "warning")
            return redirect(url_for('tables.tables_home'))


        [ df.drop(columns=[x], inplace=True) for x in [mongodb.metadata_field_names['journal'], mongodb.metadata_field_names['metadata'], '_id'] if x in df.columns]
        
        # here we allow the user to select fields they want to use, 
        # overriding the default view-all.
        # warning, this may be buggy

        for col in df.columns:
            if request.args.get(col):
                # prevent type-mismatch by casting both fields as strings
                df = df.loc[df[col].astype("string") == str(request.args.get(col))] 

        df.columns = [x.replace("_", " ") for x in df.columns]
    except Exception as e: 
        # log.warning(f"LIBREFORMS - {e}")
        # flash(f'This form does not exist. {e}', "warning")
        transaction_id = str(uuid.uuid1())
        log.warning(f"{current_user.username.upper()} - {e}", extra={'transaction_id': transaction_id})
        flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ", 'warning')

        return redirect(url_for('tables.tables_home'))

    # here we employ a context-bound temp directory to stage this file for download, see
    # discussion in app.tmpfiles and https://github.com/signebedi/libreForms/issues/169.
    from app.tmpfiles import temporary_directory
    with temporary_directory() as tempfile_path:

        fp = os.path.join(tempfile_path, filename)
        df.to_csv(fp, index=False)

        return send_from_directory(tempfile_path,
                                filename, as_attachment=True)