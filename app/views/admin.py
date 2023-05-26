"""
admin.py: admin console and logic


At it's core, the admin console is a place for admin users to manage the app's behavior. This 
is rooted in a three-step approach for app configuration: `app.config`, `app.config_overrides`,
and `libreforms.env`. The `app.config` file sets the application defaults. The `app.config_overrides`
file, as the name suggests, can be used to override the default configurations. So it takes a higher
precedence than the default `app.configs` file. Finally, the system searchs for a `libreforms.env` 
file, which takes precedence over the other two files. This admin script will work primarily with 
that libreforms.env file and, when you're running gunicorn, will automatically reload the WSGI
server when it detects changes to that file. We are still working through how to get the 
werkzeug WSGI server to reload when it detects changes to that file, too. For further discussion, 
see https://github.com/libreForms/libreForms-flask/issues/255.

Generally, the admin console will try to provide the following features, though some of the
features themselves are `far horizon` features that are not currently planned in the libreForms-flask
backlog, see https://github.com/libreForms/libreForms-flask/issues/39.

Data management
    Database externalization
    User and Group/Role Configuration
    Log Management
    Signing Key rotation
    Restart application

Config management
    Add LDAP / OAuth Authentication
    SMTP Configuration
    File System Configuration (set max file upload size)
    REST API privileges (read-only or full CRUD)
    External forms (allowed or not)
    Data backup, rotation, management, retention, restore-from-backup
    Look and Feel (display overrides)

References:
- Edit configs using dotenv https://github.com/libreForms/libreForms-flask/issues/233
- Add admin console support https://github.com/libreForms/libreForms-flask/issues/28
- Add `log` view https://github.com/libreForms/libreForms-flask/issues/80
- Add `signing key` view https://github.com/libreForms/libreForms-flask/issues/81
- Add `user / group management` view https://github.com/libreForms/libreForms-flask/issues/82
- Add `data migration` view https://github.com/libreForms/libreForms-flask/issues/130
- Facilitate form ~deletion~ https://github.com/libreForms/libreForms-flask/issues/186
- Add `form management` view https://github.com/libreForms/libreForms-flask/issues/187
- Add `mail server` view https://github.com/libreForms/libreForms-flask/issues/234
- Add a restart app option to the admin view https://github.com/libreForms/libreForms-flask/issues/311
"""

__name__ = "app.views.admin"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.1.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from flask import current_app, Blueprint, g, flash, abort, render_template, \
    request, send_from_directory, send_file, redirect, url_for
from app.views.auth import session
from app.config import config
from flask_login import current_user, login_required
from functools import wraps
import string
from app.views.forms import standard_view_kwargs
from app.log_functions import aggregate_log_data
from app.mongo import mongodb
from markupsafe import Markup
import dotenv
import libreforms
import uuid

# requirements for bulk email management
from app.models import User, Signing, db
from app.certification import generate_symmetric_key
import app.signing as signing
from werkzeug.utils import secure_filename
import pandas as pd
import os, tempfile, datetime, re, random, string
from app import log, mailer
from werkzeug.security import generate_password_hash
from celeryd.tasks import send_mail_async, restart_app_async
from app.scripts import prettify_time_diff, convert_to_string, mask_string

# borrows from and extends the functionality of flask_login.login_required, see
# https://github.com/maxcountryman/flask-login/blob/main/src/flask_login/utils.py.
def is_admin(func):

    @wraps(func)
    def decorated_view(*args, **kwargs):

        # print(current_user)

        if current_app.config.get("LOGIN_DISABLED"):
            pass

        elif not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        
        if not current_user.group == config['admin_group']:
            return abort(404)
        
        return func(*args, **kwargs)
        
    return decorated_view



def compile_admin_views_for_menu():
    
    views = []

    # here we build a list of admin views, excluding some
    for view in [key for key in current_app.view_functions if key.startswith('admin') and not key in [  'admin.restart_now', 
                                                                                                        'admin.toggle_user_active_status', 
                                                                                                        'admin.generate_random_password',
                                                                                                        'admin.toggle_signature_active_status',
                                                                                                        'admin.edit_profile',
                                                                                                        'admin.generate_api_key',
                                                                                                        'admin.toggle_form_deletion_status',
                                                                                                        ]]:
        v = view.replace('admin_','')
        v = v.replace('admin.','')
        v = v.replace('_',' ')
        v = string.capwords(v)
        views.append([view,v])

    # print (views)
    return views


def dotenv_overrides(env_file='libreforms.env',restart_app=True,**kwargs):

    try:
        # Load existing configuration variables
        existing_config = dotenv.dotenv_values(env_file)
        # print(existing_config)

        # overwrite with old configs
        for key,value in existing_config.items():
            # print(key,value)
            dotenv.set_key(env_file, key.upper(), value)

        # Overwrite with new configuration
        for key, value in kwargs.items():
            # print(key,value)
            # here we re-type bools to integer representations
            if type(value) == bool:
                value = "True" if value else 'False'
            dotenv.set_key(env_file, key.upper(), value)

        # here we restart the application on config change 
        if restart_app:
            restart_app_async.delay() # will not run if celery is not running.

        log.info(f'{current_user.username.upper()} - updated app dotenv configs: {convert_to_string(kwargs)}.')

        return True

    except Exception as e:
        # print(e)
        log.error (f'{current_user.username.upper()} - {e}', extra={'transaction_id': transaction_id})
        flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ", 'warning')
        return False



def compile_form_data(form_names=[], include_deleted=True, sort=True):
    df = pd.DataFrame(columns = ['form', 'id', 'owner', 'timestamp', 'content_summary', 'time_since_last_edit', 'active'])
    current_time = datetime.datetime.now()


    if not isinstance(form_names,list) or len(form_names) < 1:
        form_names = libreforms.forms

    for form_name in form_names:
        temp = mongodb.new_read_documents_from_collection(form_name)

        if not isinstance(temp,pd.DataFrame):
            continue

        for index,row in temp.iterrows():
    
            last_edit = datetime.datetime.strptime(row[mongodb.metadata_field_names['timestamp']], "%Y-%m-%d %H:%M:%S.%f")
            time_since_last_edit = prettify_time_diff((current_time - last_edit).total_seconds())

            # here we create a summary field of the row's content
            content_summary = ', '.join([f'{x} - {str(row[x])}' for x in row.index if x not in mongodb.metadata_fields(exclude_id=True)])
            content_summary = content_summary[:100] + " ..." if len(content_summary) > 100 else content_summary

            new_row = pd.DataFrame({    'form':[form_name], 
                                        'id': [str(row['_id'])], 
                                        'owner':[Markup(f"<a href=\"{config['domain']}/auth/profile/{row[mongodb.metadata_field_names['owner']]}\">{row[mongodb.metadata_field_names['owner']]}</a>")], 
                                        'timestamp':[row[mongodb.metadata_field_names['timestamp']]],
                                        # 'timestamp':[time_since_last_edit],
                                        'content_summary': content_summary,
                                        'time_since_last_edit': [time_since_last_edit], 
                                        'active': True,
                                    })

            df = pd.concat([df, new_row],
                    ignore_index=True)
    
        if not include_deleted:
            continue

        temp_deleted = mongodb.new_read_documents_from_collection(f"_{form_name}")

        if not isinstance(temp_deleted,pd.DataFrame):
            continue

        for index,row in temp_deleted.iterrows():
    
            last_edit = datetime.datetime.strptime(row[mongodb.metadata_field_names['timestamp']], "%Y-%m-%d %H:%M:%S.%f")
            time_since_last_edit = prettify_time_diff((current_time - last_edit).total_seconds())

            # here we create a summary field of the row's content
            content_summary = ', '.join([f'{x} - {str(row[x])}' for x in row.index if x not in mongodb.metadata_fields(exclude_id=True)])
            content_summary = content_summary[:100] + " ..." if len(content_summary) > 100 else content_summary

            new_row = pd.DataFrame({    'form':[form_name], 
                                        'id': [str(row['_id'])], 
                                        'owner':[Markup(f"<a href=\"{config['domain']}/auth/profile/{row[mongodb.metadata_field_names['owner']]}\">{row[mongodb.metadata_field_names['owner']]}</a>")], 
                                        'timestamp':[row[mongodb.metadata_field_names['timestamp']]],
                                        # 'timestamp':[time_since_last_edit],
                                        'content_summary': content_summary,
                                        'time_since_last_edit': [time_since_last_edit], 
                                        'active': False,
                                    })

            df = pd.concat([df, new_row],
                    ignore_index=True)

    return df.sort_values(by='timestamp', ignore_index=True, ascending=False) if sort else df


# this is a password generation script that takes a password length
# and regex, returning a password string. It also takes a alphanumeric_percentage
# parameter, between 0 and 1, which scopes the percentage of alphanumeric
# chars that will be used in the password generated
def percentage_alphanumeric_generate_password(regex:str, length:int, alphanumeric_percentage:float):
    def random_char_from_class(class_name):
        if class_name == '\\d':
            return random.choice(string.digits)
        elif class_name == '\\w':
            return random.choice(string.ascii_letters + string.digits)
        elif class_name == '\\s':
            return random.choice(string.whitespace)
        else:
            return random.choice(string.printable)

    # here we validate that `alphanumeric_percentage` is a float between 0 and 1
    assert 0 <= alphanumeric_percentage <= 1

    pattern = re.compile(regex)

    alphanumeric_count = int(length * alphanumeric_percentage)
    non_alphanumeric_count = length - alphanumeric_count

    while True:
        alphanumeric_part = [random_char_from_class('\\w') for _ in range(alphanumeric_count)]
        non_alphanumeric_part = [random_char_from_class(c) if c in ('\\d', '\\w', '\\s') else c for c in random.choices(regex, k=non_alphanumeric_count)]
        password = ''.join(random.sample(alphanumeric_part + non_alphanumeric_part, length))
        if pattern.fullmatch(password):
            return password

bp = Blueprint('admin', __name__, url_prefix='/admin')


# this is the redirect point for the admin left-hand menu.
# the admin handler view may be a good point to verify that a user 
# has access to the associated resource before redirecting them to it
# # @is_admin
# @bp.route('/handler/<view_name>')
# def admin_handler(view_name):
#     return redirect(url_for(f'admin.{view_name}'))


@bp.route('/')
@is_admin
def admin_home():

    return render_template('admin/admin_home.html.jinja',
        name='Admin',
        subtitle='Home',
        type="admin",
        msg="Select an admin view from the left-hand menu.",
        menu=compile_admin_views_for_menu(),
        **standard_view_kwargs(),
        )



@bp.route('/users', methods=('GET', 'POST'))
@is_admin
def user_management():

    # user_list = [row for row in User.query.with_entities(User.username).all()]
    user_list = [row for row in User.query.all()]

    return render_template('admin/user_management.html.jinja',
        name='Admin',
        subtitle='Logs',
        type="admin",
        menu=compile_admin_views_for_menu(),
        user_list=user_list,
        **standard_view_kwargs(),
        )



@bp.route('/logs', methods=('GET', 'POST'))
@is_admin
def log_management():

    user_selected = None


    # here we gauge whether user data has been passed, 
    # which will be used to tailor the log data shown.
    try:
        username = request.form['user'].upper().strip()

        assert(username != '*ALL LOGS*')

        log_data = aggregate_log_data(keyword=f'- {username} -', limit=1000, pull_from='end')

        user_selected = username.lower()

    except:

        log_data = aggregate_log_data(limit=1000, pull_from='end')


    # here we gauge whether the admin wants to change the dotenv config for logs, see dotenv 
    # config discussion here https://github.com/libreForms/libreForms-flask/issues/233.
    try:
        enable_user_profile_log_aggregation = request.form['enable_user_profile_log_aggregation'].strip()
        enable_user_profile_log_aggregation = True if enable_user_profile_log_aggregation=='yes' else False
        # print(enable_user_profile_log_aggregation)
        dotenv_overrides(enable_user_profile_log_aggregation=enable_user_profile_log_aggregation)


    except:

        pass


    # print(user_selected)
    user_list = [row.username for row in User.query.with_entities(User.username).all()]

    return render_template('admin/log_management.html.jinja',
        name='Admin',
        subtitle='Logs',
        type="admin",
        menu=compile_admin_views_for_menu(),
        log_data=log_data,
        user_list=user_list,
        user_selected=user_selected,
        **standard_view_kwargs(),
        )

@bp.route('/forms', methods=('GET', 'POST'))
@is_admin
def form_management():

    form_selected = None


    # here we gauge whether user data has been passed, 
    # which will be used to tailor the log data shown.
    try:
        
        if request.method == 'POST':
            form = request.form['form'].strip()

        else:
            form = request.args.get('form', '').strip()


        assert(form != '*all forms*')

        # QUERY FORM DATA for `form` collection
        form_data = compile_form_data(form_names=[form])

        form_selected = form

    except:

        # QUERY FORM DATA for all collections
        form_data = compile_form_data()


    # print(user_selected)
    

    return render_template('admin/form_management.html.jinja',
        name='Admin',
        subtitle='Forms',
        type="admin",
        menu=compile_admin_views_for_menu(),
        form_data=form_data,
        form_list=libreforms.forms,
        form_selected=form_selected,
        **standard_view_kwargs(),
        )



@bp.route('/signatures', methods=('GET', 'POST'))
@is_admin
def signature_management():


    # user_selected = None

    # try:
    #     username = request.form['user'].upper().strip()

    #     assert(username != '*ALL LOGS*')

    #     log_data = aggregate_log_data(keyword=f'- {username} -', limit=1000, pull_from='end')

    #     user_selected = username.lower()

    # except:

    #     log_data = aggregate_log_data(limit=1000, pull_from='end')

    signature_list = [row for row in Signing.query.all()]
    # print(signature_list)

    # print(user_selected)
    user_list = [row.username for row in User.query.with_entities(User.username).all()]

    return render_template('admin/signature_management.html.jinja',
        name='Admin',
        subtitle='Signatures',
        type="admin",
        menu=compile_admin_views_for_menu(),
        signature_list=signature_list,
        **standard_view_kwargs(),
        )




@bp.route('/smtp', methods=('GET', 'POST'))
@is_admin
def smtp_configuration():

    try:
        smtp_enabled = request.form['smtp_enabled'].strip()
        # here we assert that, if SMTP is turned off, that none of its dependent configurations have been set
        if smtp_enabled == 'no' and (config['enable_email_verification'] or config['enable_reports'] or config['allow_password_resets'] or config['allow_anonymous_form_submissions']):
            flash("You cannot disable SMTP if email verification, password resets, sending reports, or anonymous form submissions is enabled. ", "warning")
            raise Exception()
        smtp_enabled = True if smtp_enabled=='yes' else False

        smtp_mail_server = request.form['smtp_mail_server'].strip()
        smtp_port = request.form['smtp_port'].strip()
        smtp_username = request.form['smtp_username'].strip()
        smtp_password = request.form['smtp_password'].strip()
        smtp_from_address = request.form['smtp_from_address'].strip()
        send_mail_asynchronously = request.form['send_mail_asynchronously'].strip()
        send_mail_asynchronously = True if send_mail_asynchronously=='yes' else False

        # write all of these to the overrides file
        dotenv_overrides(   smtp_enabled=smtp_enabled,
                            smtp_mail_server=smtp_mail_server,
                            smtp_port=smtp_port,
                            smtp_username=smtp_username,
                            smtp_password=smtp_password,
                            smtp_from_address=smtp_from_address,
                            send_mail_asynchronously=send_mail_asynchronously,)

    except:
        pass

    return render_template('admin/smtp_configuration.html.jinja',
        name='Admin',
        subtitle='SMTP',
        type="admin",
        menu=compile_admin_views_for_menu(),
        **standard_view_kwargs(),
        )



@bp.route('/saml', methods=('GET', 'POST'))
@is_admin
def saml_configuration():

    try:
        saml_enabled = request.form['saml_enabled'].strip()
        saml_enabled = True if saml_enabled == 'yes' else False

        saml_idp_entity_id = request.form['saml_idp_entity_id'].strip()
        saml_idp_sso_url = request.form['saml_idp_sso_url'].strip()
        saml_idp_slo_url = request.form['saml_idp_slo_url'].strip()
        saml_idp_x509_cert = request.form['saml_idp_x509_cert'].strip()
        saml_strict = request.form['saml_strict'].strip()
        saml_strict = True if saml_strict == 'yes' else False
        saml_debug = request.form['saml_debug'].strip()
        saml_debug = True if saml_debug == 'yes' else False
        saml_name_id_format = request.form['saml_name_id_format'].strip()
        saml_sp_x509_cert = request.form['saml_sp_x509_cert'].strip()
        saml_sp_private_key = request.form['saml_sp_private_key'].strip()

        # write all of these to the overrides file
        dotenv_overrides(   saml_enabled=saml_enabled,
                            saml_idp_entity_id=saml_idp_entity_id,
                            saml_idp_sso_url=saml_idp_sso_url,
                            saml_idp_slo_url=saml_idp_slo_url,
                            saml_idp_x509_cert=saml_idp_x509_cert,
                            saml_strict=saml_strict,
                            saml_debug=saml_debug,
                            saml_name_id_format=saml_name_id_format,
                            saml_sp_x509_cert=saml_sp_x509_cert,
                            saml_sp_private_key=saml_sp_private_key,)

    except:
        pass

    return render_template('admin/saml_configuration.html.jinja',
        name='Admin',
        subtitle='SAML',
        type="admin",
        menu=compile_admin_views_for_menu(),
        **standard_view_kwargs(),
        )

@bp.route('/register/user', methods=('GET', 'POST'))
@is_admin
def user_register():

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        organization = request.form['organization']
        phone = request.form['phone']
        group = request.form['group']


        TEMP = {}
        for item in config['user_registration_fields'].keys():
            if config['user_registration_fields'][item]['input_type'] != 'hidden':

                if config['user_registration_fields'][item]['input_type'] == 'checkbox':
                    
                    TEMP[item] = str(request.form.getlist(item))

                else:
                    TEMP[item] = str(request.form[item]) if config['user_registration_fields'][item]['type'] == str else float(request.form[item])

        if phone == "":
            phone = None
        
        if email == "":
            email = None

        if organization == "":
            email = None

        error = None
        transaction_id = str(uuid.uuid1()) # if there is an error, this ID will link it in the logs

        if not username:
            error = 'Username is required. '
        
        # added these per https://github.com/signebedi/libreForms/issues/122
        # to give the freedom to set these as required fields
        elif config['registration_email_required'] and not email:
            error = 'Email is required. '
        elif config['registration_phone_required'] and not phone:
            error = 'Phone is required. '
        elif config['registration_organization_required'] and not organization:
            error = 'Organization is required. '

        elif not re.fullmatch(config['username_regex'], username):
            error = f'Invalid username. ({config["user_friendly_username_regex"]}) '
        elif email and not re.fullmatch(config['email_regex'], email):
            error = f'Invalid email. ({config["user_friendly_email_regex"]}) ' 
        elif phone and not re.fullmatch(config['phone_regex'], phone):
            error = f'Invalid phone number ({config["user_friendly_phone_regex"]}). ' 
        elif email and User.query.filter_by(email=email).first():
            error = 'Email is already registered. ' 
        elif User.query.filter_by(username=username.lower()).first():
            error = f'Username {username.lower()} is already registered. ' 

        if error is None:
            try:
                # we generate a password here
                password = percentage_alphanumeric_generate_password(config['password_regex'], 16, .65)

                new_user = User(
                            email=email, 
                            username=username.lower(), 
                            password=generate_password_hash(password, method='sha256'),
                            organization=organization,
                            group=group,
                            certificate=generate_symmetric_key(),
                            phone=phone,
                            theme='dark' if config['dark_mode'] else 'light', # we default to the application default
                            # created_date=created_date,
                            active=0 if config["enable_email_verification"] else 1,
                            **TEMP, # https://stackoverflow.com/a/5710402
                        ) 
                db.session.add(new_user)
                db.session.commit()

                if config["enable_email_verification"]:
                    key = signing.write_key_to_database(scope='email_verification', expiration=48, active=1, email=email)
                    m = send_mail_async.delay(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}. Please verify your email by clicking the following link: {config['domain']}/auth/verify_email/{key}. Please note this link will expire after 48 hours.", to_address=email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}. Please verify your email by clicking the following link: {config['domain']}/auth/verify_email/{key}. Please note this link will expire after 48 hours.", to_address=email, logfile=log)
                    flash(f'Successfully created user \'{username.lower()}\'. They should check their email for an activation link. Their password is: {password}', "success")
                else:
                    m = send_mail_async.delay(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}.", to_address=email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}.", to_address=email, logfile=log)
                    flash(f'Successfully created user \'{username.lower()}\'. Their password is: {password}', "success")

                m = send_mail_async.delay(subject=f'{config["site_name"]} Initial Password', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}. Your new password is: {password}", to_address=email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} Initial Password', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}. Your new password is: {password}", to_address=email, logfile=log)
                log.info(f'{current_user.username.upper()} - successfully registered with email {email}.')
            except Exception as e: 
                log.error(f'{current_user.username.upper()} - failed to register new user {username.lower()} with email {email}. {e}', extra={'transaction_id': transaction_id})
                flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ", 'warning')


    return render_template('admin/create_user.html.jinja',
        name='Admin',
        subtitle='Register User',
        type="admin",
        menu=compile_admin_views_for_menu(),
        **standard_view_kwargs(),
        )





@bp.route('/register/bulk', methods=('GET', 'POST'))
@is_admin
def bulk_register():

    if not config['allow_bulk_registration']:
        flash('This feature has not been enabled by your system administrator.', "warning")
        return redirect(url_for('home'))

    # limit access to admin group users when the corresponding configuration is set to true,
    # see https://github.com/signebedi/libreForms/issues/170.
    if config['limit_bulk_registration_to_admin_group'] and current_user.group != config['admin_group']:
        return abort(404)

    if request.method == 'POST':

        file = request.files['file']
        if file.filename == '':
            flash("Please select a CSV to upload", "warning")
            return redirect(url_for('admin.bulk_register')) 

        with tempfile.TemporaryDirectory() as tmpdirname:
            # print('created temporary directory', tmpdirname)

            filepath = secure_filename(file.filename) # first remove any banned chars
            filepath = os.path.join(tmpdirname, file.filename)

            file.save(filepath)

            error = None
            transaction_id = str(uuid.uuid1())

            if not file.filename.lower().endswith(".csv",):
                error = 'Please upload a CSV file.'
            else:
                try:
                    bulk_user_df = pd.read_csv(filepath)

                    for x in ["username", "password", "group"]: # a minimalist common sense check
                        assert x in bulk_user_df.columns
                        
                    # note that these DO require email, organization, and phone
                    # fields if these are set to being required fields in the app
                    # config, see https://github.com/signebedi/libreForms/issues/122;
                    # however, they DO NOT require that this field be populated for
                    # each row of data entered. See issue above for more discussion.
                    if config['registration_email_required']:
                        assert 'email' in bulk_user_df.columns
                    if config['registration_organization_required']:
                        assert 'organization' in bulk_user_df.columns
                    if config['registration_phone_required']:
                        assert 'phone' in bulk_user_df.columns

                    #verify that, if there are any custom fields that are required, these exist here
                    if config['user_registration_fields']:
                        for x in config['user_registration_fields'].keys():
                            if config['user_registration_fields'][x]['input_type'] != 'hidden' and config['user_registration_fields'][x]['required'] == True:
                                assert x in bulk_user_df.columns


                except Exception as e: 
                    error = e
                    log.warning(f"{current_user.username.upper()} - {e}", extra={'transaction_id': transaction_id})

            if error is None:
                # created_date=datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                
                for index, row in bulk_user_df.iterrows():
                    does_user_exist = User.query.filter_by(username=row.username.lower()).first()
                    does_email_exist =  User.query.filter_by(email=row.email.lower()).first()

                    if does_user_exist or does_email_exist:
                        flash(f"Could not register {row.username.lower()} under email {row.email.lower()}. User already exists. ", "warning")

                    elif not row.username:
                        flash(f"Could not register at row {row}. Username is required. ", "warning")
                    elif not row.password:
                        flash(f"Could not register {row.username.lower()}. Password is required. ", "warning")
                    elif config['registration_email_required'] and not row.email:
                        flash(f"Could not register {row.username.lower()}. Email is required. ", "warning")
                    elif config['registration_organization_required'] and not row.organization:
                        flash(f"Could not register {row.username.lower()}. Organization is required. ", "warning")
                    elif config['registration_phone_required'] and not row.phone:
                        flash(f"Could not register {row.username.lower()} under email {row.email.lower()}. Phone is required. ", "warning")


                    # set to default group if non is passed
                    if row.group == "" or None:
                        row.group = config['default_group']

                    else:

                        TEMP = {}
                        for item in config['user_registration_fields'].keys():
                            if config['user_registration_fields'][item]['input_type'] != 'hidden':
                                TEMP[item] = str(row[item]) if config['user_registration_fields'][item]['type'] == str else float(row[item])

                        try: 

                            user_check = User.query.filter_by(username=row.username.lower()).first()
                            email_check = User.query.filter_by(email=row.email).first()

                            assert not user_check and not email_check

                            new_user = User(
                                        email=row.email if row.email else "", 
                                        username=row.username.lower(), 
                                        password=generate_password_hash(row.password, method='sha256'),
                                        organization=row.organization if row.organization else "",
                                        phone=row.phone if row.phone else "",
                                        theme=row.theme if row.theme in ['light', 'dark'] else 'dark',
                                        # created_date=created_date,
                                        group = row.group,
                                        certificate=generate_symmetric_key(),
                                        active=0 if config["enable_email_verification"] else 1,
                                        **TEMP
                                    )
                            db.session.add(new_user)
                            db.session.commit()

                            if config["enable_email_verification"]:
                                key = signing.write_key_to_database(scope='email_verification', expiration=48, active=1, email=row.email)
                                m = send_mail_async.delay(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}. Please verify your email by clicking the following link: {config['domain']}/auth/verify_email/{key}. Please note this link will expire after 48 hours.", to_address=row.email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}. Please verify your email by clicking the following link: {config['domain']}/auth/verify_email/{key}. Please note this link will expire after 48 hours.", to_address=row.email, logfile=log)
                                flash(f'Successfully created user \'{row.username.lower()}\'. They should check their email for an activation link. ', "success")
                            else:
                                m = send_mail_async.delay(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}.", to_address=row.email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}.", to_address=row.email, logfile=log)
                                flash(f'Successfully created user \'{row.username.lower()}\'.', "success")

                            log.info(f'{row.username.upper()} - successfully registered with email {row.email}.')
                        except Exception as e: 
                            # error = f"User is already registered with username \'{row.username.lower()}\' or email \'{row.email}\'." if row.email else f"User is already registered with username \'{row.username}\'. "
                            log.error(f'{current_user.username.upper()} - failed to register new user {row.username.lower()} with email {row.email}. {e}',extra={'transaction_id': transaction_id})
                            flash(f"Issue registering {row.username.lower()}. Transaction ID: {transaction_id}.", "warning")

                    # else:
                    #     flash(f'Successfully created user \'{bulk_user_df.username.lower()}\'.')
                    #     m = send_mail_async.delay(subject=f"Successfully Registered {username}", content=f"This is a notification that {username} has been successfully registered for libreforms.", to_address=email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f"Successfully Registered {username}", content=f"This is a notification that {username} has been successfully registered for libreforms.", to_address=email, logfile=log)
                    #     return redirect(url_for("auth.add_users"))
                flash ("Finished uploading users from CSV.", "success")

            else:
                flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ", 'warning')


            # return f"File saved successfully {filepath}"



    return render_template('admin/add_users.html.jinja',
        name='Admin',
        subtitle='Bulk Register',
        type="admin",
        menu=compile_admin_views_for_menu(),
        **standard_view_kwargs(),
        )



# Implementing this will only work in production (eg. using wsgi / gunicorn) for now,
# see discussion at https://github.com/libreForms/libreForms-flask/issues/311.
@bp.route('/restart', methods=('GET', 'POST'))
@is_admin
def restart_application():


    if request.method == 'POST':
        return redirect(url_for('admin.restart_now'))

    last_restart = datetime.datetime.strptime(config['last_restart'], "%Y-%m-%d %H:%M:%S")
    current_time = datetime.datetime.now()

    # Calculate time difference
    uptime = current_time - last_restart

    return render_template('admin/restart_application.html.jinja',
        name='Admin',
        subtitle='Restart',
        type="admin",
        uptime=prettify_time_diff(uptime.total_seconds()),
        menu=compile_admin_views_for_menu(),
        **standard_view_kwargs(),
        )


@bp.route('/restart/now', methods=('GET', 'POST'))
@is_admin
def restart_now():

    # with open('restart.flag','w'): pass # touch the restart file.

    flash('Restart has been queued. ', "success")
    log.info(f'{current_user.username.upper()} - successfully queued application restart.')
    restart_app_async.delay() # will not run if celery is not running..
    return redirect(url_for('admin.restart_application'))


@bp.route(f'/toggle/s/<signature>', methods=['GET', 'POST'])
@is_admin
def toggle_signature_active_status(signature):

    s = Signing.query.filter_by(signature=signature).first()

    if not s:
        flash (f'Signature {signature} does not exist.', 'warning')
        return redirect(url_for('admin.signature_management'))


    if s.active == 0:
        s.active = 1 
        db.session.commit()
        flash (f'Activated signature {signature}. ', 'info')
        log.info(f'{current_user.username.upper()} - activated {mask_string(signature)} signature.')

    else:
        s.active = 0
        db.session.commit()
        flash (f'Deactivated signature {signature}. ', 'info')
        log.info(f'{current_user.username.upper()} - deactivated {mask_string(signature)} signature.')

    if config['notify_users_on_admin_action']:
        action_taken = "Deactivated" if s.active == 0 else "Activated"
        subject = f'{config["site_name"]} Signing Key {action_taken}'
        content = f"This email serves to notify you that an administrator has just {action_taken.lower()} a signing key {mask_string(signature)}, which is associated with your email at {config['domain']}. Please contact your system administrator if you believe this was a mistake."
        m = send_mail_async.delay(subject=subject, content=content, to_address=s.email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=subject, content=content, to_address=s.email)

    return redirect(url_for('admin.signature_management'))


@bp.route(f'/toggle/u/<username>', methods=['GET', 'POST'])
@is_admin
def toggle_user_active_status(username):

    user = User.query.filter_by(username=username.lower()).first()

    if not user:
        flash (f'User {username} does not exist.', 'warning')
        return redirect(url_for('admin.user_management'))

    if current_user.id == user.id:
        flash (f'You cannot deactivate the user you are currently logged in as.', 'warning')
        return redirect(url_for('admin.user_management'))

    if user.active == 0:
        user.active = 1 
        db.session.commit()
        flash (f'Activated user {username}. ', 'info')
        log.info(f'{current_user.username.upper()} - activated {user.username} user.')

    else:
        user.active = 0
        db.session.commit()
        flash (f'Deactivated user {username}. ', 'info')
        log.info(f'{current_user.username.upper()} - deactivated {user.username} user.')

    if config['notify_users_on_admin_action']:
        action_taken = "Deactivated" if user.active == 0 else "Activated"
        subject = f'{config["site_name"]} User {action_taken}'
        content = f"This email serves to notify you that an administrator has just {action_taken.lower()} the user '{user.username}', which is associated with your email at {config['domain']}. Please contact your system administrator if you believe this was a mistake."
        m = send_mail_async.delay(subject=subject, content=content, to_address=user.email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=subject, content=content, to_address=user.email)


    return redirect(url_for('admin.user_management'))



@bp.route(f'/password/<username>', methods=['GET', 'POST'])
@is_admin
def generate_random_password(username):
    # flash(percentage_alphanumeric_generate_password(config['password_regex'], 16, .65), 'info')
    # return redirect(url_for('admin.user_management'))

    user = User.query.filter_by(username=username.lower()).first()

    if not user:
        flash (f'User {username} does not exist.', 'warning')
        return redirect(url_for('admin.user_management'))

    # generate and hash the new password
    new_password = percentage_alphanumeric_generate_password(config['password_regex'], 16, .65)
    hashed_password = generate_password_hash(new_password, method='sha256')

    user.password = hashed_password
    db.session.commit()

    flash(f'Successfully modified \'{user.username}\' user password to: {new_password}', "success")
    log.info(f'{current_user.username.upper()} - updated {user.username} user\'s password.')

    if config['notify_users_on_admin_action']:
        subject = f'{config["site_name"]} Password Changed'
        content = f"This email serves to notify you that an administrator has just changed the password for user '{user.username}', which is associated with your email at {config['domain']}. Your new password is: {new_password}\nPlease contact your system administrator if you believe this was a mistake."
        m = send_mail_async.delay(subject=subject, content=content, to_address=user.email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=subject, content=content, to_address=user.email)


    return redirect(url_for('admin.user_management'))

    # Placeholder for email notifications
    # if config["enable_email_verification"]:
    #     m = send_mail_async.delay(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}. Please verify your email by clicking the following link: {config['domain']}/auth/verify_email/{key}. Please note this link will expire after 48 hours.", to_address=row.email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}. Please verify your email by clicking the following link: {config['domain']}/auth/verify_email/{key}. Please note this link will expire after 48 hours.", to_address=row.email, logfile=log)
    #     flash(f'Successfully created user \'{row.username.lower()}\'. They should check their email for an activation link. ', "success")
    # else:
    #     m = send_mail_async.delay(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}.", to_address=row.email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}.", to_address=row.email, logfile=log)
    #     flash(f'Successfully created user \'{row.username.lower()}\'.', "success")




@bp.route('/edit/<username>', methods=('GET', 'POST'))
@is_admin
def edit_profile(username):

    # if the current authenticated user is trying to edit their own profile, 
    # then redirect to the that route
    if username == current_user.username:
        return redirect(url_for('auth.edit_profile'))

    user = User.query.filter_by(username=username).first()

    if not user:
        flash (f'User {username} does not exist.', 'warning')
        return redirect(url_for('admin.user_management'))

    if request.method == 'POST':

        organization = request.form['organization'] or None
        phone = request.form['phone'] or None
        theme = request.form['theme'] or None
        
        TEMP = {}
        for item in config['user_registration_fields'].keys():
            if config['user_registration_fields'][item]['input_type'] != 'hidden':

                if config['user_registration_fields'][item]['input_type'] == 'checkbox':
                    
                    TEMP[item] = str(request.form.getlist(item))

                else:

                    TEMP[item] = str(request.form[item]) if config['user_registration_fields'][item]['type'] == str else None

        if phone == "" or phone == None or phone == "None":
            phone = None
        
        if organization == "" or phone == None or phone == "None":
            email = None
        
        if theme not in ['light', 'dark']:
            theme = 'dark'

        error = None

        # added these per https://github.com/signebedi/libreForms/issues/122
        # to give the freedom to set these as required fields
        if config['registration_phone_required'] and not phone:
            error = 'Phone is required. '
        elif config['registration_organization_required'] and not organization:
            error = 'Organization is required. '
        elif phone and not re.fullmatch(config['phone_regex'], phone):
            error = f'Invalid phone number ({config["user_friendly_phone_regex"]}). ' 
    
        if error is None:
            try:
                user.organization = organization 
                user.phone = phone 
                user.theme = theme 
                for item in TEMP:
                    setattr(user, item, TEMP[item])

                db.session.commit()

                flash(f"Successfully updated profile for user {username}.", "success")
                log.info(f'{current_user.username.upper()} - Successfully updated profile for user {username}.')
                return redirect(url_for('admin.user_management'))

            except Exception as e: 
                transaction_id = str(uuid.uuid1())
                log.warning(f"{current_user.username.upper()} - failed to update profile for user {username}. {e}", extra={'transaction_id': transaction_id})
                error = f"There was an error in processing your request. Transaction ID: {transaction_id}. "
            
        flash(error, "warning")

    return render_template('auth/register.html.jinja',
        edit_profile=True,
        name=username,
        subtitle='Edit Profile',
        user_data=user, # this is the data that populates the user fields
        **standard_view_kwargs(),
        )

@bp.route('/api/<username>', methods=('GET', 'POST'))
@is_admin 
def generate_api_key(username):

    user = User.query.filter_by(username=username).first()

    if not user:
        flash (f'User {username} does not exist.', 'warning')
        return redirect(url_for('admin.user_management'))

    if config['limit_rest_api_keys_per_user']:
        signing_df = pd.read_sql_table("signing", con=db.engine.connect())

        # note that this behavior will not apply when an email has not been specified for a given key, which
        # shouldn't be the case as long as emails are required fields at user registration; however, the `libreforms`
        # user, which ships by default with the application, does not have an email set - meaning that the default
        # user will not be constrained by this behavior. This can be viewed as a bug or a feature, depending on context.
        if len(signing_df.loc[(signing_df.email == user.email) & (signing_df.scope == 'api_key') & (signing_df.active == 1)]) >= config['limit_rest_api_keys_per_user']:
            flash(f'This user has already registered the maximum number of API keys they are permitted. ', "warning")
            return redirect(url_for('admin.user_management'))

    key = signing.write_key_to_database(scope='api_key', expiration=5640, active=1, email=user.email)
    m = send_mail_async.delay(subject=f'{config["site_name"]} API Key Generated', content=f"This email serves to notify you that the user {user.username} has just generated an API key for this email address at {config['domain']}. The API key is: {key}. Please note this key will expire after 365 days.", to_address=current_user.email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} API Key Generated', content=f"This email serves to notify you that the user {current_user.username} has just generated an API key for this email address at {config['domain']}. The API key is: {key}. Please note this key will expire after 365 days.", to_address=current_user.email, logfile=log)
    flash(f'Successfully generated API key {key} for \'{user.username.lower()}\'. They should check their email for further instructions. ', "success")

    return redirect(url_for('admin.user_management'))

@bp.route(f'/toggle/f/<form_name>/<document_id>', methods=['GET', 'POST'])
@is_admin
def toggle_form_deletion_status(form_name, document_id):

    forms = compile_form_data(form_name, sort=False)

    print(forms)

    form = forms.loc [forms.id == document_id]

    print(form)


    if len(form.index) == 0:
        flash (f'Form {document_id} does not exist.', 'warning')
        return redirect(url_for('admin.form_management', form=form_name))

    f = form.iloc[0]

    print(f)

    if not f.active:

        _ = mongodb.restore_soft_deleted_document(form_name, document_id)

        flash (f'Restored form {document_id}. ', 'info')
        log.info(f'{current_user.username.upper()} - restored form {document_id}.')


    else:
        _ = mongodb.soft_delete_document(form_name, document_id)
        flash (f'Deleted form {document_id}. ', 'info')
        log.info(f'{current_user.username.upper()} - deleted form {document_id}.')


    return redirect(url_for('admin.form_management', form=form_name))
