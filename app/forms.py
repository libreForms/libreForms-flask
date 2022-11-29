# import flask-related packages
from cmath import e
from fileinput import filename
from flask import Blueprint, g, flash, render_template, request, send_from_directory, send_file, redirect, url_for
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
            #         and display['allow_all_groups_default'] == False):
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
        #         and display['allow_all_groups_default'] == False:
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

# will be used to parse options for a given form
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
        }

        for field in list_fields.keys():
            if field.startswith("_"):
                # we overwrite existing option values, and add new ones
                # based on the user defined configurations
                OPTIONS[field] = list_fields[field]
        
        return OPTIONS

    except:
        return {}


bp = Blueprint('forms', __name__, url_prefix='/forms')

@bp.route(f'/')
@login_required
def forms_home():

    # print(generate_list_of_users()) 
    return render_template('app/forms.html', 
            msg="Select a form from the left-hand menu.",
            name="Form",
            type="forms",
            menu=form_menu(checkFormGroup),
            display=display,
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

                # here we insert the value and store the return value as the document ID
                document_id = mongodb.write_document_to_collection(parsed_args, form_name, reporter=current_user.username)

                flash(str(parsed_args))
                log.info(f'{current_user.username.upper()} - submitted \'{form_name}\' form, document no. {document_id}.')
                mailer.send_mail(subject=f'{display["site_name"]} {form_name} Submitted ({document_id})', content=f"This email serves to verify that {current_user.username} ({current_user.email}) has just submitted the {form_name} form, which you can view at {display['domain']}/submissions/{form_name}/{document_id}. {'; '.join(key + ': ' + str(value) for key, value in parsed_args.items()) if options['_send_form_with_email_notification'] else ''}", to_address=current_user.email, logfile=log)
                
                
                return redirect(url_for('submissions.render_document', form_name=form_name, document_id=document_id))

            return render_template('app/forms.html', 
                context=forms,                                          # this passes the form fields as the primary 'context' variable
                name=form_name,                                         # this sets the name of the page for the page header
                menu=form_menu(checkFormGroup),              # this returns the forms in libreform/forms to display in the lefthand menu
                type="forms",       
                options=options, 
                display=display,
                filename = f'{form_name.lower().replace(" ","")}.csv' if options['_allow_csv_templates'] else False,
                user=current_user,
                depends_on=compile_depends_on_data(form_name, user_group=current_user.group),
                user_list = collect_list_of_users() if display['allow_forms_access_to_user_list'] else [],
                )

        except Exception as e:
            flash(f'This form does not exist. {e}')
            return redirect(url_for('forms.forms_home'))


# this is the download link for files in the temp directory
@bp.route('/download/<path:filename>')
@login_required
def download_file(filename):

    # this is our first stab at building templates, without accounting for nesting or repetition
    df = pd.DataFrame (columns=[x for x in progagate_forms(filename.replace('.csv', '')).keys()], group=current_user.group)

    fp = os.path.join(tempfile_path, filename)
    df.to_csv(fp, index=False)

    return send_from_directory(tempfile_path,
                            filename, as_attachment=True)