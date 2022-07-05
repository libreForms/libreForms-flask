# import flask-related packages
from cmath import e
from fileinput import filename
from flask import Blueprint, g, flash, render_template, request, send_from_directory
from webargs import fields, flaskparser
from flask_login import current_user

# import custom packages from the current repository
import libreforms, mongodb
from app import display, log
from app.auth import login_required, session

# and finally, import other packages
import os
import pandas as pd


def init_tmp_fs():
# if application tmp/ path doesn't exist, make it
    if  os.path.exists ("app/static/tmp/"):
        os.system("rm -rf app/static/tmp/")
    os.mkdir('app/static/tmp/')    
    log.info('SYSTEM - created static/tmp directory.')


def generate_csv_templates(form=None):
    if form:
        if parse_options(form=form)['_allow_csv_templates']:

            # this is our first stab at building templates, without accounting for nesting or repetition
            df = pd.DataFrame (columns=[x for x in progagate_forms(form).keys()])
            # placeholder for nesting
            # placeholder for repetition
            df.to_csv(f'app/static/tmp/{form.lower().replace(" ","")}.csv', index=False)
            log.info(f'LIBREFORMS - created app/static/tmp/{form.lower().replace(" ","")}.csv.')
    else:
        pass

def handle_csv_upload(csv_path, form=None):
    pass


def parse_form_fields(form=False):

    FORM_ARGS = {}           

    for field in libreforms.forms[form].keys():

        if field.startswith("_"):
            pass
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
            FORM_ARGS[field] = fields.Str(
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

        if form[field]['input_field']['type'] in ['radio','checkbox']:
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
def progagate_forms(form=False):
    
    list_fields = libreforms.forms[form]

    VALUES = {}

    # here we drop the meta data fields   
    
    for field in list_fields.keys():
        if not field.startswith("_"): 
            VALUES[field] = list_fields[field]
    
    return VALUES

# will be used to parse options for a given form
def parse_options(form=False):
        
    # we start by reading the user defined forms into memory
    list_fields = libreforms.forms[form]

    # we define the default values for application-defined options
    OPTIONS = {
        "_dashboard": False,
        "_allow_repeat": False, 
        "_allow_uploads": False, 
        "_allow_csv_templates": False,
        "_suppress_default_values": False,  
    }

    for field in list_fields.keys():
        if field.startswith("_"):
            # we overwrite existing option values, and add new ones
            # based on the user defined configurations
            OPTIONS[field] = list_fields[field]
    
    return OPTIONS

# read database password file, if it exists
if os.path.exists ("mongodb_pw"):
    with open("mongodb_pw", "r+") as f:
        mongodb_pw = f.read().strip()
else:  
    mongodb_pw=None
# initialize mongodb database
mongodb = mongodb.MongoDB(mongodb_pw)


# set up form handling
init_tmp_fs()
for form in libreforms.forms.keys():
    generate_csv_templates(form)


bp = Blueprint('forms', __name__, url_prefix='/forms')

@bp.route(f'/')
@login_required
def forms_home():
    return render_template('app/index.html', 
            msg="Select a form from the left-hand menu.",
            name="Form",
            type="forms.forms",
            menu=[x for x in libreforms.forms.keys()],
            display=display,
            user=current_user,
        ) 
        

# this creates the route to each of the forms
@bp.route(f'/<form_name>', methods=['GET', 'POST'])
@login_required
def forms(form_name):

    try:
        options = parse_options(form_name)
        forms = progagate_forms(form_name)

        if request.method == 'POST':
            parsed_args = flaskparser.parser.parse(parse_form_fields(form_name), request, location="form")
            mongodb.write_document_to_collection(parsed_args, form_name, reporter=current_user.username)
            flash(str(parsed_args))
            log.info(f'{current_user.username.upper()} - submitted \'{form_name}\' form.')

        return render_template('app/index.html', 
            context=forms,                                          # this passes the form fields as the primary 'context' variable
            name=form_name,                                         # this sets the name of the page for the page header
            menu=[x for x in libreforms.forms.keys()],              # this returns the forms in libreform/forms to display in the lefthand menu
            type="forms.forms",       
            options=options, 
            display=display,
            filename = f'{form_name.lower().replace(" ","")}.csv' if options['_allow_csv_templates'] else False,
            user=current_user,
            )

    except Exception as e:
        return render_template('app/index.html', 
            form_not_found=True,
            msg=e,
            name="404",
            type="forms.forms",
            menu=[x for x in libreforms.forms.keys()],
            display=display,
            user=current_user,
        )

# this is the download link for files in the static/tmp directory
@bp.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory('static/tmp',
                               filename, as_attachment=True)
