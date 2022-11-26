
# import flask-related packages
from flask import Blueprint, g, flash, abort, render_template, \
    request, send_from_directory, send_file, redirect, url_for
from webargs import fields, flaskparser
from flask_login import current_user

# import custom packages from the current repository
import libreforms
from app import display, log, tempfile_path, db, mailer, mongodb
from app.models import User
from app.auth import login_required, session


# and finally, import other packages
import os
import pandas as pd


def get_record_of_submissions(form_name=None, user=None):
    if form_name:
        data = mongodb.read_documents_from_collection(form_name)
        df = pd.DataFrame(list(data))

        # set ID to string instead of object ID
        df['_id'] = df['_id'].astype(str)
        df.rename(columns = {'_id':'id'}, inplace = True)

        # set the document id as the index
        # df.set_index('_id')

        # if len(df.index) < 1:
            # flash('This form has not received any submissions.')
            # return redirect(url_for('tables.tables_home'))
            # return None

        # df.drop(columns=["_id"], inplace=True)
        
        # here we allow the user to select fields they want to use, 
        # overriding the default view-all.
        # warning, this may be buggy

        if user:
            df = df.loc[df['Reporter'] == user]

        df.columns = [x.replace("_", " ") for x in df.columns]

        return df

    return pd.DataFrame()


def aggregate_form_data():
    pass

bp = Blueprint('submissions', __name__, url_prefix='/submissions')


@bp.route('/<form_name>/all')
@login_required
def render_all_submissions(form_name):
    pass


# this is kind of like the home page for a given form
@bp.route('/<form_name>')
@login_required
def render_submissions_for_form(form_name):
    pass


# @bp.route('/<user>')
# @login_required
# def render_user_submissions(user):
#     if user == current_user:
#         pass

#     else:
#         abort(404)


@bp.route('/<form_name>/<document_id>')
@login_required
def render_document(form_name, document_id):
    record = get_record_of_submissions(form_name=form_name, user=current_user.username)

    try:
        record = record.loc[record['id'] == str(document_id)]


        return render_template('app/submissions.html',
            type="submissions",
            name=form_name,
            submission=record,
            display=display,
            user=current_user,
        )
    except:
        abort(404)