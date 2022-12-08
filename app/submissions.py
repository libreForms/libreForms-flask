""" 
submissions.py: implementation of views for post-submission form management



"""

__name__ = "app.submissions"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.0.1"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# import flask-related packages
from flask import current_app, Blueprint, g, flash, abort, render_template, \
    request, send_from_directory, send_file, redirect, url_for
from webargs import fields, flaskparser
from flask_login import current_user
from markupsafe import Markup
from bson import ObjectId
import numpy as np

# import custom packages from the current repository
import libreforms
from app import display, log, tempfile_path, mailer, mongodb
from app.models import User, db
from app.auth import login_required, session
from app.certification import encrypt_with_symmetric_key, verify_symmetric_key
from app.forms import form_menu, checkGroup, checkFormGroup, \
    checkKey, parse_options, progagate_forms, parse_form_fields, \
    collect_list_of_users, compile_depends_on_data, rationalize_routing_routing_list


# and finally, import other packages
import os
import pandas as pd


def get_record_of_submissions(form_name=None, user=None, remove_underscores=True):
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

            if remove_underscores:
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

    df = pd.DataFrame(columns=['form', 'Timestamp', 'id', 'hyperlink', 'Reporter'])
    collections = mongodb.collections()

    if len(collections) > 0:

        for form in collections:

            if user:
                temp_df = get_record_of_submissions(form, user=user)
            else:
                temp_df = get_record_of_submissions(form)

            if isinstance(temp_df, pd.DataFrame):

                for index, row in temp_df.iterrows():
                    z = pd.Series({'Reporter':row['Reporter'], 'Timestamp':row['Timestamp'], 'form':form, 'id':row['id'], 'hyperlink':gen_hyperlink(row, form),}).to_frame().T
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

        # we previously added back in the timestamp (and did it again later for subsequent entries in the
        # document history) - is it worth the extra computation requirement to avoid redundance in adding
        # Timestamp field multiple times? See https://github.com/signebedi/libreForms/issues/140.
        # FULL_HISTORY[dates[0]]['Timestamp'] = dates[0]

        # delete the initial_submission key if it exists; it's redundant here and can probably be deprecated.
        # Nb. This line of code was made redundant by https://github.com/signebedi/libreForms/issues/141.
        # if checkKey(FULL_HISTORY[dates[0]], 'initial_submission'): del FULL_HISTORY[dates[0]]['initial_submission']

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
            
            # see above: because we chose to redundantly add the Timestamp into the 
            # Journal struct keys - redundant since it's used as a parent key to diffrentiate 
            # between edits - we no longer need to add more lines of code ... not sure if this was
            # the right call, but it's easy enough to comment this (and the earlier) line
            # and  to just go with the redundancy ... for more, see
            # https://github.com/signebedi/libreForms/issues/140.
            # BASE_HISTORY['Timestamp'] = item

            # finally we write this update to FULL_HISTORY dict
            FULL_HISTORY[item] = BASE_HISTORY.copy()


        return FULL_HISTORY

    except Exception as e:
        print(e)
        return None


# a short method to just select changes and ignore anything that hasn't changed
# when editing an existing form
def check_args_for_changes(parsed_args, overrides):
    TEMP = {}

    # from pprint import pprint
    # pprint (overrides)
    if 'Journal' in overrides:
        del overrides['Journal'] # this is unnecessary space to iterate through, so drop if exists

    # print(parsed_args, '\n~~~\n', overrides)

    for item in parsed_args:
        if checkKey(overrides, item) and parsed_args[item] == overrides[item]:
            pass
            # print(item, ': ', parsed_args[item], overrides[item], 'No Change')
        else:
            try:
                TEMP[item] = parsed_args[item]
                # print(item, ': ', parsed_args[item], overrides[item], '*')
            except Exception as e:
                print(e)

    return TEMP


def set_digital_signature(      username, 
                                # this is the encrypted string we'd like to verify
                                encrypted_string, 
                                base_string,
                                # most cases benefit from markup with badges; but some 
                                # (like PDFs) are better off with simple strings
                                return_markup=True): 
    
    # for various reasons, the string that we expect to be encrypted is actually a
    # Nonetype - this is because the encrypted string just hasn't been set yet...
    # so, let's just return that Nonetype and go about our business
    if not encrypted_string:
        return None
        
    try:
        with db.engine.connect() as conn:
            reporter = db.session.query(User).filter_by(username=username).first()

        visible_signature_field = getattr(reporter, display['visible_signature_field'])


        verify_signature = verify_symmetric_key (key=reporter.certificate,
                                                encrypted_string=encrypted_string,
                                                base_string=base_string)

        if not return_markup:
            if verify_signature:
                return visible_signature_field + ' (verified)'



            return visible_signature_field + ' (**unverified)'



        if verify_signature:
            return Markup(f'{visible_signature_field} <span class="badge bg-success" data-bs-toggle="tooltip" data-bs-placement="right" title="This form has a verified signature from {reporter.email}">Signature Verified</span>')

        else:
            return Markup(f'{visible_signature_field} <span class="badge bg-warning" data-bs-toggle="tooltip" data-bs-placement="right" title="This form does not have a verifiable signature from {reporter.email}">Signature Cannot Be Verified</span>')

    except:
        return None


bp = Blueprint('submissions', __name__, url_prefix='/submissions')


@bp.route('/all')
@login_required
def render_all_submissions():

        record = aggregate_form_data(user=None)
        # print(record)

        # we start by dropping out any entries that no longer have 
        # form configurations; some vestigial forms may exist in the 
        # system; there is a bigger problem: how do we handle forms
        # that receive submissions but are later removed from the system
        # or have their names changed? There should be some kind of orderly
        # transition process in the UI, or export-unstructured-data feature
        # for admins, see https://github.com/signebedi/libreForms/issues/130.
        record = record.drop(record.loc[~record.form.isin(libreforms.forms.keys())].index)
        # print(record['form'].unique())

        ### this is where we run the data set through some 
        ### logic that checks _deny_read and removes forms for which
        ### the current user's group does not have access, see
        ### https://github.com/signebedi/libreForms/issues/124
    
        # collections = mongodb.collections()
        for form in libreforms.forms.keys():
            # print(form)
            verify_group = parse_options(form=form)['_submission']
            
            if checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']:
                # print(record.loc[record.form == form])
                record = record.drop(record[record['form'] == form].index)

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

        try:
            verify_group = parse_options(form=form_name)['_submission']
        except Exception as e:
            flash('This form does not exist.')
            log.warning(f'{current_user.username.upper()} - {e}')
            return redirect(url_for('submissions.submissions_home'))


        # by routing these condition through parse_options, we make the logic easier to
        # verify using default values if none are passed; meaning we can presume something
        # about the datastructure ..
        # if checkKey(libreforms.forms, form_name) and \
        #     checkKey(libreforms.forms[form_name], '_enable_universal_form_access') and \
        #     libreforms.forms[form_name]['_enable_universal_form_access']:
        if parse_options(form=form_name)['_submission']['_enable_universal_form_access'] and not \
            (checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']):
                flash("Note: this form permits broad view access all its submissions. ")
                record = get_record_of_submissions(form_name=form_name)
        else:
            record = get_record_of_submissions(form_name=form_name, user=current_user.username)


        if not isinstance(record, pd.DataFrame):
            flash(f'This form has not received any submissions.')
            return redirect(url_for('submissions.submissions_home'))
    
        else:

            record = record [['Timestamp', 'id', 'Reporter']]
            record['form'] = form_name

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
        try:
            record = aggregate_form_data(user=user)

        except Exception as e:
            abort(404)

        if not isinstance(record, pd.DataFrame):
            abort(404)

    
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

        try:
            options = parse_options(form=form_name)
            verify_group = options['_submission']
        except Exception as e:
            flash('This form does not exist.')
            log.warning(f'{current_user.username.upper()} - {e}')
            return redirect(url_for('submissions.submissions_home'))

        # if checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']:
        #     flash('You do not have access to this resource.')
        #     return redirect(url_for('submissions.submissions_home'))


        # if checkKey(libreforms.forms, form_name) and \
        #     checkKey(libreforms.forms[form_name], '_enable_universal_form_access') and \
        #     libreforms.forms[form_name]['_enable_universal_form_access']:
        if parse_options(form=form_name)['_submission']['_enable_universal_form_access'] and not \
            (checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']):
            flash("Note: this form permits broad view access all its submissions. ")
            record = get_record_of_submissions(form_name=form_name)

        else:

            record = get_record_of_submissions(form_name=form_name, user=current_user.username)


        if not isinstance(record, pd.DataFrame):
            flash('This document does not exist.')
            return redirect(url_for('submissions.submissions_home'))
    
        else:
            record = record.loc[record['id'] == str(document_id)]
            # we abort if the form doesn't exist
            if len(record.index)<1:
                abort(404)

            record.drop(columns=['Journal'], inplace=True)


            # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
            if 'Signature' in record.columns:
                if options['_digitally_sign']:
                    record['Signature'].iloc[0] = set_digital_signature(username=record['Owner'].iloc[0],
                                                                        encrypted_string=record['Signature'].iloc[0], 
                                                                        base_string=display['signature_key'])
                else:
                    record.drop(columns=['Signature'], inplace=True)

            # Added signature verification, see https://github.com/signebedi/libreForms/issues/144    
            if 'Approval' in record.columns and record['Approval'].iloc[0]:
                try:
                    record['Approval'].iloc[0] = set_digital_signature(username=db.session.query(User).filter_by(email=record['Approver'].iloc[0]).first().username,
                            encrypted_string=record['Approval'].iloc[0],
                            base_string=display['approval_key'])

                except:
                    record['Approval'].iloc[0] = None

            # we set nan values to None
            record.replace({np.nan:None}, inplace=True)


            msg = Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}/history'>view document history</a>")

            # print (current_user.username)
            # print (record['Reporter'].iloc[0])

            if ((not checkKey(verify_group, '_deny_write') or not current_user.group in verify_group['_deny_write'])) or current_user.username == record['Reporter'].iloc[0]:
                msg = msg + Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}/edit'>edit this document</a>")

            if parse_options(form_name)['_form_approval'] and 'Approver' in record.columns and record['Approver'].iloc[0] == current_user.email:
                msg = msg + Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}/review'>go to form approval</a>")

            if parse_options(form_name)['_allow_pdf_download']:
                msg = msg + Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}/download'>download PDF</a>")
            
            return render_template('app/submissions.html',
                type="submissions",
                name=form_name,
                submission=record,
                msg=msg,
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


        try:
            options = parse_options(form=form_name)
            verify_group = options['_submission']
        except Exception as e:
            flash('This form does not exist.')
            log.warning(f'{current_user.username.upper()} - {e}')
            return redirect(url_for('submissions.submissions_home'))

        # if checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']:
        #     flash('You do not have access to this resource.')
        #     return redirect(url_for('submissions.submissions_home'))


        # if checkKey(libreforms.forms, form_name) and \
        #     checkKey(libreforms.forms[form_name], '_enable_universal_form_access') and \
        #     libreforms.forms[form_name]['_enable_universal_form_access']:
        if parse_options(form=form_name)['_submission']['_enable_universal_form_access'] and not \
            (checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']):

            flash("Note: this form permits broad view access all its submissions. ")
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
            breadcrumb = Markup(f'<ol style="--bs-breadcrumb-divider: \'>\';" class="breadcrumb {"" if display["dark_mode"] and not current_user.theme == "light" else "bg-transparent text-dark"}">')
            for item in record.columns:
                if item == timestamp:
                    breadcrumb = breadcrumb + Markup(f'<li class="breadcrumb-item active">{item}</li>')
                else:
                    breadcrumb = breadcrumb + Markup(f'<li class="breadcrumb-item"><a href="?Timestamp={item}" class="{"" if display["dark_mode"] and not current_user.theme == "light" else "text-dark"}">{item}</a></li>')
            breadcrumb = breadcrumb + Markup('</ol>')


            for val in record.columns:
                if val != timestamp:
                    # print(f'dropped {val}')
                    record.drop([val], axis=1, inplace=True)

            display_data = record.transpose()

            # print(display_data.iloc[0])

            # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
            if 'Signature' in display_data.columns:
                if options['_digitally_sign']:
                    display_data['Signature'].iloc[0] = set_digital_signature(username=display_data['Owner'].iloc[0],
                                                                                encrypted_string=display_data['Signature'].iloc[0], 
                                                                                base_string=display['signature_key'])

            # Added signature verification, see https://github.com/signebedi/libreForms/issues/144    
            if 'Approval' in display_data.columns:
                if pd.notnull(display_data['Approval'].iloc[0]): # verify that this is not nan, see https://stackoverflow.com/a/57044299/13301284
                    # print(display_data['Approval'].iloc[0])
                    display_data['Approval'].iloc[0] = set_digital_signature(username=db.session.query(User).filter_by(email=display_data['Approver'].iloc[0]).first().username,
                                    encrypted_string=display_data['Approval'].iloc[0],
                                    base_string=display['approval_key'])
                
                # After https://github.com/signebedi/libreForms/issues/145, adding this to ensure that
                # `Approval` is never None. 
                else:
                    # display_data.drop(columns=['Approval'], inplace=True)
                    display_data['Approval'].iloc[0] = None


            display_data.replace({np.nan:None}, inplace=True)

            # here we set a list of values to emphasize in the table because they've changed values
            t = get_record_of_submissions(form_name) 
            t2 = t.loc[t.id == document_id] 
            t3 = dict(t2[['Journal']].iloc[0].values[0]) 
            emphasize = [x for x in t3[timestamp].keys()]
            flash(f'The following values changed in this version and are emphasized below: {", ".join(emphasize)}. ')


            msg = Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}'>go back to document</a>")

            # print (current_user.username)
            # print (record.transpose()['Reporter'].iloc[0])
            # print (record['Reporter'].iloc[0])

            if ((not checkKey(verify_group, '_deny_write') or not current_user.group in verify_group['_deny_write'])) or current_user.username == record['Reporter'].iloc[0]:
                msg = msg + Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}/edit'>edit this document</a>")
            

            if parse_options(form_name)['_form_approval'] and 'Approver' in display_data.columns and display_data['Approver'].iloc[0] == current_user.email:
                msg = msg + Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}/review'>go to form approval</a>")

            # eventually, we may wish to add support for downloading past versions 
            # of the PDF, too; not just the current form of the PDF; the logic does 
            # seem to support this, eg. sending the `display_data`
            if parse_options(form_name)['_allow_pdf_download']:
                msg = msg + Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}/download'>download PDF</a>")

            return render_template('app/submissions.html',
                type="submissions",
                name=form_name,
                submission=display_data,
                display=display,
                emphasize=emphasize,
                breadcrumb=breadcrumb,
                user=current_user,
                msg=msg,
                menu=form_menu(checkFormGroup),
            )


@bp.route('/<form_name>/<document_id>/edit', methods=('GET', 'POST'))
@login_required
def render_document_edit(form_name, document_id):
    try:

        if not checkGroup(group=current_user.group, struct=parse_options(form_name)):
                flash(f'You do not have access to this view. ')
                return redirect(url_for('submissions.submissions_home'))

        else:

            try:
                verify_group = parse_options(form=form_name)['_submission']
            except Exception as e:
                flash('This form does not exist.')
                log.warning(f'{current_user.username.upper()} - {e}')
                return redirect(url_for('submissions.submissions_home'))

            # if checkKey(verify_group, '_deny_write') and current_user.group in verify_group['_deny_write']:
            #     flash('You do not have access to this resource.')
            #     return redirect(url_for('submissions.submissions_home'))


            # if checkKey(libreforms.forms, form_name) and \
            #     checkKey(libreforms.forms[form_name], '_enable_universal_form_access') and \
            #     libreforms.forms[form_name]['_enable_universal_form_access']:
            if parse_options(form=form_name)['_submission']['_enable_universal_form_access'] and not \
            (checkKey(verify_group, '_deny_write') and current_user.group in verify_group['_deny_write']):
                # flash("Warning: this form lets everyone view all its submissions. ")
                record = get_record_of_submissions(form_name=form_name,remove_underscores=False)

            else:

                record = get_record_of_submissions(form_name=form_name, user=current_user.username, remove_underscores=False)


            if not isinstance(record, pd.DataFrame):
                flash('This document does not exist.')
                return redirect(url_for('submissions.submissions_home'))
        
            else:
        
                options = parse_options(form_name)
                forms = progagate_forms(form_name, group=current_user.group)

                if not str(document_id) in record['id'].values:
                    flash('You do not have edit access to this form.')
                    return redirect(url_for('submissions.submissions_home'))      

                record = record.loc[record['id'] == str(document_id)]
                # we abort if the form doesn't exist
                if len(record.index)<1:
                    abort(404)

                # here we convert the slice to a dictionary to use to override default values
                overrides = record.iloc[0].to_dict()
                # print(overrides)

                if request.method == 'POST':
                    
                    parsed_args = flaskparser.parser.parse(parse_form_fields(form_name, user_group=current_user.group, args=list(request.form)), request, location="form")
                    
                    # here we drop any elements that are not changes
                    parsed_args = check_args_for_changes(parsed_args, overrides)

                    # we may need to pass this as a string
                    parsed_args['_id'] = ObjectId(document_id)

                    # from pprint import pprint
                    # pprint(parsed_args)

                    digital_signature = encrypt_with_symmetric_key(current_user.certificate, display['signature_key']) if options['_digitally_sign'] else None

                    # here we pass a modification
                    mongodb.write_document_to_collection(parsed_args, form_name, reporter=current_user.username, modification=True, digital_signature=digital_signature)
                    
                    flash(str(parsed_args))

                    # log the update
                    log.info(f'{current_user.username.upper()} - updated \'{form_name}\' form, document no. {document_id}.')

                    # here we build our message and subject, customized for anonymous users
                    subject = f'{display["site_name"]} {form_name} Updated ({document_id})'
                    content = f"This email serves to verify that {current_user.username} ({current_user.email}) has just updated the {form_name} form, which you can view at {display['domain']}/submissions/{form_name}/{document_id}. {'; '.join(key + ': ' + str(value) for key, value in parsed_args.items() if key != 'Journal') if options['_send_form_with_email_notification'] else ''}"
                    
                    # and then we send our message
                    mailer.send_mail(subject=subject, content=content, to_address=current_user.email, cc_address_list=rationalize_routing_routing_list(form_name), logfile=log)

                    # and then we redirect to the forms view page
                    return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id))

                


                return render_template('app/forms.html', 
                    context=forms,                                          # this passes the form fields as the primary 'context' variable
                    name=form_name,                                         # this sets the name of the page for the page header
                    menu=form_menu(checkFormGroup),              # this returns the forms in libreform/forms to display in the lefthand menu
                    type="forms",       
                    default_overrides=overrides,
                    editing_existing_form=True,
                    options=options, 
                    display=display,
                    filename = f'{form_name.lower().replace(" ","")}.csv' if options['_allow_csv_templates'] else False,
                    user=current_user,
                    depends_on=compile_depends_on_data(form_name, user_group=current_user.group),
                    user_list = collect_list_of_users() if display['allow_forms_access_to_user_list'] else [],
                    )

    except Exception as e:
        flash(f'This form does not exist. {e}')
        return redirect(url_for('submissions.submissions_home'))

# this is a replica of render_document() above, just modified to check for 
# parse_options(form_name)['_form_approval'] and verify that the current_user
# is the form approver, otherwise abort. See https://github.com/signebedi/libreForms/issues/8.

@bp.route('/<form_name>/<document_id>/review', methods=['GET', 'POST'])
@login_required
def review_document(form_name, document_id):
    
    try:
        options = parse_options(form=form_name)
        verify_group = options['_submission']
        if not options['_form_approval']:
            abort(404)
            # return redirect(url_for('submissions.render_document', form_name=form_name,document_id=document_id))

    except Exception as e:
        flash('This form does not exist.')
        log.warning(f'{current_user.username.upper()} - {e}')
        return redirect(url_for('submissions.submissions_home'))


    record = get_record_of_submissions(form_name=form_name)

    if not isinstance(record, pd.DataFrame):
        flash('This document does not exist.')
        return redirect(url_for('submissions.submissions_home'))

    else:

        record = record.loc[record['id'] == str(document_id)]
        # we abort if the form doesn't exist
        if len(record.index)<1:
            abort(404)

        # if the approver verification doesn't check out
        if not 'Approver' in record.columns or not record['Approver'].iloc[0] or record['Approver'].iloc[0] != current_user.email:
            abort(404)


        if request.method == 'POST':
            approve = request.form['approve']
            comment = request.form['comment']
            
            # print(str(approve), str(comment))

            # if approve == 'not-now':
            #     flash('You have not approved this form. ')

            # elif approve == 'no':
            #     flash('You disapproved this form. ')

            # elif approve == 'yes':
            #     flash('You have approved this form. ')
            
            # if comment == '':
            #     flash('You have not added any comments to this form. ')
            # else:
            #     flash('You have added comments to this form. ')

            if approve == 'yes':
                flash('You have approved this form. ')
                digital_signature = encrypt_with_symmetric_key(current_user.certificate, display['approval_key']) if options['_digitally_sign'] else None
            elif approve == 'no':
                flash('You disapproved this form. ')
                digital_signature = encrypt_with_symmetric_key(current_user.certificate, display['disapproval_key']) if options['_digitally_sign'] else None
            else:
                flash('You have not approved this form. ')
                digital_signature = None

            if comment == '':
                # set comment to None if the arrived empty
                comment = None
                flash('You have not added any comments to this form. ')
            else:
                flash('You have added comments to this form. ')
 

            # here we pull the default values to assess the POSTed values against
            overrides = record.iloc[0].to_dict()
                    
            # here we drop any elements that are not changed from the overrides
            verify_changes_to_approval = check_args_for_changes({'Approval': digital_signature}, overrides)
            verify_changes_to_approver_comment = check_args_for_changes({'Approver_Comment': comment}, overrides)

           
            # presuming there is a change, write the change
            # if approve != 'no' or comment != '':

            mongodb.write_document_to_collection({'_id': ObjectId(document_id)}, form_name, 
                                                    reporter=current_user.username, 
                                                    modification=True,
                                                    # if these pass check_args_for_changes(), then pass values; else None
                                                    approval=verify_changes_to_approval['Approval'] if 'Approval' in verify_changes_to_approval else None,
                                                    approver_comment=verify_changes_to_approver_comment['Approver_Comment'] if 'Approver_Comment' in verify_changes_to_approver_comment else None)

            return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id))


            # if approval == '' and comment != '':
            #     flash('You have added a comment to this form. ')



        record.drop(columns=['Journal'], inplace=True)


        # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
        if 'Signature' in record.columns:
            if options['_digitally_sign']:
                record['Signature'].iloc[0] = set_digital_signature(username=record['Owner'].iloc[0],
                                                                    encrypted_string=record['Signature'].iloc[0], 
                                                                    base_string=display['signature_key'])
            else:
                record.drop(columns=['Signature'], inplace=True)
        # Added signature verification, see https://github.com/signebedi/libreForms/issues/144    
        if 'Approval' in record.columns and record['Approval'].iloc[0]:
            try:
                record['Approval'].iloc[0] = set_digital_signature(username=db.session.query(User).filter_by(email=record['Approver'].iloc[0]).first().username,
                                encrypted_string=record['Approval'].iloc[0],
                                base_string=display['approval_key'])
            except:
                record['Approval'].iloc[0] = None

        # we set nan values to None
        record.replace({np.nan:None}, inplace=True)


        msg = Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}'>go back to document</a>")
        msg = msg + Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}/history'>view document history</a>")

        # print (current_user.username)
        # print (record['Reporter'].iloc[0])


        return render_template('app/submissions.html',
            type="submissions",
            name=form_name,
            submission=record,
            msg=msg,
            display=display,
            form_approval=True,
            user=current_user,
            menu=form_menu(checkFormGroup),
        )



# this generates PDFs
@bp.route('/<form_name>/<document_id>/download')
@login_required
def generate_pdf(form_name, document_id):

    try:
        test_the_form_options = parse_options(form=form_name)

    except Exception as e:
        flash('This form does not exist.')
        log.warning(f'{current_user.username.upper()} - {e}')
        return redirect(url_for('submissions.render_document', form_name=form_name,document_id=document_id))

    if not test_the_form_options['_allow_pdf_download']:
        flash(f'This form does not have downloads enabled. ')
        return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id))


    if not checkGroup(group=current_user.group, struct=test_the_form_options):
        flash(f'You do not have access to this view. ')
        return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id))

    else:
        
        verify_group = test_the_form_options['_submission']

        if verify_group['_enable_universal_form_access'] and not \
            (checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']):
            record = get_record_of_submissions(form_name=form_name)

        else:

            record = get_record_of_submissions(form_name=form_name, user=current_user.username)


        if not isinstance(record, pd.DataFrame):
            flash('This document does not exist.')
            return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id))
    
        else:
    
            record = record.loc[record['id'] == str(document_id)]
            # we abort if the form doesn't exist
            if len(record.index)<1:
                abort(404)

            record.drop(columns=['Journal'], inplace=True)

            # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
            if 'Signature' in record.columns:
                if test_the_form_options['_digitally_sign']:
                    record['Signature'].iloc[0] = set_digital_signature(username=record['Owner'].iloc[0],
                                                                        encrypted_string=record['Signature'].iloc[0], 
                                                                        base_string=display['signature_key'], 
                                                                        return_markup=False)
                else:
                    record.drop(columns=['Signature'], inplace=True)
            
            # Added signature verification, see https://github.com/signebedi/libreForms/issues/144    
            if 'Approval' in record.columns and record['Approval'].iloc[0]:
                try:
                    record['Approval'].iloc[0] = set_digital_signature(username=db.session.query(User).filter_by(email=record['Approver'].iloc[0]).first().username,
                                encrypted_string=record['Approval'].iloc[0], 
                                base_string=display['approval_key'],
                                return_markup=False)

                except:
                    record['Approval'].iloc[0] = None

            # we set nan values to None
            record.replace({np.nan:None}, inplace=True)


            import libreforms
            import datetime
            from app.pdf import generate_pdf
            filename = f"{form_name}_{document_id}.pdf"
            fp = os.path.join(tempfile_path, filename)
            # document_name= f'{datetime.datetime.utcnow().strftime("%Y-%m-%d")}_{current_user.username}_{form_name}.pdf'

            generate_pdf(   form_name=form_name, 
                            data_structure=dict(record.iloc[0]), 
                            username=current_user.username,
                            document_name=fp,
                            skel=libreforms.forms[form_name]    )

            return send_from_directory(tempfile_path,
                                    filename, as_attachment=True)