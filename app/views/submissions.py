""" 
submissions.py: implementation of views for post-submission form management



"""

__name__ = "app.views.submissions"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.9.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# import flask-related packages
from flask import current_app, Blueprint, g, flash, abort, render_template, \
    request, send_from_directory, send_file, redirect, url_for
from webargs import fields, flaskparser
from werkzeug.security import check_password_hash        
from flask_login import current_user
from markupsafe import Markup
from bson import ObjectId

# import custom packages from the current repository
import libreforms
from app import config, log, mailer, mongodb
from app.models import User, db
from app.form_access import list_of_forms_approved_by_this_group
from app.views.auth import login_required, session
from app.certification import encrypt_with_symmetric_key, verify_symmetric_key
from app.views.forms import form_menu, checkGroup, checkFormGroup, \
    checkKey, propagate_form_configs, propagate_form_fields, define_webarg_form_data_types, \
    collect_list_of_users, compile_depends_on_data, rationalize_routing_list, standard_view_kwargs
from celeryd.tasks import send_mail_async


# and finally, import other packages
import os
import pandas as pd
import numpy as np
import json


def get_record_of_submissions(form_name=None, user=None, remove_underscores=False):
    if form_name:

        try:
            data = mongodb.read_documents_from_collection(form_name)
            df = pd.DataFrame(list(data))

            # set ID to string instead of object ID
            df['_id'] = df['_id'].astype(str)
            # df.rename(columns = {'_id':'id'}, inplace = True)

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
                    df = df.loc[df[mongodb.metadata_field_names['owner']] == user]
                except Exception as e: 
                    log.info(f"{user.upper()} - tried to query {form_name} database for user but no entries were found. {e}")
                    return None

            if remove_underscores:
                df.columns = [x.replace("_", " ") for x in df.columns]

            if len(df.index) == 0:
                return None

            return df
        except Exception as e: 
            log.warning(f"LIBREFORMS - {e}")
            return None


    return None


def gen_hyperlink(row, form_name, content_field=None):
    # return Markup(f"<p><a href=\"{config['domain']}/submissions/{form_name}/{row._id}\">{form_name}</a></p>")
    if content_field:
        return Markup(f"<a href=\"{config['domain']}/submissions/{form_name}/{row._id}\">{row[content_field]}</a>")

    return Markup(f"<a href=\"{config['domain']}/submissions/{form_name}/{row._id}\">{config['domain']}/submissions/{form_name}/{row._id}</a>")


# in this method we aggregate all the relevant information
def aggregate_form_data(*args, user=None):

    columns=['form', mongodb.metadata_field_names['timestamp'], '_id', 'hyperlink', mongodb.metadata_field_names['reporter'], mongodb.metadata_field_names['owner']]+[x for x in args]
    # print (columns)

    df = pd.DataFrame(columns=columns)
    collections = mongodb.collections()

    if len(collections) > 0:

        for form in collections:

            if user:
                temp_df = get_record_of_submissions(form, user=user)
            else:
                temp_df = get_record_of_submissions(form)

            if isinstance(temp_df, pd.DataFrame):

                for index, row in temp_df.iterrows():

                    TEMP = {mongodb.metadata_field_names['owner']:row[mongodb.metadata_field_names['owner']], 
                            mongodb.metadata_field_names['reporter']:row[mongodb.metadata_field_names['reporter']], 
                            mongodb.metadata_field_names['timestamp']:row[mongodb.metadata_field_names['timestamp']], 
                            'form':form, 
                            '_id':row['_id'], 
                            'hyperlink':gen_hyperlink(row, form),
                            }

                    for a in args:
                        TEMP[a] = row[a] if a in row else None

                    # print(TEMP)


                    z = pd.Series(TEMP).to_frame().T

                    # print (z)
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

        record = df.loc[df._id == document_id] # here we search for the document ID

        history = dict(record[[mongodb.metadata_field_names['journal']]].iloc[0].values[0]) # here we pull out the document history

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
            # BASE_HISTORY[mongodb.metadata_field_names['timestamp']] = item

            # finally we write this update to FULL_HISTORY dict
            FULL_HISTORY[item] = BASE_HISTORY.copy()


        return FULL_HISTORY

    except Exception as e: 
        log.warning(f"LIBREFORMS - {e}")
        return None


# a short method to just select changes and ignore anything that hasn't changed
# when editing an existing form
def check_args_for_changes(parsed_args, overrides):
    TEMP = {}

    # from pprint import pprint
    # pprint (overrides)
    if mongodb.metadata_field_names['journal'] in overrides:
        del overrides[mongodb.metadata_field_names['journal']] # this is unnecessary space to iterate through, so drop if exists

    if mongodb.metadata_field_names['metadata'] in overrides:
        del overrides[mongodb.metadata_field_names['metadata']] # this is unnecessary space to iterate through, so drop if exists


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
                log.warning(f"LIBREFORMS - {e}")

    return TEMP


def set_digital_signature(      username, 
                                # this is the encrypted string we'd like to verify
                                encrypted_string, 
                                base_string,
                                # we allow ourselves to set a fallback string
                                # to assess the encrypted string against in the 
                                # event of a failure; this will return a DENIED
                                # badge.
                                fallback_string=None,
                                # select_on=config['visible_signature_field'],
                                # most cases benefit from markup with badges; but some 
                                # (like PDFs) are better off with simple strings
                                return_markup=True,
                                # if the following are given a value, then include
                                # this data in the signature rendered for the user;
                                # IP address will only work if the _collect_client_ip
                                # form config is set to True; for more discussion, see
                                # https://github.com/signebedi/libreForms/issues/175
                                timestamp=None,
                                ip=None,): 
    
    # for various reasons, the string that we expect to be encrypted is actually a
    # Nonetype - this is because the encrypted string just hasn't been set yet...
    # so, let's just return that Nonetype and go about our business
    if not encrypted_string:
        return None
    
    # interestingly, we're referencing documents using a pandas dataframe, instead of the raw
    # dictionary. This was, initially, for simplicity and ease of queries. In fact, it still
    # makes sense for summary views that provide lists of documents. But it is highly ineffecient
    # for single document views, and results in added logic like this, where if the `encrypted_string`
    # parameter is a float, then it is probably a NAN value in the pandas dataframe, see 
    # https://pandas.pydata.org/pandas-docs/stable/user_guide/missing_data.html.
    if type(encrypted_string) == float:
        return None

    # print(ip if ip else '')
    # print(timestamp if timestamp else '')

    try:
        with db.engine.connect() as conn:
            reporter = db.session.query(User).filter_by(username=username).first()

        visible_signature_field = getattr(reporter, config['visible_signature_field'])


        verify_signature = verify_symmetric_key (key=reporter.certificate,
                                                encrypted_string=encrypted_string,
                                                base_string=base_string)

        # test whether the fallback passes instead
        verify_fallback = verify_symmetric_key (key=reporter.certificate,
                                                encrypted_string=encrypted_string,
                                                base_string=fallback_string)


        if not return_markup:
            if verify_signature:
                return visible_signature_field + f' (Signed{" on "+timestamp if timestamp else ""}{" from "+ip if ip else ""})'
            elif verify_fallback:
                return visible_signature_field + f' (Disapproved{" on "+timestamp if timestamp else ""}{" from "+ip if ip else ""})'


            return visible_signature_field + ' (**Unverified)'



        if verify_signature:
            return Markup(f'{visible_signature_field} <span class="badge bg-success" data-bs-toggle="tooltip" data-bs-placement="right" title="This form has a verified signature from {reporter.username}{" on "+timestamp if timestamp else ""}{" from "+ip if ip else ""}">Signed</span>')
        elif verify_fallback:
            return Markup(f'{visible_signature_field} <span class="badge bg-danger" data-bs-toggle="tooltip" data-bs-placement="right" title="This form has a verified signature from {reporter.username}{" on "+timestamp if timestamp else ""}{" from "+ip if ip else ""}">Disapproved</span>')

        return Markup(f'{visible_signature_field} <span class="badge bg-warning" data-bs-toggle="tooltip" data-bs-placement="right" title="This form does not have a verifiable signature from {reporter.username}">Unverified</span>')

    except Exception as e: 
        log.warning(f"LIBREFORMS - {e}")
        return None
# this function is used to generate a list of approvals for the current user
# select_on is the field upon which we will select the approval value.
# this is written such that `len(aggregate_approval_count(select_on=getattr(current_user,config['visible_signature_field'])).index)`
# will return the number of unsigned approvals
def aggregate_approval_count(select_on=None): 

        try:
            record = aggregate_form_data(mongodb.metadata_field_names['approver'], mongodb.metadata_field_names['approval'], user=None)

            # first we drop values that are not tied to the current list of acceptible forms
            record = record.drop(record.loc[~record.form.isin(libreforms.forms.keys())].index)

            # then we select those whose approver is set to the select_on parameter
            forms_approved_by_user = record.loc[(record[mongodb.metadata_field_names['approver']] == select_on) & (record[mongodb.metadata_field_names['approval']].isna())]

            # these forms should be approved by group
            forms_approved_by_group = record.loc[(record.form.isin(list_of_forms_approved_by_this_group(group=current_user.group))) & (record[mongodb.metadata_field_names['approval']].isna())]

            # print(pd.concat([forms_approved_by_user, forms_approved_by_group], ignore_index=True))

            # we concat the two dataframes above and return
            return pd.concat([forms_approved_by_user, forms_approved_by_group], ignore_index=True)
            

        except Exception as e: 
            log.warning(f"LIBREFORMS - {e}") 
            return pd.DataFrame()
            

def generate_username_badge_list(form_name:str) -> list:
    
    if not config['parse_usernames_as_badges']:
        return []
    
    FIELD_LIST = []
    
    # add the basic metadata fields
    FIELD_LIST.append(mongodb.metadata_field_names['owner'])
    FIELD_LIST.append(mongodb.metadata_field_names['reporter'])
    FIELD_LIST.append(mongodb.metadata_field_names['approver'])
    FIELD_LIST.append(mongodb.metadata_field_names['approval'])

    for index,data in propagate_form_fields(form_name).items():
        if '_render_user_badges' in data and data['_render_user_badges']:
            FIELD_LIST.append(index)

    return FIELD_LIST

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
            verify_group = propagate_form_configs(form=form)['_submission']
            
            if checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']:
                # print(record.loc[record.form == form])
                record = record.drop(record[record['form'] == form].index)

        if not isinstance(record, pd.DataFrame):
            flash('The application has not received any submissions.', "warning")
            return redirect(url_for('submissions.submissions_home'))
    
        else:

            return render_template('submissions/submissions_form_home.html.jinja',
                type="submissions",
                name='Submissions',
                subtitle="All",
                submission=record,
                menu=form_menu(checkFormGroup),
                **standard_view_kwargs(),
            )



# define a home route
@bp.route('/')
@login_required
def submissions_home():
    return render_template('submissions/submissions.html.jinja', 
            msg="Select a form from the left-hand menu to view past submissions.",
            name='Submissions',
            subtitle="Home",
            type="submissions",
            submissions_home=True,
            menu=form_menu(checkFormGroup),
            **standard_view_kwargs(),
        ) 


# this is kind of like the home page for a given form
@bp.route('/<form_name>')
@login_required
def submissions(form_name):


    if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)):
            flash(f'You do not have access to this view. ', "warning")
            return redirect(url_for('submissions.submissions_home'))

    else:

        try:
            verify_group = propagate_form_configs(form=form_name)['_submission']
        except Exception as e: 
            flash('This form does not exist.', "warning")
            log.warning(f'{current_user.username.upper()} - {e}')
            return redirect(url_for('submissions.submissions_home'))


        # by routing these condition through propagate_form_configs, we make the logic easier to
        # verify using default values if none are passed; meaning we can presume something
        # about the datastructure ..
        # if checkKey(libreforms.forms, form_name) and \
        #     checkKey(libreforms.forms[form_name], '_enable_universal_form_access') and \
        #     libreforms.forms[form_name]['_enable_universal_form_access']:
        if propagate_form_configs(form=form_name)['_submission']['_enable_universal_form_access'] and not \
            (checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']):
                flash("Note: this form permits broad view access all its submissions. ", "info")
                record = get_record_of_submissions(form_name=form_name)
        else:
            record = get_record_of_submissions(form_name=form_name, user=current_user.username)


        if not isinstance(record, pd.DataFrame):
            flash(f'This form has not received any submissions.', "warning")
            return redirect(url_for('submissions.submissions_home'))
    
        else:

            record = record [[mongodb.metadata_field_names['timestamp'], '_id', mongodb.metadata_field_names['owner']]+propagate_form_configs(form=form_name)['_submission_view_summary_fields']]
            record['form'] = form_name

            record['Last Edited'] = record.apply(lambda x: gen_hyperlink(x, form_name, content_field=mongodb.metadata_field_names['timestamp']), axis=1)

            return render_template('submissions/submissions_form_home.html.jinja',
                type="submissions",
                name='Submissions',
                subtitle=form_name,
                submission=record,
                menu=form_menu(checkFormGroup),
                **standard_view_kwargs(),
            )

# this view shows the forms that are requiring current_user review
@bp.route('/review/<user>')
@login_required
def render_user_review(user):

        record = aggregate_approval_count(select_on=getattr(current_user,config['visible_signature_field']))

        # # collections = mongodb.collections()
        # for form in libreforms.forms.keys():
        #     # print(form)
        #     verify_group = propagate_form_configs(form=form)['_submission']
            
        #     if checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']:
        #         # print(record.loc[record.form == form])
        #         record = record.drop(record[record['form'] == form].index)
    

        return render_template('submissions/submissions_form_home.html.jinja',
            type="submissions",
            name='Submissions',
            subtitle="Review",
            submission=record,
            menu=form_menu(checkFormGroup),
            **standard_view_kwargs(),
        )

# this is the user by user view; it allows any authenticated user to view, 
# but only shows form for which their group has not been denied read access
@bp.route('/user/<user>')
@login_required
def render_user_submissions(user):
        try:
            record = aggregate_form_data(user=user)

        except Exception as e: 
            log.warning(f"LIBREFORMS - {e}")
            return abort(404)

        if not isinstance(record, pd.DataFrame):
            flash('No submissions found for this user. ', "warning")
            return redirect(url_for('auth.profile'))

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
            verify_group = propagate_form_configs(form=form)['_submission']
            
            if checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']:
                # print(record.loc[record.form == form])
                record = record.drop(record[record['form'] == form].index)

    
        else:

            return render_template('submissions/submissions_form_home.html.jinja',
                type="submissions",
                name='Submissions',
                subtitle="All",
                submission=record,
                menu=form_menu(checkFormGroup),
                **standard_view_kwargs(),
            )


@bp.route('/<form_name>/<document_id>')
@login_required
def render_document(form_name, document_id, ignore_menu=False):
    if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)):
            flash(f'You do not have access to this view. ', "warning")
            return redirect(url_for('submissions.submissions_home'))

    else:

        try:
            options = propagate_form_configs(form=form_name)
            verify_group = options['_submission']
        except Exception as e: 
            flash('This form does not exist.', "warning")
            log.warning(f'{current_user.username.upper()} - {e}')
            return redirect(url_for('submissions.submissions_home'))

        # if checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']:
        #     flash('You do not have access to this resource.')
        #     return redirect(url_for('submissions.submissions_home'))


        # if checkKey(libreforms.forms, form_name) and \
        #     checkKey(libreforms.forms[form_name], '_enable_universal_form_access') and \
        #     libreforms.forms[form_name]['_enable_universal_form_access']:
        if propagate_form_configs(form=form_name)['_submission']['_enable_universal_form_access'] and not \
            (checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']):
            flash("Note: this form permits broad view access all its submissions. ", "info")
            record = get_record_of_submissions(form_name=form_name)

        else:

            record = get_record_of_submissions(form_name=form_name, user=current_user.username)


        if not isinstance(record, pd.DataFrame):
            flash('This document does not exist.', "warning")
            return redirect(url_for('submissions.submissions_home'))
    
        else:
            record = record.loc[record['_id'] == str(document_id)]
            # we abort if the form doesn't exist
            if len(record.index)<1:
                return abort(404)

            # print(record)
            record.drop(columns=[mongodb.metadata_field_names['journal']], inplace=True)

            # strangely enough, this is the only way we could get the `Metadata` struct to work here,
            # seehttps://github.com/signebedi/libreForms/issues/175.
            # print(dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0]))

            # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
            if mongodb.metadata_field_names['signature'] in record.columns:
                if options['_digitally_sign']:
                    record[mongodb.metadata_field_names['signature']].iloc[0] = set_digital_signature(username=record[mongodb.metadata_field_names['owner']].iloc[0],
                                                                        encrypted_string=record[mongodb.metadata_field_names['signature']].iloc[0], 
                                                                        base_string=config['signature_key'],
                                                                        ip=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['signature_ip'] if mongodb.metadata_field_names['metadata'] in record.columns and 'signature_ip' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,
                                                                        timestamp=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['signature_timestamp'] if mongodb.metadata_field_names['metadata'] in record.columns and 'signature_timestamp' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,)
                else:
                    record.drop(columns=[mongodb.metadata_field_names['signature']], inplace=True)

            # Added signature verification, see https://github.com/signebedi/libreForms/issues/144    
            if mongodb.metadata_field_names['approval'] in record.columns and record[mongodb.metadata_field_names['approval']].iloc[0]:
                filters = (
                getattr(User, config['visible_signature_field']) == getattr(current_user, config['visible_signature_field']),
                )
                manager = db.session.query(User).filter(*filters).first()

                try:
                    record[mongodb.metadata_field_names['approval']].iloc[0] = set_digital_signature(username=manager.username,
                            encrypted_string=record[mongodb.metadata_field_names['approval']].iloc[0],
                            base_string=config['approval_key'],
                            fallback_string=config['disapproval_key'],
                            ip=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['approval_ip'] if 'approval_ip' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,
                            timestamp=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['approval_timestamp'] if 'approval_timestamp' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,)

                except Exception as e: 
                    log.warning(f"LIBREFORMS - {e}")
                    record[mongodb.metadata_field_names['approval']].iloc[0] = None

            # we set nan values to None
            record.replace({np.nan:None}, inplace=True)

            # we drop Metadata from the form that's rendered for the user, since this data
            # is generally not intended to be visible
            record.drop(columns=[mongodb.metadata_field_names['metadata']], inplace=True)

            msg = Markup(f"<table role=\"presentation\"><tr><td><a href = '{config['domain']}/submissions/{form_name}/{document_id}/history'><button type=\"button\" class=\"btn btn-outline-success btn-sm\" style = \"margin-right: 10px;\">view document history</button></a></td>")

            # print (current_user.username)
            # print (record[mongodb.metadata_field_names['reporter']].iloc[0])

            if ((not checkKey(verify_group, '_deny_write') or not current_user.group in verify_group['_deny_write'])) or current_user.username == record[mongodb.metadata_field_names['owner']].iloc[0]:
                msg = msg + Markup(f"<td><a href = '{config['domain']}/submissions/{form_name}/{document_id}/edit'><button type=\"button\" class=\"btn btn-outline-success btn-sm\" style = \"margin-right: 10px;\">edit this document</button></a></td>")

            # if propagate_form_configs(form_name)['_form_approval'] and mongodb.metadata_field_names['approver'] in record.columns and record[mongodb.metadata_field_names['approver']].iloc[0] == getattr(current_user,config['visible_signature_field']):
            # new method for checking whether to allow approval, see https://github.com/libreForms/libreForms-flask/issues/155
            if (aggregate_approval_count()._id.str.contains(document_id) == True).sum() > 0:
                msg = msg + Markup(f"<td><a href = '{config['domain']}/submissions/{form_name}/{document_id}/review'><button type=\"button\" class=\"btn btn-outline-success btn-sm\" style = \"margin-right: 10px;\">go to form approval</button></a></td>")

            if propagate_form_configs(form_name)['_allow_pdf_download']:
                msg = msg + Markup(f"<td><a href = '{config['domain']}/submissions/{form_name}/{document_id}/download'><button type=\"button\" class=\"btn btn-outline-success btn-sm\" style = \"margin-right: 10px;\">download PDF</button></a></td>")

            # if set to True, this will suppress the left-bar nav, see
            # https://github.com/libreForms/libreForms-flask/issues/375
            ignore_menu = request.args.get('ignore_menu', False)

            # if ignore_menu is set to true, then that means we've just submitted a form... 
            # so, let's invite the user to submit another
            if ignore_menu:
                msg = msg + Markup(f"<td><a href = '{config['domain']}/forms/{form_name}'><button type=\"button\" class=\"btn btn-outline-success btn-sm\" style = \"margin-right: 10px;\">submit another form</button></a></td>")

            msg = msg + Markup ("</tr></table>")
            

            return render_template('submissions/submissions.html.jinja',
                type="submissions",
                name='Submissions',
                subtitle=form_name,
                submission=record,
                msg=msg,
                menu=None if ignore_menu else form_menu(checkFormGroup),
                badge_list=generate_username_badge_list(form_name),
                **standard_view_kwargs(),
            )


@bp.route('/<form_name>/<document_id>/history', methods=('GET', 'POST'))
@login_required
def render_document_history(form_name, document_id):

    if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)):
            flash(f'You do not have access to this view. ', "warning")
            return redirect(url_for('submissions.submissions_home'))

    else:


        try:
            options = propagate_form_configs(form=form_name)
            verify_group = options['_submission']
        except Exception as e: 
            flash('This form does not exist.', "warning")
            log.warning(f'{current_user.username.upper()} - {e}')
            return redirect(url_for('submissions.submissions_home'))

        # if checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']:
        #     flash('You do not have access to this resource.')
        #     return redirect(url_for('submissions.submissions_home'))


        # if checkKey(libreforms.forms, form_name) and \
        #     checkKey(libreforms.forms[form_name], '_enable_universal_form_access') and \
        #     libreforms.forms[form_name]['_enable_universal_form_access']:
        if propagate_form_configs(form=form_name)['_submission']['_enable_universal_form_access'] and not \
            (checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']):

            flash("Note: this form permits broad view access all its submissions. ", "info")
            record = pd.DataFrame(generate_full_document_history(form_name, document_id, user=None))
        else:
            record = pd.DataFrame(generate_full_document_history(form_name, document_id, user=current_user.username))


        if not isinstance(record, pd.DataFrame) or len(record) < 1:
            flash('This document does not exist.', "warning")
            return redirect(url_for('submissions.submissions_home'))
    
        else:

            # if a timestamp has been selected, then we set that to the page focus
            if request.args.get('Timestamp'):
                timestamp = request.args.get('Timestamp')
                # print(timestamp)
            # if a timestamp hasn't been passed in the get vars, then we default to the most recent
            else:
                # timestamp = record.iloc[-1, record.columns.get_loc(mongodb.metadata_field_names['timestamp'])]
                timestamp = record.columns[-1]
                # print('no timestamp found', timestamp)

            # I'm experimenting with creating the Jinja element in the backend ...
            # it makes applying certain logic -- like deciding which element to mark
            # as active -- much more straightforward. 
            breadcrumb = Markup(f'<ol style="--bs-breadcrumb-divider: \'>\';" class="breadcrumb {"" if config["dark_mode"] and not current_user.theme == "light" else "bg-transparent text-dark"}">')
            for item in record.columns:
                if item == timestamp:
                    breadcrumb = breadcrumb + Markup(f'<li class="breadcrumb-item active">{item}</li>')
                else:
                    breadcrumb = breadcrumb + Markup(f'<li class="breadcrumb-item"><a href="?Timestamp={item}" class="{"" if config["dark_mode"] and not current_user.theme == "light" else "text-dark"}">{item}</a></li>')
            breadcrumb = breadcrumb + Markup('</ol>')


            for val in record.columns:
                if val != timestamp:
                    # print(f'dropped {val}')
                    record.drop([val], axis=1, inplace=True)

            display_data = record.transpose()

            # print(display_data.iloc[0])

            # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
            if mongodb.metadata_field_names['signature'] in display_data.columns:
                if options['_digitally_sign']:
                    display_data[mongodb.metadata_field_names['signature']].iloc[0] = set_digital_signature(username=display_data[mongodb.metadata_field_names['owner']].iloc[0],
                                                                                encrypted_string=display_data[mongodb.metadata_field_names['signature']].iloc[0], 
                                                                                base_string=config['signature_key'],
                                                                                ip=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['signature_ip'] if mongodb.metadata_field_names['metadata'] in record.columns and 'signature_ip' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,
                                                                                timestamp=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['signature_timestamp'] if mongodb.metadata_field_names['metadata'] in record.columns and 'signature_timestamp' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,)

            # Added signature verification, see https://github.com/signebedi/libreForms/issues/144    
            if mongodb.metadata_field_names['approval'] in display_data.columns:
                if pd.notnull(display_data[mongodb.metadata_field_names['approval']].iloc[0]): # verify that this is not nan, see https://stackoverflow.com/a/57044299/13301284
                    
                    filters = (
                    getattr(User, config['visible_signature_field']) == getattr(current_user, config['visible_signature_field']),
                    )
                    manager = db.session.query(User).filter(*filters).first()
                    
                    # print(display_data[mongodb.metadata_field_names['approval']].iloc[0])
                    display_data[mongodb.metadata_field_names['approval']].iloc[0] = set_digital_signature(username=manager.username,
                                    encrypted_string=display_data[mongodb.metadata_field_names['approval']].iloc[0],
                                    base_string=config['approval_key'],
                                    fallback_string=config['disapproval_key'],
                                    ip=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['approval_ip'] if 'approval_ip' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,
                                    timestamp=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['approval_timestamp'] if 'approval_timestamp' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,)
                
                # After https://github.com/signebedi/libreForms/issues/145, adding this to ensure that
                # `Approval` is never None. 
                else:
                    # display_data.drop(columns=[mongodb.metadata_field_names['approval']], inplace=True)
                    display_data[mongodb.metadata_field_names['approval']].iloc[0] = None


            display_data.replace({np.nan:None}, inplace=True)

            # here we set a list of values to emphasize in the table because they've changed values
            t = get_record_of_submissions(form_name) 

            if not isinstance(t, pd.DataFrame):
                flash(f'Could not render document history for datetime {timestamp}. ', "warning")
                return redirect(url_for('submissions.render_document_history', form_name=form_name, document_id=document_id))

            t2 = t.loc[t._id == document_id] 
            t3 = dict(t2[[mongodb.metadata_field_names['journal']]].iloc[0].values[0]) 
            emphasize = [x for x in t3[timestamp].keys()]
            flash(f'The following values changed in this version and are emphasized below: {", ".join(emphasize)}. ', "info")

            msg = Markup(f"<table role=\"presentation\"><tr><td><a href = '{config['domain']}/submissions/{form_name}/{document_id}'><button type=\"button\" class=\"btn btn-outline-success btn-sm\" style = \"margin-right: 10px;\">go back to document</button></a></td>")

            # print (current_user.username)
            # print (record.transpose()[mongodb.metadata_field_names['reporter']].iloc[0])
            # print (record[mongodb.metadata_field_names['reporter']].iloc[0])

            if ((not checkKey(verify_group, '_deny_write') or not current_user.group in verify_group['_deny_write'])) or current_user.username == record[mongodb.metadata_field_names['owner']].iloc[0]:
                msg = msg + Markup(f"<td><a href = '{config['domain']}/submissions/{form_name}/{document_id}/edit'><button type=\"button\" class=\"btn btn-outline-success btn-sm\" style = \"margin-right: 10px;\">edit this document</button></a></td>")
            

            # if propagate_form_configs(form_name)['_form_approval'] and mongodb.metadata_field_names['approver'] in display_data.columns and display_data[mongodb.metadata_field_names['approver']].iloc[0] == getattr(current_user,config['visible_signature_field']):
            # new method for checking whether to allow approval, see https://github.com/libreForms/libreForms-flask/issues/155
            # print((aggregate_approval_count()._id.str.contains(document_id) == True).sum())
            if (aggregate_approval_count()._id.str.contains(document_id) == True).sum() > 0:
                msg = msg + Markup(f"<td><a href = '{config['domain']}/submissions/{form_name}/{document_id}/review'><button type=\"button\" class=\"btn btn-outline-success btn-sm\" style = \"margin-right: 10px;\">go to form approval</button></a></td>")

            # eventually, we may wish to add support for downloading past versions 
            # of the PDF, too; not just the current form of the PDF; the logic does 
            # seem to support this, eg. sending the `display_data`
            if propagate_form_configs(form_name)['_allow_pdf_download']:
                msg = msg + Markup(f"<td><a href = '{config['domain']}/submissions/{form_name}/{document_id}/download'><button type=\"button\" class=\"btn btn-outline-success btn-sm\" style = \"margin-right: 10px;\">download PDF</button></a></td>")

            msg = msg + Markup ("</tr></table>")

            return render_template('submissions/submissions.html.jinja',
                type="submissions",
                name='Submissions',
                subtitle=form_name,
                submission=display_data,
                emphasize=emphasize,
                breadcrumb=breadcrumb,
                msg=msg,
                menu=form_menu(checkFormGroup),
                **standard_view_kwargs(),
            )


@bp.route('/<form_name>/<document_id>/edit', methods=('GET', 'POST'))
@login_required
def render_document_edit(form_name, document_id):
    try:

        if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)):
                flash(f'You do not have access to this view. ', "warning")
                return redirect(url_for('submissions.submissions_home'))

        else:

            try:
                verify_group = propagate_form_configs(form=form_name)['_submission']
            except Exception as e: 
                flash('This form does not exist.', "warning")
                log.warning(f'{current_user.username.upper()} - {e}')
                return redirect(url_for('submissions.submissions_home'))

            # if checkKey(verify_group, '_deny_write') and current_user.group in verify_group['_deny_write']:
            #     flash('You do not have access to this resource.')
            #     return redirect(url_for('submissions.submissions_home'))


            # if checkKey(libreforms.forms, form_name) and \
            #     checkKey(libreforms.forms[form_name], '_enable_universal_form_access') and \
            #     libreforms.forms[form_name]['_enable_universal_form_access']:
            if propagate_form_configs(form=form_name)['_submission']['_enable_universal_form_access'] and not \
            (checkKey(verify_group, '_deny_write') and current_user.group in verify_group['_deny_write']):
                # flash("Warning: this form lets everyone view all its submissions. ")
                record = get_record_of_submissions(form_name=form_name,remove_underscores=False)

            else:

                record = get_record_of_submissions(form_name=form_name, user=current_user.username, remove_underscores=False)


            if not isinstance(record, pd.DataFrame):
                flash('This document does not exist.', "warning")
                return redirect(url_for('submissions.submissions_home'))
        
            else:
        
                options = propagate_form_configs(form_name)
                forms = propagate_form_fields(form_name, group=current_user.group)

                if not str(document_id) in record['_id'].values:
                    flash('You do not have edit access to this form.', "warning")
                    return redirect(url_for('submissions.submissions_home'))      

                record = record.loc[record['_id'] == str(document_id)]
                # we abort if the form doesn't exist
                if len(record.index)<1:
                    return abort(404)

                # here we convert the slice to a dictionary to use to override default values
                overrides = record.iloc[0].to_dict()
                # print(overrides)

                if request.method == 'POST':

                    # here we conduct a passworde check if digital signatures are enabled and password
                    # protected, see  https://github.com/signebedi/libreForms/issues/167
                    if config['require_password_for_electronic_signatures'] and options['_digitally_sign']:
                        password = request.form['_password']
                    
                        if not check_password_hash(current_user.password, password):
                            flash('Incorrect password.', "warning")
                            return redirect(url_for('submissions.render_document_edit', form_name=form_name, document_id=document_id))

                    
                    parsed_args = flaskparser.parser.parse(define_webarg_form_data_types(form_name, user_group=current_user.group, args=list(request.form)), request, location="form")
                    
                    # here we remove the _password field from the parsed args so it's not written to the database,
                    # see https://github.com/signebedi/libreForms/issues/167. 
                    if '_password' in parsed_args:
                        del parsed_args['_password']

                    # here we drop any elements that are not changes
                    parsed_args = check_args_for_changes(parsed_args, overrides)

                    # we may need to pass this as a string
                    parsed_args['_id'] = ObjectId(document_id)

                    # from pprint import pprint
                    # pprint(parsed_args)

                    digital_signature = encrypt_with_symmetric_key(current_user.certificate, config['signature_key']) if options['_digitally_sign'] else None

                    # here we pass a modification
                    mongodb.write_document_to_collection(parsed_args, form_name, reporter=current_user.username, modification=True, digital_signature=digital_signature,
                                                            ip_address=request.remote_addr if options['_collect_client_ip'] else None,)
                    
                    # if config['write_documents_asynchronously']:
                    #     import time, requests
                    #     while True:
                    #         requests.get(url_for('taskstatus', task_id=r.task_id))
                    #         print(r.task_id)
                    #         time.sleep(.1)

                    flash(f'{form_name} form successfully submitted, document ID {document_id}. ', "success")
                    if config['debug']:
                        flash(str(parsed_args), "info")


                    # log the update
                    log.info(f'{current_user.username.upper()} - updated \'{form_name}\' form, document no. {document_id}.')

                    # here we build our message and subject, customized for anonymous users
                    subject = f'{config["site_name"]} {form_name} Updated ({document_id})'
                    content = f"This email serves to verify that {current_user.username} ({current_user.email}) has just updated the {form_name} form, which you can view at {config['domain']}/submissions/{form_name}/{document_id}. {'; '.join(key + ': ' + str(value) for key, value in parsed_args.items() if key not in [mongodb.metadata_field_names['journal'], mongodb.metadata_field_names['metadata']]) if options['_send_form_with_email_notification'] else ''}"
                    
                    # and then we send our message
                    m = send_mail_async.delay(subject=subject, content=content, to_address=current_user.email, cc_address_list=rationalize_routing_list(form_name)) if config['send_mail_asynchronously'] else mailer.send_mail(subject=subject, content=content, to_address=current_user.email, cc_address_list=rationalize_routing_list(form_name), logfile=log)


                    # form processing trigger, see https://github.com/libreForms/libreForms-flask/issues/201    
                    if config['enable_form_processing']:
                        current_app.config['FORM_PROCESSING'].onUpdate(document_id=document_id, form_name=form_name)


                    # and then we redirect to the forms view page
                    return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id, ignore_menu=True))

                


                return render_template('app/forms.html.jinja', 
                    context=forms,                                          # this passes the form fields as the primary 'context' variable
                    name='Forms',
                    subtitle='Edit',
                    menu=form_menu(checkFormGroup),              # this returns the forms in libreform/forms to display in the lefthand menu
                    type="forms",       
                    default_overrides=overrides,
                    editing_existing_form=True,
                    options=options, 
                    filename = f'{form_name.lower().replace(" ","")}.csv' if options['_allow_csv_templates'] else False,
                    depends_on=compile_depends_on_data(form_name, user_group=current_user.group),
                    user_list = collect_list_of_users() if config['allow_forms_access_to_user_list'] else [],
                    # here we tell the jinja to include password re-entry for form signatures, if configured,
                    # see https://github.com/signebedi/libreForms/issues/167.
                    require_password=True if config['require_password_for_electronic_signatures'] and options['_digitally_sign'] else False,
                    **standard_view_kwargs(),
                    )

    except Exception as e: 
        log.warning(f"LIBREFORMS - {e}")
        flash(f'This form does not exist. {e}', "warning")
        return redirect(url_for('submissions.submissions_home'))

# this is a replica of render_document() above, just modified to check for 
# propagate_form_configs(form_name)['_form_approval'] and verify that the current_user
# is the form approver, otherwise abort. See https://github.com/signebedi/libreForms/issues/8.

@bp.route('/<form_name>/<document_id>/review', methods=['GET', 'POST'])
@login_required
def review_document(form_name, document_id):
    
    try:
        options = propagate_form_configs(form=form_name)
        verify_group = options['_submission']
        if not options['_form_approval']:
            return abort(404)
            # return redirect(url_for('submissions.render_document', form_name=form_name,document_id=document_id))

    except Exception as e: 
        flash('This form does not exist.', "warning")
        log.warning(f'{current_user.username.upper()} - {e}')
        return redirect(url_for('submissions.submissions_home'))


    record = get_record_of_submissions(form_name=form_name)

    if not isinstance(record, pd.DataFrame):
        flash('This document does not exist.', "warning")
        return redirect(url_for('submissions.submissions_home'))

    else:

        record = record.loc[record['_id'] == str(document_id)]
        # we abort if the form doesn't exist
        if len(record.index)<1:
            return abort(404)

        # if the approver verification doesn't check out
        # if not mongodb.metadata_field_names['approver'] in record.columns or not record[mongodb.metadata_field_names['approver']].iloc[0] or record[mongodb.metadata_field_names['approver']].iloc[0] != getattr(current_user,config['visible_signature_field']):
        # new method for checking whether to allow approval, see https://github.com/libreForms/libreForms-flask/issues/155
        if (aggregate_approval_count()._id.str.contains(document_id) == True).sum() < 1:
            return abort(404)

        if request.method == 'POST':

            # here we conduct a passworde check if digital signatures are enabled and password
            # protected, see  https://github.com/signebedi/libreForms/issues/167
            if config['require_password_for_electronic_signatures']:
                password = request.form['_password']
            
                if not check_password_hash(current_user.password, password):
                    flash('Incorrect password.', "warning")
                    return redirect(url_for('submissions.review_document', form_name=form_name, document_id=document_id))


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
                flash('You have approved this form. ', "success")
                digital_signature = encrypt_with_symmetric_key(current_user.certificate, config['approval_key']) if '_form_approval' in options else None
            elif approve == 'no':
                flash('You disapproved this form. ', "success")
                digital_signature = encrypt_with_symmetric_key(current_user.certificate, config['disapproval_key']) if '_form_approval' in options else None
            elif approve == 'pushback':
                flash('You returned this form without approval. ', "success")
                digital_signature = None

            else:
                flash('You have not approved this form. ', "success")
                digital_signature = None

            if comment == '':
                # set comment to None if the arrived empty
                comment = None
                flash('You have not added any comments to this form. ', "warning")
            else:
                flash('You have added comments to this form. ', "warning")
 

            # here we pull the default values to assess the POSTed values against
            overrides = record.iloc[0].to_dict()
                    
            # here we drop any elements that are not changed from the overrides
            verify_changes_to_approver = check_args_for_changes({mongodb.metadata_field_names['approver']: getattr(current_user, config['visible_signature_field'])}, overrides)
            verify_changes_to_approval = check_args_for_changes({mongodb.metadata_field_names['approval']: digital_signature}, overrides)
            verify_changes_to_approver_comment = check_args_for_changes({mongodb.metadata_field_names['approver_comment']: comment}, overrides)

           
            # presuming there is a change, write the change
            # if approve != 'no' or comment != '':

            mongodb.write_document_to_collection({'_id': ObjectId(document_id)}, form_name, 
                                                    reporter=current_user.username, 
                                                    modification=True,
                                                    # if these pass check_args_for_changes(), then pass values; else None
                                                    approver=verify_changes_to_approver[mongodb.metadata_field_names['approver']] if mongodb.metadata_field_names['approver'] in verify_changes_to_approver else None,
                                                    approval=verify_changes_to_approval[mongodb.metadata_field_names['approval']] if mongodb.metadata_field_names['approval'] in verify_changes_to_approval else None,
                                                    approver_comment=verify_changes_to_approver_comment[mongodb.metadata_field_names['approver_comment']] if mongodb.metadata_field_names['approver_comment'] in verify_changes_to_approver_comment else None,
                                                    ip_address=request.remote_addr if options['_collect_client_ip'] else None,)


            # form processing trigger, see https://github.com/libreForms/libreForms-flask/issues/201
            if config['enable_form_processing']:
                if approve == 'yes':
                    current_app.config['FORM_PROCESSING'].onApproval(document_id=document_id, form_name=form_name)
                elif approve == 'no':
                    current_app.config['FORM_PROCESSING'].onDisapproval(document_id=document_id, form_name=form_name)

            return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id))


            # if approval == '' and comment != '':
            #     flash('You have added a comment to this form. ')


        record.drop(columns=[mongodb.metadata_field_names['journal']], inplace=True)


        # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
        if mongodb.metadata_field_names['signature'] in record.columns:
            if options['_digitally_sign']:
                record[mongodb.metadata_field_names['signature']].iloc[0] = set_digital_signature(username=record[mongodb.metadata_field_names['owner']].iloc[0],
                                                                    encrypted_string=record[mongodb.metadata_field_names['signature']].iloc[0], 
                                                                    base_string=config['signature_key'],
                                                                    ip=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['signature_ip'] if mongodb.metadata_field_names['metadata'] in record.columns and 'signature_ip' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,
                                                                    timestamp=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['signature_timestamp'] if mongodb.metadata_field_names['metadata'] in record.columns and 'signature_timestamp' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,)
            else:
                record.drop(columns=[mongodb.metadata_field_names['signature']], inplace=True)
        # Added signature verification, see https://github.com/signebedi/libreForms/issues/144    
        if mongodb.metadata_field_names['approval'] in record.columns and record[mongodb.metadata_field_names['approval']].iloc[0]:
            try:

                filters = (
                getattr(User, config['visible_signature_field']) == getattr(current_user, config['visible_signature_field']),
                )
                manager = db.session.query(User).filter(*filters).first()


                # this needs to set the filter using eg. getattr(approver, config['visible_signature_field']) 
                record[mongodb.metadata_field_names['approval']].iloc[0] = set_digital_signature(username=manager.username,
                                                                    encrypted_string=record[mongodb.metadata_field_names['approval']].iloc[0],
                                                                    base_string=config['approval_key'],
                                                                    fallback_string=config['disapproval_key'],
                                                                    ip=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['approval_ip'] if 'approval_ip' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,
                                                                    timestamp=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['approval_timestamp'] if 'approval_timestamp' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,)
            except Exception as e: 
                log.warning(f"LIBREFORMS - {e}")
                record[mongodb.metadata_field_names['approval']].iloc[0] = None

        # we set nan values to None
        record.replace({np.nan:None}, inplace=True)

        # drop Metadata field since it's not generally meant to be viewed 
        record.drop(columns=[mongodb.metadata_field_names['metadata']], inplace=True)


        msg = Markup(f"<table role=\"presentation\"><tr><td><a href = '{config['domain']}/submissions/{form_name}/{document_id}'><button type=\"button\" class=\"btn btn-outline-success btn-sm\" style = \"margin-right: 10px;\">go back to document</button></a></td>")
        msg = msg + Markup(f"<td><a href = '{config['domain']}/submissions/{form_name}/{document_id}/history'><button type=\"button\" class=\"btn btn-outline-success btn-sm\" style = \"margin-right: 10px;\">view document history</button></a></td></tr></table>")

        # print (current_user.username)
        # print (record[mongodb.metadata_field_names['reporter']].iloc[0])


        return render_template('submissions/submissions.html.jinja',
            type="submissions",
            name='Submissions',
            subtitle=form_name,
            submission=record,
            msg=msg,
            form_approval=True,
            menu=form_menu(checkFormGroup),
            # here we tell the jinja to include password re-entry for form signatures, if configured,
            # see https://github.com/signebedi/libreForms/issues/167.
            require_password=True if config['require_password_for_electronic_signatures'] and '_form_approval' in options else False,
            **standard_view_kwargs(),
        )



# this generates PDFs
@bp.route('/<form_name>/<document_id>/download')
@login_required
def generate_pdf(form_name, document_id):

    try:
        test_the_form_options = propagate_form_configs(form=form_name)

    except Exception as e: 
        flash('This form does not exist.', "warning")
        log.warning(f'{current_user.username.upper()} - {e}')
        return redirect(url_for('submissions.render_document', form_name=form_name,document_id=document_id))

    if not test_the_form_options['_allow_pdf_download']:
        flash(f'This form does not have downloads enabled. ', "warning")
        return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id))


    if not checkGroup(group=current_user.group, struct=test_the_form_options):
        flash(f'You do not have access to this view. ', "warning")
        return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id))

    else:
        
        verify_group = test_the_form_options['_submission']

        if verify_group['_enable_universal_form_access'] and not \
            (checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']):
            record = get_record_of_submissions(form_name=form_name)

        else:

            record = get_record_of_submissions(form_name=form_name, user=current_user.username)


        if not isinstance(record, pd.DataFrame):
            flash('This document does not exist.', "warning")
            return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id))
    
        else:
    
            record = record.loc[record['_id'] == str(document_id)]
            # we abort if the form doesn't exist
            if len(record.index)<1:
                return abort(404)

            record.drop(columns=[mongodb.metadata_field_names['journal']], inplace=True)

            # Added signature verification, see https://github.com/signebedi/libreForms/issues/8
            if mongodb.metadata_field_names['signature'] in record.columns:
                if test_the_form_options['_digitally_sign']:
                    record[mongodb.metadata_field_names['signature']].iloc[0] = set_digital_signature(username=record[mongodb.metadata_field_names['owner']].iloc[0],
                                                                        encrypted_string=record[mongodb.metadata_field_names['signature']].iloc[0], 
                                                                        base_string=config['signature_key'], 
                                                                        return_markup=False,
                                                                        ip=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['signature_ip'] if mongodb.metadata_field_names['metadata'] in record.columns and 'signature_ip' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,
                                                                        timestamp=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['signature_timestamp'] if mongodb.metadata_field_names['metadata'] in record.columns and 'signature_timestamp' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,)
                else:
                    record.drop(columns=[mongodb.metadata_field_names['signature']], inplace=True)
            
            # Added signature verification, see https://github.com/signebedi/libreForms/issues/144    
            if mongodb.metadata_field_names['approval'] in record.columns and record[mongodb.metadata_field_names['approval']].iloc[0]:
                filters = (
                getattr(User, config['visible_signature_field']) == getattr(current_user, config['visible_signature_field']),
                )
                manager = db.session.query(User).filter(*filters).first()

                try:
                    record[mongodb.metadata_field_names['approval']].iloc[0] = set_digital_signature(username=manager.username,
                                encrypted_string=record[mongodb.metadata_field_names['approval']].iloc[0], 
                                base_string=config['approval_key'],
                                fallback_string=config['disapproval_key'],
                                return_markup=False,
                                ip=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['approval_ip'] if 'approval_ip' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,
                                timestamp=dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])['approval_timestamp'] if 'approval_timestamp' in dict(list(dict(record[mongodb.metadata_field_names['metadata']]).values())[0])else None,)

                except Exception as e: 
                    log.warning(f"LIBREFORMS - {e}")
                    record[mongodb.metadata_field_names['approval']].iloc[0] = None

            # we set nan values to None
            record.replace({np.nan:None}, inplace=True)

            # drop Metadata field since it's not generally meant to be viewed 
            record.drop(columns=[mongodb.metadata_field_names['metadata']], inplace=True)


            import libreforms
            import datetime
            from app.pdf import generate_pdf as make_pdf
            from app.pdf import v3_generate_pdf
            filename = f"{form_name}_{document_id}.pdf"


            # here we employ a context-bound temp directory to stage this file for download, see
            # discussion in app.tmpfiles and https://github.com/signebedi/libreForms/issues/169.
            from app.tmpfiles import temporary_directory
            with temporary_directory() as tempfile_path:


                fp = os.path.join(tempfile_path, filename)
                # document_name= f'{datetime.datetime.utcnow().strftime("%Y-%m-%d")}_{current_user.username}_{form_name}.pdf'

                # make_pdf( form_name=form_name, 
                #               data_structure=dict(record.iloc[0]), 
                #               username=current_user.username,
                #               document_name=fp,
                #               skel=propagate_form_fields(form=form_name) )

                # v3_generate_pdf(    form_name=form_name, 
                #                     form_data=dict(record.iloc[0]),
                #                     metadata=None,
                #                     document_id=document_id,
                #                     document_name=fp)
                    
                # Convert the HTML string to a PDF file

                from bs4 import BeautifulSoup
                from xhtml2pdf import pisa


                html_content = render_document(form_name=form_name, document_id=document_id)
                soup = BeautifulSoup(html_content, 'html.parser')
                content_table = str(soup.find(id='content-table'))

                with open(fp, "wb") as output_file:
                    pisa_status = pisa.CreatePDF(content_table, dest=output_file)

                if pisa_status.err:
                    flash("An error occurred while generating the PDF.", "warning")
                    return redirect(url_for('submissions.render_document', form_name=form_name,document_id=document_id))


                return send_from_directory(tempfile_path,
                                        filename, as_attachment=True)