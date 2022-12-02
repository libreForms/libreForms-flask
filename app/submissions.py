
# import flask-related packages
from flask import current_app, Blueprint, g, flash, abort, render_template, \
    request, send_from_directory, send_file, redirect, url_for
from webargs import fields, flaskparser
from flask_login import current_user
from markupsafe import Markup
from bson import ObjectId

# import custom packages from the current repository
import libreforms
from app import display, log, tempfile_path, mailer, mongodb
from app.models import User, db
from app.auth import login_required, session
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


# a short method to just select changes and ignore anything that hasn't changed
# when editing an existing form
def check_args_for_changes(parsed_args, overrides):
    TEMP = {}

    del overrides['Journal'] # this is unnecessary space to iterate through...

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


bp = Blueprint('submissions', __name__, url_prefix='/submissions')


@bp.route('/all')
@login_required
def render_all_submissions():

        record = aggregate_form_data(user=None)
        # print(record)

        ### this is where we should run the data set through some 
        ### logic that checks _deny_read and removes forms for which
        ### the current user's group does not have access
        # verify_group = parse_options(form=form_name)['_submission']
        # if checkKey(verify_group, '_deny_read') and current_user.group in verify_group['_deny_read']:
        #     flash('You do not have access to this resource.')
        #     return redirect(url_for('submissions.submissions_home'))


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
            flash('This form has not received any submissions.')
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
            flash('This user has not made any submissions.')
            return redirect(url_for('submissions.submissions_home'))


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

        try:
            verify_group = parse_options(form=form_name)['_submission']
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

            record.drop(columns=['Journal'], inplace=True)

            msg = Markup(f"<a href = '{display['domain']}/submissions/{form_name}/{document_id}/history'>view document history</a>")

            # print (current_user.username)
            # print (record['Reporter'].iloc[0])

            if not (checkKey(verify_group, '_deny_write') or current_user.group in verify_group['_deny_write']) or current_user.username == record['Reporter'].iloc[0]:
                msg = msg + Markup(f"<br/><a href = '{display['domain']}/submissions/{form_name}/{document_id}/edit'>edit this document</a>")

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
            verify_group = parse_options(form=form_name)['_submission']
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

            if not (checkKey(verify_group, '_deny_write') or current_user.group in verify_group['_deny_write']) or current_user.username == record.transpose()['Reporter'].iloc[0]:
                msg = msg + Markup(f"<br/><a href = '{display['domain']}/submissions/{form_name}/{document_id}/edit'>edit this document</a>")

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

                    # here we pass a modification
                    mongodb.write_document_to_collection(parsed_args, form_name, reporter=current_user.username, modification=True)
                    
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