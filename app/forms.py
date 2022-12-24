""" 
forms.py: implementation of views and base logic for form submission



"""

__name__ = "app.forms"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# import flask-related packages
from cmath import e
from fileinput import filename
from flask import Blueprint, flash, render_template, request, send_from_directory, \
                                send_file, redirect, url_for, current_app
from webargs import fields, flaskparser
from flask_login import current_user
from sqlalchemy.sql import text

# import custom packages from the current repository
import libreforms
from app import config, log, tempfile_path, mailer, mongodb
from app.models import User, db
from app.auth import login_required, session
from app.certification import encrypt_with_symmetric_key


# and finally, import other packages
import os
import pandas as pd



# this logic was written generally to support rationalize_routing_routing_list()
# by accepting a group name as a parameter and returning a list of email addresses
# belonging to each user in that group.
def get_list_of_emails_by_group(group, **kwargs):
    # query = f'SELECT email FROM {User.__tablename__} WHERE group = "{group}"'
    try:
        with db.engine.connect() as conn:
            # email_list = db.select(User.__tablename__).where(User.__tablename__.columns.group == group)
            # filter(model.Email == EmailInput)
            email_list = db.session.query(User).filter_by(group=group).all()
            # print([x.email for x in email_list])
            return [x.email for x in email_list]
            # return conn.execute(query).fetchall()

    except:
        return []

# this function is added to generate a list of email addresses for a given form to 
# send notifications once a form is submitted. See documentation of this feature at:
# https://github.com/signebedi/libreForms/issues/94, as well as documentation on
# routing and approval generally at: https://github.com/signebedi/libreForms/issues/8.
def rationalize_routing_routing_list(form_name):

    # first, we draw on parse_options() for the form in question
    # to apply defaults for missing values.
    routing_list = parse_options(form_name)['_routing_list']
    # print(routing_list)

    # then, we check if SMTP is enabled and, if not & the administrator has set a 
    # non-Nonetype value for _routing_list['type'], we then we log a warning but 
    # gracefully return an empty list
    if routing_list['type'] and not config['smtp_enabled']:
        log.warning('LIBREFORMS - administrators have set a routing list {routing_list} for form {form_name} but SMTP has not been enabled.')
        return []

    if not routing_list['type']:
        return []

    # if the form administrators have defined a static list of emails to receive 
    # form submission emails, then return that list here.
    elif routing_list['type'] == 'static':
        return routing_list['target']

    # this section is probably the most complex problem set; if groups are configured, 
    # we expect the value of 'target' to be a list of the groups to send notifications,
    # and we need to query for a list of emails for users in each group and return a 
    # concatenated list. For this, we wrote the get_list_of_emails_by_group() method,
    # defined above, and use list comprehension to generate the concatenated list.
    elif routing_list['type'] == 'groups':
        TEMP = []
        for group in routing_list['target']:
            TEMP = TEMP + get_list_of_emails_by_group(group)
        return TEMP

    # like in the case of static, if 'custom' is passed we are expecting that some kind
    # of custom logic defined in routing_list['target'] will return a list of emails, so we
    # pass those values here directly to the send_mail directive
    elif routing_list['type'] == 'custom':
        return routing_list['target']

    # default to returning an empty list to fail gracefully
    else:
        return []

def checkKey(dic, key):
    return True if dic and key in dic.keys() else False

def checkGroup(group, struct):
    return False if checkKey(struct, '_deny_groups') and group \
        in struct['_deny_groups'] else True

def form_menu(func):
    return [x for x in libreforms.forms.keys() if func(x, current_user.group)]

def checkFieldGroup(form, field, group):
    return False if checkKey(libreforms.forms[form][field], '_deny_groups') and group \
        in libreforms.forms[form][field]['_deny_groups'] else True

def checkFormGroup(form, group):
    return False if checkKey(parse_options(form), '_deny_groups') and group \
        in parse_options(form)['_deny_groups'] else True

def checkTableGroup(form, group):
    return False if checkKey(parse_options(form)['_table'], '_deny_groups') and group \
        in parse_options(form)['_table']['_deny_groups'] else True

# using parse_options to clean up some values here
def checkDashboardGroup(form, group):
    return False if checkKey(parse_options(form)['_dashboard'], '_deny_groups') and group \
        in parse_options(form)['_dashboard']['_deny_groups'] else True


# this function just compiles 'depends_on' data for each form
# to build a useful data tree that can be parsed by the jinja / javascript
def compile_depends_on_data(form=None, user_group=None):

    if form:

        RETURN = {}

        for field in libreforms.forms[form].keys():


            # if checkKey(libreforms.forms[form][field], '_group_access') and \
            #         (user_group in libreforms.forms[form][field]['_group_access']['deny']) \
            #         or (user_group not in libreforms.forms[form][field]['_group_access']['allow'] \
            #         and config['allow_all_groups_default'] == False):
            #     pass

            # else:

                # ignore form configs that start with _ but only select if the _depends_on has been set
                if not field.startswith("_") and "_depends_on" in libreforms.forms[form][field].keys():

                    element = libreforms.forms[form][field]['_depends_on']

                    if element[0] not in RETURN:
                        RETURN[element[0]] = {element[1]:[field]}

                    elif element[0] in RETURN and element[1] not in RETURN[element[0]].keys():
                        RETURN[element[0]][element[1]] = [field]

                    else:
                        RETURN[element[0]][element[1]].append(field)

        return RETURN

    return None

def collect_list_of_users(**kwargs): # we'll use the kwargs later to override default user fields
    query = f'SELECT username,email FROM {User.__tablename__}'
    # query = f'SELECT username FROM user'
    with db.engine.connect() as conn:
    # running the query
        # user_list = []
        # for x,y in conn.execute(query).fetchall():
        #     user_list.append(x,y)
        # return [x[0] for x in conn.execute(query).fetchall()]
        return [f"{x[0]} ({x[1]})" for x in conn.execute(query).fetchall()]


def generate_list_of_users(db=db):
    col = User.query.with_entities(User.username, User.email).distinct()
    return [(row.email, row.username) for row in col.all()]

def parse_form_fields(form=False, user_group=None, args=None):

    FORM_ARGS = {}  

    # print(list(args))

    # for field in args if args else libreforms.forms[form].keys():
    for field in libreforms.forms[form].keys():

        # we add this logic to allow us to iterate through the args 
        # provided and only parse these - and yet, not allow the provided
        # args to dictate which to parse for the form generally - as this
        # creates a risk that clients will pass maliciously formed requests;
        # instead, we start with the original form, and only proceed with
        # each field in the original form if it was passed as an arg. 
        if args and field not in args:
            pass
        
        elif field.startswith("_"):
            pass

        # here we ignore fields if the user's group has either been explicitly excluded from the field,
        # or if they are simply not included in the `allow` field and the we don't allow access by default.
        # elif user_group in libreforms.forms[form][field]['_group_access']['deny'] \
        #         or user_group not in libreforms.forms[form][field]['_group_access']['allow'] \
        #         and config['allow_all_groups_default'] == False:
        #     pass

        elif not checkGroup(user_group, libreforms.forms[form][field]):
            pass
        
        # adding this due to problems parsing checkboxes and (presumably) other
        # input types that permit multiple values
        elif libreforms.forms[form][field]['input_field']['type'] == "checkbox":
            FORM_ARGS[field] = fields.List(fields.String(),
                        required=libreforms.forms[form][field]['output_data']['required'],
                        validators=libreforms.forms[form][field]['output_data']['validators'],)

        elif libreforms.forms[form][field]['output_data']['type'] == "str":
            FORM_ARGS[field] = fields.Str(
                        required=libreforms.forms[form][field]['output_data']['required'],
                        validators=libreforms.forms[form][field]['output_data']['validators'],)
        elif libreforms.forms[form][field]['output_data']['type'] == "float":
            FORM_ARGS[field] = fields.Float(
                        required=libreforms.forms[form][field]['output_data']['required'],
                        validators=libreforms.forms[form][field]['output_data']['validators'],)
        elif libreforms.forms[form][field]['output_data']['type'] == "list":
            FORM_ARGS[field] = fields.List(fields.String(),
                        required=libreforms.forms[form][field]['output_data']['required'],
                        validators=libreforms.forms[form][field]['output_data']['validators'],)
        elif libreforms.forms[form][field]['output_data']['type'] == "int":
            FORM_ARGS[field] = fields.Int(
                        required=libreforms.forms[form][field]['output_data']['required'],
                        validators=libreforms.forms[form][field]['output_data']['validators'],)
        elif libreforms.forms[form][field]['output_data']['type'] == "date":
            FORM_ARGS[field] = fields.Date(
                        required=libreforms.forms[form][field]['output_data']['required'],
                        validators=libreforms.forms[form][field]['output_data']['validators'],)
        else:
            FORM_ARGS[field] = fields.Str(
                        required=libreforms.forms[form][field]['output_data']['required'],
                        validators=libreforms.forms[form][field]['output_data']['validators'],)

    return FORM_ARGS


# this is probably over-engineering and can be merged into other functions
# in the future. In short, it takes a progagate_forms() object and returns
# a by-field breakdown of how the data should be treated when collected and
# then when parsed (eg. take many inputs, parse as many outputs)
def reconcile_form_data_struct(form=False):

    # this function expencts a progagate_forms() object to be passed as
    # the form arg, as in `form = progagate_forms(form=form)``

    MATCH = {}

    for field in form.keys():

        if form[field]['input_field']['type'] in ['radio','checkbox', 'select']:
            if form[field]['output_data']['type'] in ['str', 'int', 'float']:
                MATCH[field] = {'many-to-one':len(form[field]['input_field']['content'])}
            elif form[field]['output_data']['type'] in ['list']:
                MATCH[field] = {'many-to-many':len(form[field]['input_field']['content'])}

        # here I opt to explicitly state the allowed other input data types
        # because I want the system to break when we add other data types 
        # for now; the API is still unstable, and I would prefer to have
        # hard checks in place to ensure predictable behavior
        elif form[field]['input_field']['type'] in ['text', 'password', 'date', 'hidden', 'number']: 
            if form[field]['output_data']['type'] in ['str', 'int', 'float']:
                MATCH[field] = {'one-to-one':len(form[field]['input_field']['content'])}
            elif form[field]['output_data']['type'] in ['list']:
                MATCH[field] = {'one-to-many':len(form[field]['input_field']['content'])}

        # also: what do we do about 'file' input/output types?

    return MATCH


# this function creates a list of the form fields 
# we want to pass to the web application
def progagate_forms(form=False, group=None):
    
    try:
        list_fields = libreforms.forms[form]

        VALUES = {}

        # here we drop the meta data fields   
        
        for field in list_fields.keys():
            if not field.startswith("_") and checkGroup(group, libreforms.forms[form][field]): # drop configs and fields we don't have access to
                VALUES[field] = list_fields[field]
        
        return VALUES
    except:
        return {}

# will be used to parse the configurations for a given form and - maybe most importantly
# as a gateway to apply default values to missing fields from the admin-defined form config.
def parse_options(form=False):
    
    try:
        # we start by reading the user defined forms into memory
        list_fields = libreforms.forms[form]

        # we define the default values for application-defined options
        OPTIONS = {
            "_dashboard": None,
            "_table": None,
            "_description": False,
            "_allow_repeat": False, 
            "_allow_uploads": False, 
            "_allow_csv_templates": False,
            "_suppress_default_values": False,  
            "_allow_anonymous_access": False,  
            "_smtp_notifications":False,
            '_deny_groups': [],
            '_enable_universal_form_access': False,
            '_submission': {
                '_enable_universal_form_access': False,
                '_deny_read': [],
                '_deny_write': [],
                },
            '_send_form_with_email_notification':False,
            '_routing_list':{
                'type': None,
                'target': [],
            },
            '_suppress_journal_from_views': True,
            "_allow_pdf_download": True, 
            "_allow_pdf_past_versions": True, 
            "_digitally_sign": False,
            "_form_approval": False
        }

        for field in list_fields.keys():
            if field.startswith("_"):

                # we run assertions when our data structure requires there to 
                # be certain attributes in a field config
                if field == '_submission':
                    assert (checkKey(list_fields[field],'_enable_universal_form_access'))
                    assert (checkKey(list_fields[field],'_deny_read'))
                    assert (checkKey(list_fields[field],'_deny_write'))

                if field in ['_routing_list', '_form_approval']:
                    assert (checkKey(list_fields[field],'type'))
                    assert (checkKey(list_fields[field],'target'))

                # we overwrite existing option values, and add new ones
                # based on the user defined configurations
                OPTIONS[field] = list_fields[field]
        
        return OPTIONS

    except:
        return {}



# added to enable routing of forms to managers for approval,
# see https://github.com/signebedi/libreForms/issues/8.
def verify_form_approval(form_name):
    approval = parse_options(form_name)['_form_approval']
    
    
    # this method entails selecting a field from the user
    # table assumes that this will be an email for an existing
    # user. See below for an example of what this would look like
    # in the form config:
    #                                   '_form_approval': {
    #                                     'type': 'user_field',
    #                                     'target': 'manager',}

    if approval and approval['type'] == 'user_field':

        with db.engine.connect() as conn:
            # manager = db.session.query(User).filter_by(email=current_user[approval['target']]).first()

            # unless we need to entire user object, this return value will probably be enough to get 
            # us the email of the user's approver ...
            # return getattr(current_user, approval['target'])

            filters = (
                User.email == getattr(current_user, approval['target']),
            )
            manager = db.session.query(User).filter(*filters).first()

            # print(vars(manager))
            
            return manager
            
    # '_form_approval': {
    #   'type': 'user-specified',
    #   'target': ['manager'],}

    # '_form_approval': {
    #   'type': 'static',
    #   'target': ['username@example.com'],}


    # '_form_approval': {
    #   'type': 'group',
    #   'target': ['manager'],}

    # '_form_approval': {
    #   'type': 'select_from_group',
    #   'target': 'manager',} # but could also be a different field type

    else:
        return None





bp = Blueprint('forms', __name__, url_prefix='/forms')

@bp.route(f'/')
@login_required
def forms_home():

    # print(generate_list_of_users()) 
    return render_template('app/forms.html', 
            msg="Select a form from the left-hand menu.",
            name="Form",
            type="forms",
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            menu=form_menu(checkFormGroup),
            config=config,
            user=current_user,
        ) 
        

# this creates the route to each of the forms
@bp.route(f'/<form_name>', methods=['GET', 'POST'])
@login_required
# @flaskparser.use_args(parse_form_fields(form=form_name), location='form')
def forms(form_name):


    if not checkGroup(group=current_user.group, struct=parse_options(form_name)):
        flash(f'You do not have access to this dashboard.')
        return redirect(url_for('forms.forms_home'))

    else:

        try:
            options = parse_options(form_name)
            forms = progagate_forms(form_name, group=current_user.group)


            if request.method == 'POST':
                
                # print([x for x in list(request.form)])
                # for x in list(request.form):
                #     print(x)
                parsed_args = flaskparser.parser.parse(parse_form_fields(form_name, user_group=current_user.group, args=list(request.form)), request, location="form")
                # parsed_args = {}

                # for item in libreforms.forms[form_name].keys():
                #     print(item)


                #     try: 
                #         if libreforms.forms[form_name][item]['input_field']['type'] == 'checkbox':
                                
                #             parsed_args[item] = str(request.form.getlist(item))
                            

                #         else:
                #             parsed_args[item] = str(request.form[item]) if libreforms.forms[form_name][item]['output_data']['type'] == 'str' else float(request.form[item])

                #     except:
                #         pass

                #     print(parsed_args[item])
                # print(parsed_args)

                digital_signature = encrypt_with_symmetric_key(current_user.certificate, config['signature_key']) if options['_digitally_sign'] else None
                
                approver = verify_form_approval(form_name)
                # print(approver)

                # here we insert the value and store the return value as the document ID
                document_id = mongodb.write_document_to_collection(parsed_args, form_name, 
                                reporter=current_user.username, 
                                digital_signature=digital_signature,
                                approver=getattr(approver, config['visible_signature_field']) if approver else None)

                flash(str(parsed_args))
                                
                log.info(f'{current_user.username.upper()} - submitted \'{form_name}\' form, document no. {document_id}.')
                
                # here we build our message and subject
                subject = f'{config["site_name"]} {form_name} Submitted ({document_id})'
                content = f"This email serves to verify that {current_user.username} ({current_user.email}) has just submitted the {form_name} form, which you can view at {config['domain']}/submissions/{form_name}/{document_id}. {'; '.join(key + ': ' + str(value) for key, value in parsed_args.items() if key != 'Journal') if options['_send_form_with_email_notification'] else ''}"
                                
                # and then we send our message
                current_app.config['MAILER'](subject=subject, content=content, to_address=current_user.email, cc_address_list=rationalize_routing_routing_list(form_name), logfile=log)

                if approver:
                    subject = f'{config["site_name"]} {form_name} Requires Approval ({document_id})'
                    content = f"This email serves to notify that {current_user.username} ({current_user.email}) has just submitted the {form_name} form for your review, which you can view at {config['domain']}/submissions/{form_name}/{document_id}/review."
                    current_app.config['MAILER'](subject=subject, content=content, to_address=approver.email, cc_address_list=rationalize_routing_routing_list(form_name), logfile=log)

                return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id))

            return render_template('app/forms.html', 
                context=forms,                                          # this passes the form fields as the primary 'context' variable
                name=form_name,                                         # this sets the name of the page for the page header
                menu=form_menu(checkFormGroup),              # this returns the forms in libreform/forms to display in the lefthand menu
                type="forms",       
                options=options, 
                config=config,
                notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
                filename = f'{form_name.lower().replace(" ","")}.csv' if options['_allow_csv_templates'] else False,
                user=current_user,
                depends_on=compile_depends_on_data(form_name, user_group=current_user.group),
                user_list = collect_list_of_users() if config['allow_forms_access_to_user_list'] else [],
                )

        except Exception as e:
            flash(f'This form does not exist. {e}')
            return redirect(url_for('forms.forms_home'))


# this is the download link for files in the temp directory
@bp.route('/download/<path:filename>')
@login_required
def download_file(filename):

    # this is our first stab at building templates, without accounting for nesting or repetition
    df = pd.DataFrame (columns=[x for x in progagate_forms(filename.replace('.csv', ''), group=current_user.group).keys()])

    fp = os.path.join(tempfile_path, filename)
    df.to_csv(fp, index=False)

    return send_from_directory(tempfile_path,
                            filename, as_attachment=True)