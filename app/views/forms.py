""" 
forms.py: implementation of views and base logic for form submission



"""

__name__ = "app.views.forms"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# import flask-related packages
from flask import Blueprint, flash, render_template, request, send_from_directory, \
                        send_file, redirect, url_for, current_app, abort, Response
from werkzeug.security import check_password_hash        
from werkzeug.utils import secure_filename
from webargs import fields, flaskparser
from flask_login import current_user, login_required
from sqlalchemy.sql import text
from markupsafe import Markup
from werkzeug.datastructures import ImmutableMultiDict

# import custom packages from the current repository
import libreforms
from app import config, log, mailer, mongodb
from app.models import User, db
from app.certification import encrypt_with_symmetric_key
from celeryd.tasks import send_mail_async
from app.scripts import convert_to_string
from app.decorators import required_login_and_password_reset

# wtf forms requirements
if config['enable_wtforms_test_features']:
    from flask_wtf import FlaskForm
    from wtforms import Form, StringField, IntegerField, BooleanField, FloatField, SubmitField, FieldList, DateField, FormField
    from wtforms.validators import DataRequired, Optional

# and finally, import other packages
import os, json, uuid, copy
import pandas as pd
import tempfile
import inspect
from cmath import e
from math import isnan
from fileinput import filename
from typing import List, Type, Dict, Any, Optional, Union
# from collections import defaultdict

# The kwargs we are passing to view function rendered jinja is getting out-
# of-hand. We can easily replace this with the following method as **kwargs, 
# see https://github.com/libreForms/libreForms-flask/issues/306.
def standard_view_kwargs():

    kwargs = {}

    kwargs['notifications'] = current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None
    kwargs['user'] = current_user if current_user.is_authenticated else None
    kwargs['config'] = config
    kwargs['stringify'] = convert_to_string
    kwargs['is_nan'] = isnan
    kwargs['len'] = len

    return kwargs

# this logic was written generally to support rationalize_routing_list()
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

    except Exception as e: 
        log.warning(f"LIBREFORMS - {e}")
        return []

# this function is added to generate a list of email addresses for a given form to 
# send notifications once a form is submitted. See documentation of this feature at:
# https://github.com/signebedi/libreForms/issues/94, as well as documentation on
# routing and approval generally at: https://github.com/signebedi/libreForms/issues/8.
def rationalize_routing_list(form_name):

    # first, we draw on propagate_form_configs() for the form in question
    # to apply defaults for missing values.
    routing_list = propagate_form_configs(form_name)['_routing_list']
    # print(routing_list)

    # then, we check if SMTP is enabled and, if not & the administrator has set a 
    # non-Nonetype value for _routing_list['type'], we then we log a warning but 
    # gracefully return an empty list
    if routing_list['type'] and not config['smtp_enabled']:
        log.warning(f'LIBREFORMS - administrators have set a routing list for {routing_list.target} for form {form_name} but SMTP has not been enabled.')
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
        return routing_list['taTemporaryDirectoryrget']

    # default to returning an empty list to fail gracefully
    else:
        return []


# The group of methods below are used to check group permissions to access certain resource.
# Yes, it's ugly. But it gets the job done by creating a set of different methods that return
# True or False if a resource can be accessed by a user of a given group.

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
    return False if checkKey(propagate_form_configs(form), '_deny_groups') and group \
        in propagate_form_configs(form)['_deny_groups'] else True

def checkTableGroup(form, group):
    return False if checkKey(propagate_form_configs(form)['_table'], '_deny_groups') and group \
        in propagate_form_configs(form)['_table']['_deny_groups'] else True

# using propagate_form_configs to clean up some values here
def checkDashboardGroup(form, group):
    # return False if checkKey(propagate_form_configs(form)['_dashboard'], '_deny_groups') and group \
    #     in propagate_form_configs(form)['_dashboard']['_deny_groups'] else True
    x = propagate_form_configs(form)['_dashboard']
    return True if x and len(x) > 0 else False # temporarily need to just let everything through w/o ACLs

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
    return [f"{x.username} {x.email}" for x in db.session.query(User).all()]



def generate_list_of_users(db=db):
    col = User.query.with_entities(User.username, User.email).distinct()
    return [(row.email, row.username) for row in col.all()]


# We have known for some time that we would need to re-write the form management tools to use
# flask-wtf instead of webargs - it will help with dependency management and more seamless 
# integration with other flask features. Initially, we used webargs because it was more 
# straightforward to define arbitrary form structures, but this approach may help bridge that
# gap, see discussion at https://github.com/libreForms/libreForms-flask/issues/30.
if config['enable_wtforms_test_features']:

    def create_dynamic_form(form_name: str, user_group: str, form_data: Optional[ImmutableMultiDict] = None) -> Union[Type[FlaskForm], Dict[str, Any]]:
        """
        Create a dynamic FlaskForm based on the given form_name and user_group.
        Optionally, process the form data if provided.

        :param form_name: The name of the form.
        :param user_group: The user group for which the form is being generated.
        :param form_data: Optional dictionary containing form data to process.
        :return: Returns the DynamicForm class if form_data is not provided, otherwise returns the processed form data as a dictionary.
        """
        def unpack_form_data(form_data: ImmutableMultiDict) -> Dict[str, Any]:
            """
            Unpack the ImmutableMultiDict form data to a simple dictionary, correctly handling list data types.

            :param form_data: ImmutableMultiDict containing form data.
            :return: A dictionary containing the unpacked form data.
            """
            # Restructure the ImmutableMultiDict
            parsed_data = {key: form_data.getlist(key) for key in form_data.keys()}
            
            # Unpack single-value lists
            parsed_data = {key: value[0] if len(value) == 1 else value for key, value in parsed_data.items()}

            return parsed_data

        form_data = unpack_form_data(form_data) if form_data else {}

        # Create the SimpleForm class
        class SimpleForm(FlaskForm):
            pass

        class SimpleStringForm(Form):
            field = StringField()

        # Add fields to the SimpleForm class based on the form data
        for field_name, field_value in form_data.items():
            if isinstance(field_value, list):
                setattr(SimpleForm, field_name, FieldList(FormField(SimpleStringForm), default=field_value))
            else:
                setattr(SimpleForm, field_name, StringField(default=field_value))

        # Process the form data, validate and store the values in a dictionary
        if form_data:
            form_instance = SimpleForm()
            if form_instance.validate():
                processed_data = {field_name: getattr(form_instance, field_name).data for field_name in form_data.keys()}
                return processed_data

        return SimpleForm

# webargs allows us to dynamically define form fields and assign them 
# data types with ease - this was one of the reasons we opted initially
# to use webargs, though we've been considering a pivot back to WTForms
# to avoid bloat, if this feature can be replicated, see discussion at
# https://github.com/signebedi/libreForms/issues/30.
def define_webarg_form_data_types(form=False, user_group=None, args=None):
    
    FORM_ARGS = {}  

    # options = propagate_form_configs[form]
    # if config['require_password_for_electronic_signatures'] and options['_digitally_sign']:
    FORM_ARGS['_password'] = fields.String(load_only=True)

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
            continue
        
        if field.startswith("_"):
            continue


        # here we ignore fields if the user's group has either been explicitly excluded from the field,
        # or if they are simply not included in the `allow` field and the we don't allow access by default.
        # elif user_group in libreforms.forms[form][field]['_group_access']['deny'] \
        #         or user_group not in libreforms.forms[form][field]['_group_access']['allow'] \
        #         and config['allow_all_groups_default'] == False:
        #     pass

        if not checkGroup(user_group, libreforms.forms[form][field]):            
            continue
        
        # here we pull and unpack the validators for a given form field
        v = libreforms.forms[form][field]['output_data']['validators'] if 'validators' in libreforms.forms[form][field]['output_data'] else []

        validators = [x[0] if type(x) == tuple else x for x in v]

        # validators = []        
        # for item in v:
        #     if type(item) == type(lambda x: x):
        #         validators.append(item)
        #     elif type(item) == tuple:
        #         validators.append(item[0])


        # adding this due to problems parsing checkboxes and (presumably) other
        # input types that permit multiple values
        if libreforms.forms[form][field]['input_field']['type'] == "checkbox":
            FORM_ARGS[field] = fields.List(fields.String(), required=libreforms.forms[form][field]['output_data']['required'], validate=validators)

        elif libreforms.forms[form][field]['output_data']['type'] == "str":
            FORM_ARGS[field] = fields.Str(required=libreforms.forms[form][field]['output_data']['required'], validate=validators)
        elif libreforms.forms[form][field]['output_data']['type'] == "float":
            FORM_ARGS[field] = fields.Float(required=libreforms.forms[form][field]['output_data']['required'], validate=validators)
        elif libreforms.forms[form][field]['output_data']['type'] == "list":
            FORM_ARGS[field] = fields.List(fields.String(), required=libreforms.forms[form][field]['output_data']['required'], validate=validators)
        # elif libreforms.forms[form][field]['output_data']['type'] == "dict":
            # FORM_ARGS[field] = fields.Dict(keys=fields.Str(), values=fields.Str(),
            # FORM_ARGS[field] = fields.Dict(
            #             required=libreforms.forms[form][field]['output_data']['required'], validate=validators,
            #             validators=validators)
        elif libreforms.forms[form][field]['output_data']['type'] == "int":
            FORM_ARGS[field] = fields.Int(required=libreforms.forms[form][field]['output_data']['required'], validate=validators)
        elif libreforms.forms[form][field]['output_data']['type'] == "date":
            FORM_ARGS[field] = fields.Date(required=libreforms.forms[form][field]['output_data']['required'], validate=validators)
        else:
            FORM_ARGS[field] = fields.Str(required=libreforms.forms[form][field]['output_data']['required'], validate=validators)


    return FORM_ARGS


# this is probably over-engineering and can be merged into other functions
# in the future. In short, it takes a propagate_form_fields() object and returns
# a by-field breakdown of how the data should be treated when collected and
# then when parsed (eg. take many inputs, parse as many outputs)
def reconcile_form_data_struct(form=False):

    # this function expencts a propagate_form_fields() object to be passed as
    # the form arg, as in `form = propagate_form_fields(form=form)``

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

# every form defined under libreforms/ contains a series of key-value pairs for fields and configs. 
# Fields constitute the actual input fields that end users will see and complete when completing forms.
# This method, largely analogous to the propagate_out_form_configs() method below, creates a list of 
# the form fields we want to pass to the web application and returns them.
def propagate_form_fields(form=False, group=None):
    
    try:

        # import libreforms as lf
        # list_fields = lf.forms[form].copy()
        list_fields = copy.deepcopy(libreforms.forms[form])


        # print(list_fields)

        VALUES = {}

        # here we drop the meta data fields   

        for field in list_fields.keys():
            if not field.startswith("_") and checkGroup(group, list_fields[field]): # drop configs and fields we don't have access to
                VALUES[field] = list_fields[field].copy()
                # if the content field is callable, then call it, see
                # https://github.com/libreForms/libreForms-flask/issues/305
                if callable(VALUES[field]['input_field']['content'][0]):
                    VALUES[field]['input_field']['content'] = VALUES[field]['input_field']['content'][0]()
                    # print ("ACTUAL VALS: ", VALUES[field]['input_field']['content'])


                # here we also add support for `apparent` form content, when administrators want the data to look 
                # different for the end user, than for the system backend, see the following issue for further discussion:
                # https://github.com/libreForms/libreForms-flask/issues/339
                if 'apparent_content' in VALUES[field]['input_field'] and callable(VALUES[field]['input_field']['apparent_content'][0]):
                    VALUES[field]['input_field']['apparent_content'] = VALUES[field]['input_field']['apparent_content'][0]()
                    # Bruh, we want to render these at runtime
                    # print("APPARENT VALS: ", VALUES[field]['input_field']['apparent_content'])
                
        return VALUES
    
    except Exception as e: 
        log.warning(f"LIBREFORMS - {e}")
        return {}

def render_form_display_name(form_name, form_config):
  
  if '_title' in form_config and '_subtitle' in form_config:
    return f"{form_config['_title']}: {form_config['_subtitle']}"

  elif '_title' in form_config:
    return form_config['_title']

  return form_name.replace('_',' ')


# every form defined under libreforms/ contains a series of key-value pairs for fields and configs. 
# Configs define unique behavior for each form and are denoted by a _ at the beginning of the key;
# for example `_dashboard` or `_allow_csv_uploads`. This method parses the configs for a given form and,
# more importantly, applies default values to missing fields from the admin-defined form config.
def propagate_form_configs(form=False):
    
    try:
        # we start by reading the user defined forms into memory
        list_fields = libreforms.forms[form]

        # we define the default values for application-defined options
        OPTIONS = {
            # we're doing something a lil strange with the _display_name field 
            # by calling ahead to values we have not yet iterated through... 
            # see https://github.com/libreForms/libreForms-flask/issues/333
            "_display_name": render_form_display_name(form, list_fields), 
            "_form_name": form, # add the form name as an option for self-referencing
            "_dashboard": None,
            "_table": None,
            "_description": False,
            "_allow_repeat": False, 
            "_allow_csv_uploads": False, 
            "_allow_csv_templates": False,
            "_suppress_default_values": False,  
            "_allow_anonymous_access": False,  
            "_smtp_notifications":False,
            '_deny_groups': [],
            "_allow_owner_deletion": True,
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
            "_form_approval": False,
            "_collect_client_ip":True,
            "_submission_view_summary_fields": [],
            '_on_creation':[],
            '_on_submission':[],
            '_on_update':[],
            '_on_approval':[],
            '_on_disapproval':[],
            '_on_duplication':[],
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

                # if field == '_dashboard':
                #     if len(list_fields[key]) < 1:
                #         list_fields[key] = None

                # these, if set, should always be a list
                if field in ['_on_creation', '_on_submission', '_on_update', '_on_approval', '_on_disapproval',]:
                    assert (isinstance(list_fields[field],list))

                # we overwrite existing option values, and add new ones
                # based on the user defined configurations
                OPTIONS[field] = list_fields[field]
        
        return OPTIONS

    except Exception as e: 
        log.warning(f"LIBREFORMS - {e}")
        return {}



# added to enable routing of forms to managers for approval,
# see https://github.com/signebedi/libreForms/issues/8.
def verify_form_approval(form_name):
    approval = propagate_form_configs(form_name)['_form_approval']
    
    
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
            approver = db.session.query(User).filter(*filters).first()

            # print(vars(manager))
            
            return approver
            
    # '_form_approval': {
    #   'type': 'user-specified',
    #   'target': 'manager',}

    # '_form_approval': {
    #   'type': 'static',
    #   'target': 'username@example.com',}

    if approval and approval['type'] == 'static':

        with db.engine.connect() as conn:
            # manager = db.session.query(User).filter_by(email=current_user[approval['target']]).first()

            # unless we need to entire user object, this return value will probably be enough to get 
            # us the email of the user's approver ...
            # return getattr(current_user, approval['target'])

            approver = db.session.query(User).filter(email=approval['target']).first()

            # print(vars(manager))
            
            return approver

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
@required_login_and_password_reset
def forms_home():

    # print(generate_list_of_users()) 
    return render_template('app/forms.html.jinja', 
            msg="Select a form from the left-hand menu.",
            name='Forms',
            subtitle="Home",
            type="forms",
            menu=form_menu(checkFormGroup),
            **standard_view_kwargs(),
        ) 
        

# this creates the route to each of the forms
@bp.route(f'/<form_name>', methods=['GET', 'POST'])
@required_login_and_password_reset
# @flaskparser.use_args(define_webarg_form_data_types(form=form_name), location='form')
def forms(form_name):


    if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)):
        flash(f'You do not have access to this form.', "warning")
        return redirect(url_for('forms.forms_home'))

    else:

        # try:
        options = propagate_form_configs(form_name)
        forms = propagate_form_fields(form_name, group=current_user.group)


        if request.method == 'POST':
            

            # here we conduct a passworde check if digital signatures are enabled and password
            # protected, see  https://github.com/signebedi/libreForms/issues/167
            if config['require_password_for_electronic_signatures'] and options['_digitally_sign']:
                password = request.form['_password']
            
                if not check_password_hash(current_user.password, password):
                    flash('Incorrect password.', "warning")
                    return redirect(url_for('forms.forms', form_name=form_name))


            if config['enable_wtforms_test_features']:

                # Generate the dynamic form class
                # FormClass = create_dynamic_form(form_name, current_user.group, form_data=list(request.form))
                # f_data = request.form.to_dict()
                # print(request.form)

 
                FormClass = create_dynamic_form(form_name, current_user.group, form_data=request.form)

                # Create an instance of the dynamic form class
                form_instance = FormClass()

                # Populate the form instance with submitted data
                form_instance.process(request.form)

                # Validate the form data
                # if form_instance.validate():

                parsed_args = form_instance.data
                # Proceed with form processing

            else:

                # print(list(request.form))
                parsed_args = flaskparser.parser.parse(define_webarg_form_data_types(form_name, user_group=current_user.group, args=list(request.form)), request, location="form")

            # here we remove the _password field from the parsed args so it's not written to the database,
            # see https://github.com/signebedi/libreForms/issues/167. 
            if '_password' in parsed_args:
                del parsed_args['_password']
            # print(parsed_args)                
            
            # parsed_args = {}

            # for item in libreforms.forms[form_name].keys():
            #     print(item)


            #     try: 
            #         if libreforms.forms[form_name][item]['input_field']['type'] == 'checkbox':
                            
            #             parsed_args[item] = str(request.form.getlist(item))
                        

            #         else:
            #             parsed_args[item] = str(request.form[item]) if libreforms.forms[form_name][item]['output_data']['type'] == 'str' else float(request.form[item])

            #     except Exception as e: 
            #         log.warning(f"LIBREFORMS - {e}")
            #         pass

            #     print(parsed_args[item])
            # print(parsed_args)

            digital_signature = encrypt_with_symmetric_key(current_user.certificate, config['signature_key']) if options['_digitally_sign'] else None
            
            approver = verify_form_approval(form_name)
            # print(approver)


            document_id = mongodb.write_document_to_collection(parsed_args, form_name, 
                            reporter=current_user.username, 
                            digital_signature=digital_signature,
                            approver=getattr(approver, config['visible_signature_field']) if approver else None,
                            ip_address=request.remote_addr if options['_collect_client_ip'] else None,)



            ## here we're trying out some logic to async submit forms, see 
            ## https://github.com/libreForms/libreForms-flask/issues/180
            # if config['write_documents_asynchronously']:
            #     import time, requests
            #     r = current_app.config['MONGODB_WRITER'].apply_async(kwargs={
            #                 'data':parsed_args, 
            #                 'collection_name':form_name, 
            #                 'reporter':current_user.username, 
            #                 'digital_signature':digital_signature,
            #                 'approver':getattr(approver, config['visible_signature_field']) if approver else None,
            #                 'ip_address':request.remote_addr if options['_collect_client_ip'] else None,})
            #     while True:
            #         a = requests.get(url_for('taskstatus', task_id=document_id.task_id))
            #         print(r.task_id)
            #         if a == 'COMPLETE': break
            #         time.sleep(.1)
            # else:
            #     # here we insert the value and store the return value as the document ID
            #     document_id = mongodb.write_document_to_collection(parsed_args, form_name, 
            #                 reporter=current_user.username, 
            #                 digital_signature=digital_signature,
            #                 approver=getattr(approver, config['visible_signature_field']) if approver else None,
            #                 ip_address=request.remote_addr if options['_collect_client_ip'] else None,)


            flash(f'{form_name} form successfully submitted, document ID {document_id}. ', "success")
            if config['debug']:
                flash(str(parsed_args), "info")


            log.info(f'{current_user.username.upper()} - submitted \'{form_name}\' form, document no. {document_id}.')
            
            # here we build our message and subject
            subject = f'{config["site_name"]} {form_name} Submitted ({document_id})'
            content = f"This email serves to verify that {current_user.username} ({current_user.email}) has just submitted the {form_name} form, which you can view at {config['domain']}/submissions/{form_name}/{document_id}. {'; '.join(key + ': ' + str(value) for key, value in parsed_args.items() if key != mongodb.metadata_field_names['journal']) if options['_send_form_with_email_notification'] else ''}"
                            
            # and then we send our message
            m = send_mail_async.delay(subject=subject, content=content, to_address=current_user.email, cc_address_list=rationalize_routing_list(form_name)) if config['send_mail_asynchronously'] else mailer.send_mail(subject=subject, content=content, to_address=current_user.email, cc_address_list=rationalize_routing_list(form_name), logfile=log)

            if approver:
                subject = f'{config["site_name"]} {form_name} Requires Approval ({document_id})'
                content = f"This email serves to notify that {current_user.username} ({current_user.email}) has just submitted the {form_name} form for your review, which you can view at {config['domain']}/submissions/{form_name}/{document_id}/review."
                m = send_mail_async.delay(subject=subject, content=content, to_address=approver.email, cc_address_list=rationalize_routing_list(form_name)) if config['send_mail_asynchronously'] else mailer.send_mail(subject=subject, content=content, to_address=approver.email, cc_address_list=rationalize_routing_list(form_name), logfile=log)

            # form processing trigger, see https://github.com/libreForms/libreForms-flask/issues/201
            if config['enable_form_processing']:
                current_app.config['FORM_PROCESSING'].onCreation(document_id=document_id, form_name=form_name)

            return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id, ignore_menu=True))


        return render_template('app/forms.html.jinja', 
            context=forms,                                          # this passes the form fields as the primary 'context' variable
            name='Forms',
            subtitle=form_name,
            menu=form_menu(checkFormGroup),              # this returns the forms in libreform/forms to display in the lefthand menu
            type="forms",       
            options=options, 
            filename = f'{form_name.lower().replace(" ","")}.csv' if options['_allow_csv_templates'] else False,
            depends_on=compile_depends_on_data(form_name, user_group=current_user.group),
            user_list = collect_list_of_users() if config['allow_forms_access_to_user_list'] else [],
            # here we tell the jinja to include password re-entry for form signatures, if configured,
            # see https://github.com/signebedi/libreForms/issues/167.
            require_password=True if config['require_password_for_electronic_signatures'] and options['_digitally_sign'] else False,
            # callable=callable,
            **standard_view_kwargs(),
            )

        # except Exception as e: 

        #     transaction_id = str(uuid.uuid1())
        #     log.warning(f"LIBREFORMS - {e}", extra={'transaction_id': transaction_id})
        #     flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ", 'warning')

        #     # log.warning(f"LIBREFORMS - {e}")
        #     # flash(f'There was an issue processing your request. {e}', "warning")
        #     return redirect(url_for('forms.forms_home'))

# this is the upload route for submitting forms via CSV, see
# https://github.com/libreForms/libreForms-flask/issues/184
@bp.route(f'/<form_name>/upload', methods=['GET', 'POST'])
@required_login_and_password_reset
def upload_forms(form_name):
    # if request.method == 'POST':

    if not checkGroup(group=current_user.group, struct=propagate_form_configs(form_name)):
        flash(f'You do not have access to this form.', "warning")
        return redirect(url_for('forms.forms_home'))

    try:
        options = propagate_form_configs(form_name)
        forms = propagate_form_fields(form_name, group=current_user.group)
        assert options['_allow_csv_uploads']

    except Exception as e:
        # print(e)
        return redirect(url_for('forms.forms', form_name=form_name))

    if request.method == 'POST':


        try:
            
            # collect the file name
            file = request.files['file']

            # get file size and assert
            file_size = len(file.read())
            assert config['max_form_upload_size'] >= file_size, f"File upload size is too large. Max file size is {config['max_form_upload_size']} bytes."

            # Reset the file pointer to the beginning of the file
            file.seek(0)

            # print(file.filename)
            # assert we've passed a file name
            assert file.filename != '', "Please select a file to upload"

            with tempfile.TemporaryDirectory() as tmpdirname:

                filepath = secure_filename(file.filename) # first remove any banned chars
                filepath = os.path.join(tmpdirname, file.filename)

                if not config['allow_form_uploads_as_excel']:
                    assert file.filename.lower().endswith(".csv",), 'Please upload a CSV file.'
                else:
                    assert file.filename.lower().endswith(('.csv', '.xlsx', '.xls')), 'Please upload a CSV or Excel file.'

                # Save a local copy of the file
                file.save(filepath)

                if file.filename.lower().endswith('.xlsx'):
                    excel_file = pd.ExcelFile(filepath, engine='openpyxl')

                    # ensure the excel document only has one sheet
                    assert len(excel_file.sheet_names) == 1, "Your submitted Excel file has too many sheets. To avoid breaking assumptions, please only submit Excel files with a single sheet."

                    # Read a specific sheet as a DataFrame
                    df = excel_file.parse()

                elif file.filename.lower().endswith('.xls'):
                    excel_file = pd.ExcelFile(filepath, engine='xlrd')

                    # ensure the excel document only has one sheet
                    assert len(excel_file.sheet_names) == 1, "Your submitted Excel file has too many sheets. To avoid breaking assumptions, please only submit Excel files with a single sheet."

                    # Read a specific sheet as a DataFrame
                    df = excel_file.parse()


                else:
                    # print('csv')
                    df = pd.read_csv(filepath)
                    
                # print(df)

                for x in forms.keys(): # a minimalist common sense check
                    assert x in df.columns, f"{x} not in columns"
                    

        except Exception as e: 
            # log.warning(f"{current_user.username.upper()} - {str(e)}")
            # flash(str(e), 'warning')

            transaction_id = str(uuid.uuid1())
            log.warning(f"{current_user.username.upper()} - {e}", extra={'transaction_id': transaction_id})
            flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ", 'warning')

            return redirect(url_for('forms.upload_forms', form_name=form_name))


        for index, row in df.iterrows():
            # print(row)
        
            try:
                ### eventually add content validators for each cell here

                # drop any stray columns
                row.drop(labels=[x for x in row.index if x not in forms.keys()], inplace=True)

                # construct a dictionary payload
                data = row.to_dict()

                # write to database
                document_id = mongodb.write_document_to_collection(data, form_name, 
                                reporter=current_user.username, 
                                ip_address=request.remote_addr if options['_collect_client_ip'] else None,)

                URL = f"{config['domain']}/submissions/{form_name}/{document_id}"
                flash(Markup(f"Successfully created new form, which can be accessed at <a href=\"{URL}\">{URL}</a>"), 'info')

            except Exception as e: 

                transaction_id = str(uuid.uuid1())
                log.warning(f"{current_user.username.upper()} - {e}", extra={'transaction_id': transaction_id})
                flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ", 'warning')

                # log.warning(f"{current_user.username.upper()} - {str(e)}")
                # flash(str(e), 'warning')

    return render_template('app/upload_form.html.jinja', 
        name='Forms',
        subtitle=form_name,
        menu=form_menu(checkFormGroup),
        type="forms",       
        filename = f'{form_name.lower().replace(" ","")}.csv' if options['_allow_csv_templates'] else False,
        user_list = collect_list_of_users() if config['allow_forms_access_to_user_list'] else [],
        **standard_view_kwargs(),
        )

@bp.route(f'/lookup', methods=['GET', 'POST'])
@required_login_and_password_reset
def generate_lookup():

    if request.method == 'POST':

        document_id = request.json['document_id']
        form_name = request.json['form_name']

        data = mongodb.get_document_as_dict(form_name, document_id)

        if isinstance(data,dict):

            data = {key.replace('_',' '):convert_to_string(value) for key, value in data.items() if key not in mongodb.metadata_fields(exclude_id=True)}
            # print(data)
            return Response(json.dumps(data), status=config['success_code'], mimetype='application/json')

        return Response(json.dumps({'status':'failure'}), status=config['error_code'], mimetype='application/json')

    return abort(404)

@bp.route(f'/lint', methods=['GET', 'POST'])
@required_login_and_password_reset
def lint_field():


    def validate_option(form, field, value):

        # here we set the validators field, if it exists
        validators = libreforms.forms[form][field]['output_data']['validators'].copy() if 'validators' in libreforms.forms[form][field]['output_data'] else []

        for validator in validators:

            # admins can pass validators as tuples where the second value is the error msg. 
            # Here, we unpack if they are tuples.
            if type(validator) == tuple:
                (validator, error_msg) = validator

            else:
                error_msg = f"{field} failed validation." 


            # print(str(validator))
            try:
                assert validator(value), error_msg

            except Exception as e:
                return str(e)

        return True

    if request.method == 'POST':
        # print(request)

        # string = request.json['string']
        form = request.json['form'] 
        field = request.json['field']
        value = request.json['value']

        # print(string)

        v = validate_option(form, field, value)

        if type(v) == bool:
            return Response(json.dumps({'status':'success'}), status=config['success_code'], mimetype='application/json')

        return Response(json.dumps({'status':'failure', 'msg': v}), status=config['error_code'], mimetype='application/json')

    return abort(404)


# this is the download link for files in the temp directory
@bp.route('/download/<path:filename>')
@required_login_and_password_reset
def download_file(filename):

    # this is our first stab at building templates, without accounting for nesting or repetition
    df = pd.DataFrame (columns=[x for x in propagate_form_fields(filename.replace('.csv', ''), group=current_user.group).keys()])

    # here we employ a context-bound temp directory to stage this file for download, see
    # discussion in app.tmpfiles and https://github.com/signebedi/libreForms/issues/169.
    from app.tmpfiles import temporary_directory
    with temporary_directory() as tempfile_path:

        # appending `template` to the start to avoid confusion with other downloads
        template_filename = "template_"+filename

        fp = os.path.join(tempfile_path, template_filename)
        df.to_csv(fp, index=False)

        return send_from_directory(tempfile_path,
                                template_filename, as_attachment=True)