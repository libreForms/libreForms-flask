
# import flask-related packages
from flask import Blueprint, g, flash, abort, render_template, \
    request, send_from_directory, send_file, redirect, url_for
from webargs import fields, flaskparser
from flask_login import current_user
from markupsafe import Markup


# import custom packages from the current repository
import libreforms
from app import display, log, tempfile_path, db, mailer, mongodb
from app.models import User
from app.auth import login_required, session
from app.forms import form_menu, checkGroup, checkFormGroup, checkKey, parse_options


# and finally, import other packages
import os
import pandas as pd


def get_record_of_submissions(form_name=None, user=None):
    if form_name:

        try:
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
                try:
                    df = df.loc[df['Reporter'] == user]
                except:
                    log.info(f"{user.upper()} - tried to query {form_name} database for user but no entries were found.")
                    return None

            df.columns = [x.replace("_", " ") for x in df.columns]

            if len(df.index) == 0:
                return None

            return df
        except:
            return None


    return None


def gen_hyperlink(row, form_name):
    # return Markup(f"<p><a href=\"{display['domain']}/submissions/{form_name}/{row.id}\">{form_name}</a></p>")
    return Markup(f"<a href=\"{display['domain']}/submissions/{form_name}/{row.id}\">{display['domain']}/submissions/{form_name}/{row.id}</a>")


# in this method we aggregate all the relevant information
def aggregate_form_data(user=None):

    df = pd.DataFrame(columns=['form', 'Timestamp', 'id', 'hyperlink'])
    collections = mongodb.collections()

    if len(collections) > 0:

        for form in collections:

            if user:
                temp_df = get_record_of_submissions(form, user=user)
            else:
                temp_df = get_record_of_submissions(form)

            if isinstance(temp_df, pd.DataFrame):

                for index, row in temp_df.iterrows():
                    z = pd.Series({'Timestamp':row['Timestamp'], 'form':form, 'id':row['id'], 'hyperlink':gen_hyperlink(row, form),}).to_frame().T
                    df = pd.concat([df, z], ignore_index=True)
                    

    return df if len(df.index)>0 else None



# Right now, each document submission stores a full carbon copy of the initial submission in 
# the `Journal`, and then just a summary of the changes in each subsequent change. There are 
# good cases to be made for this approach, as well as for the alternative approach of storing 
# a **complete** new copy  under journal each time a change is made. I think it makes sense 
# to just store subsequent changes because it allows us to highlight DIFFs pretty easily. In 
# addition, it minimizes sprawl and complexity in the data structure. That said, to accomplish 
# this objective of this issue, I needed to work around the limitations of this changes-only 
# approach -- namely, that it's hard to construct a full document from a reference to changes 
# only. So I wrote the following method to 'expand' the `Journal` data structure, see 
# https://github.com/signebedi/libreForms/issues/91 for more information about this.

def generate_full_document_history(form, document_id, user=None):
    try:
        df = get_record_of_submissions(form, user=user if user else None) # here we get the list of entries

        record = df.loc[df.id == document_id] # here we search for the document ID

        history = dict(record[['Journal']].iloc[0].values[0]) # here we pull out the document history

        # dates of new submissions are used as the unique keys in each Journal entry for a form,
        # so we create a list 
        dates = [x for x in history.keys()] 
                
        # now we create a replacement dictionary that will store the full document history in memory, 
        # even though we stored the bare minimum in the database.
        FULL_HISTORY = {}

        # this is an ephemeral dictionary that we are we will re-write each time with the most recent 
        # version. At the time of writing, this seemed like the most efficient way to accomplish what
        # I'm trying to do without iterating through each array / hash multiple times to expand them... 
        BASE_HISTORY = {}

        # the first entry of each Journal contains a full replica of the original submission, so we
        # start with it here to set a baseline
        FULL_HISTORY[dates[0]] = history[dates[0]].copy()

        # delete the initial_submission key if it exists; it's redundant here and can probably be deprecated
        if checkKey(FULL_HISTORY[dates[0]], 'initial_submission'): del FULL_HISTORY[dates[0]]['initial_submission']

        # create an initial carbon copy in BASE_HISTORY - remember, this isn't the for-record dictionary,
        # we're just using it to store the current values of each Journal entry as we iterate through them
        # and expand them.
        BASE_HISTORY = FULL_HISTORY[dates[0]].copy()

        # now we iterate through the remaining submissions that have been logged in the Journal,
        # as these just contain the changes that were submitted. 
        ### NB. we need to capture each subsequent submission!
        for item in dates[1:]:
            for change in history[item].keys():
                BASE_HISTORY[change] = history[item][change]
            FULL_HISTORY[item] = BASE_HISTORY.copy()


        return FULL_HISTORY

    except Exception as e:
        print(e)
        return None


bp = Blueprint('submissions', __name__, url_prefix='/submissions')


@bp.route('/all')
@login_required
def render_all_submissions():

        record = aggregate_form_data(user=None)

        if not isinstance(record, pd.DataFrame):
            flash('The application has not received any submissions.')
            return redirect(url_for('submissions.submissions_home'))
    
        else:

            return render_template('app/submissions.html',
                type="submissions",
                name="all",
                submission=record,
                display=display,
                form_home=True,
                user=current_user,
                menu=form_menu(checkFormGroup),
            )



# define a home route
@bp.route('/')
@login_required
def submissions_home():
    return render_template('app/submissions.html', 
            msg="Select a form from the left-hand menu to view past submissions.",
            name="Submissions",
            type="submissions",
            submissions_home=True,
            menu=form_menu(checkFormGroup),
            display=display,
            user=current_user,
        ) 


# this is kind of like the home page for a given form
@bp.route('/<form_name>')
@login_required
def submissions(form_name):


    if not checkGroup(group=current_user.group, struct=parse_options(form_name)):
            flash(f'You do not have access to this view. ')
            return redirect(url_for('submissions.submissions_home'))

    else:

        if checkKey(libreforms.forms[form_name], "_promiscuous_access_to_submissions") and \
            libreforms.forms[form_name]["_promiscuous_access_to_submissions"]:
                flash("Warning: this form let's everyone view all its submissions.")
                record = get_record_of_submissions(form_name=form_name)
        else:
            record = get_record_of_submissions(form_name=form_name, user=current_user.username)


        if not isinstance(record, pd.DataFrame):
            flash('This form has not received any submissions.')
            return redirect(url_for('submissions.submissions_home'))
    
        else:

            record = record [['Timestamp', 'id']]

            record['hyperlink'] = record.apply(lambda x: gen_hyperlink(x, form_name), axis=1)

            return render_template('app/submissions.html',
                type="submissions",
                name=form_name,
                submission=record,
                display=display,
                form_home=True,
                user=current_user,
                menu=form_menu(checkFormGroup),
            )

### this is very vulnerable -- we should use group auth to restrict access at a form level...
@bp.route('/user/<user>')
@login_required
def render_user_submissions(user):
        record = aggregate_form_data(user=user)

        if not isinstance(record, pd.DataFrame):
            flash('This user has not made any submissions.')
            return redirect(url_for('submissions.submissions_home'))
    
        else:

            return render_template('app/submissions.html',
                type="submissions",
                name="all",
                submission=record,
                display=display,
                form_home=True,
                user=current_user,
                menu=form_menu(checkFormGroup),
            )


@bp.route('/<form_name>/<document_id>')
@login_required
def render_document(form_name, document_id):
    if not checkGroup(group=current_user.group, struct=parse_options(form_name)):
            flash(f'You do not have access to this view. ')
            return redirect(url_for('submissions.submissions_home'))

    else:

        if checkKey(libreforms.forms[form_name], "_promiscuous_access_to_submissions") and \
            libreforms.forms[form_name]["_promiscuous_access_to_submissions"]:

            flash("Warning: this form let's everyone view all its submissions.")
            record = get_record_of_submissions(form_name=form_name)

        else:

            record = get_record_of_submissions(form_name=form_name, user=current_user.username)


        if not isinstance(record, pd.DataFrame):
            flash('This document does not exist.')
            return redirect(url_for('submissions.submissions_home'))
    
        else:
    
            record = record.loc[record['id'] == str(document_id)]


            return render_template('app/submissions.html',
                type="submissions",
                name=form_name,
                submission=record,
                msg=Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}/history'>view document history</a>"),
                display=display,
                user=current_user,
                menu=form_menu(checkFormGroup),
            )


@bp.route('/<form_name>/<document_id>/history', methods=('GET', 'POST'))
@login_required
def render_document_history(form_name, document_id):

    if not checkGroup(group=current_user.group, struct=parse_options(form_name)):
            flash(f'You do not have access to this view. ')
            return redirect(url_for('submissions.submissions_home'))

    else:

        if checkKey(libreforms.forms[form_name], "_promiscuous_access_to_submissions") and \
            libreforms.forms[form_name]["_promiscuous_access_to_submissions"]:
                flash("Warning: this form let's everyone view all its submissions.")
                record = pd.DataFrame(generate_full_document_history(form_name, document_id, user=None))
        else:
            record = pd.DataFrame(generate_full_document_history(form_name, document_id, user=current_user.username))


        if not isinstance(record, pd.DataFrame):
            flash('This document does not exist.')
            return redirect(url_for('submissions.submissions_home'))
    
        else:

            # if a timestamp has been selected, then we set that to the page focus
            if request.args.get("Timestamp"):
                timestamp = request.args.get("Timestamp")
            # if a timestamp hasn't been passed in the get vars, then we default to the most recent
            else:
                # timestamp = record.iloc[-1, record.columns.get_loc('Timestamp')]
                timestamp = record.columns[-1]

            # I'm experimenting with creating the Jinja element in the backend ...
            # it makes applying certain logic -- like deciding which element to mark
            # as active -- much more straightforward. 
            breadcrumb = Markup('<ol style="--bs-breadcrumb-divider: \'>\';" class="breadcrumb">')
            for item in record.columns:
                if item == timestamp:
                    breadcrumb = breadcrumb + Markup(f'<li class="breadcrumb-item active">{item}</li>')
                else:
                    breadcrumb = breadcrumb + Markup(f'<li class="breadcrumb-item"><a href="?Timestamp={item}">{item}</a></li>')
            breadcrumb = breadcrumb + Markup('</ol>')

            for val in record.columns:
                if val != timestamp:
                    # print(f'dropped {val}')
                    record.drop([val], axis=1, inplace=True)

            display_data = record.transpose()
            # print(display_data)

            return render_template('app/submissions.html',
                type="submissions",
                name=form_name,
                submission=display_data,
                display=display,
                breadcrumb=breadcrumb,
                user=current_user,
                msg=Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}'>go back to document</a>"),
                menu=form_menu(checkFormGroup),
            )

# this generates PDFs
# @bp.route('/<form_name><document_id>/download')
# @login_required
# def generate_pdf(form_name, document_id):

#     from reportlab.pdfgen.canvas import Canvas

#     filename = f"{form_name}_{document_id}.pdf"
#     canvas = Canvas(filename)

#     # # this is our first stab at building templates, without accounting for nesting or repetition
#     # df = pd.DataFrame (columns=[x for x in progagate_forms(filename.replace('.csv', '')).keys()], group=current_user.group)

#     # fp = os.path.join(tempfile_path, filename)
#     # df.to_csv(fp, index=False)

#     return send_from_directory(tempfile_path,
#                             filename, as_attachment=True)