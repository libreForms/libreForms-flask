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
__version__ = "1.8.0"
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

# requirements for bulk email management
from app.models import User, Signing, db
from app.certification import generate_symmetric_key
import app.signing as signing
from werkzeug.utils import secure_filename
import pandas as pd
import os, tempfile, datetime
from app import log
from werkzeug.security import generate_password_hash
from celeryd.tasks import send_mail_async, restart_app_async
from app.pdf import convert_to_string

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
    for view in [key for key in current_app.view_functions if key.startswith('admin') and not key in ['admin.restart_now']]:
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
        log.error (f'{current_user.username.upper()} - {e}')
        return False



def compile_form_data(form_names=[]):
    df = pd.DataFrame(columns = ['form', 'id', 'owner', 'timestamp'])


    if not isinstance(form_names,list) or len(form_names) < 1:
        form_names = libreforms.forms


    for form_name in form_names:        
        temp = mongodb.new_read_documents_from_collection(form_name)

        if not isinstance(temp,pd.DataFrame):
            continue

        for index,row in temp.iterrows():
            
            new_row = pd.DataFrame({    'form':[form_name], 
                                        'id': [Markup(f"<a href=\"{config['domain']}/submissions/{form_name}/{row['_id']}\">{row['_id']}</a>")], 
                                        'owner':[Markup(f"<a href=\"{config['domain']}/auth/profile/{row[mongodb.metadata_field_names['owner']]}\">{row[mongodb.metadata_field_names['owner']]}</a>")], 
                                        'timestamp':[row[mongodb.metadata_field_names['timestamp']]],})

            df = pd.concat([df, new_row],
                       ignore_index=True)
            
    return df


def prettify_time_diff(time:float):
    if time < 3600:
        if (time / 60) < 1:
            return "less than a minute ago"
        elif (time / 90) < 1 <= (time / 60):
            return "about a minute ago"
        elif (time / 420) < 1 <= (time / 90):
            return "a few minutes ago"
        elif (time / 900) < 1 <= (time / 420):
            return "about ten minutes ago"
        elif (time / 1500) < 1 <= (time / 900):
            return "about twenty minutes ago"
        elif (time / 2100) < 1 <= (time / 1500):
            return "about thirty minutes ago"
        elif (time / 2700) < 1 <= (time / 2100):
            return "about thirty minutes ago"
        elif (time / 3300) < 1 <= (time / 2700):
            return "about forty minutes ago"
        elif (time / 3600) < 1 <= (time / 3300):
            return "about fifty minutes ago"
    elif 84600 > time >= 3600: # we short 86400 seconds by 1800 seconds to manage rounding issues
        return f"about {round(time / 3600)} hour/s ago"
    elif 84600 <= time:
        return f"about {round(time / 86400)} day/s ago"
    else:
        return ""



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
        form = request.form['form'].strip()

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
            flash("You cannot disable SMTP if email verification, password resets, sending reports, or anonymous form submissions is enabled. ")
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

@bp.route('/register/bulk', methods=('GET', 'POST'))
@is_admin
def bulk_register():

    if not config['allow_bulk_registration']:
        flash('This feature has not been enabled by your system administrator.')
        return redirect(url_for('home'))

    # limit access to admin group users when the corresponding configuration is set to true,
    # see https://github.com/signebedi/libreForms/issues/170.
    if config['limit_bulk_registration_to_admin_group'] and current_user.group != config['admin_group']:
        return abort(404)

    if request.method == 'POST':

        file = request.files['file']
        if file.filename == '':
            flash("Please select a CSV to upload")
            return redirect(url_for('auth.bulk_register')) 

        with tempfile.TemporaryDirectory() as tmpdirname:
            # print('created temporary directory', tmpdirname)

            filepath = secure_filename(file.filename) # first remove any banned chars
            filepath = os.path.join(tmpdirname, file.filename)

            file.save(filepath)

            error = None

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
                    log.warning(f"{current_user.username.upper()} - {e}")
                    error = e

            if error is None:
                created_date=datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                
                for index, row in bulk_user_df.iterrows():
                    does_user_exist = User.query.filter_by(username=row.username.lower()).first()
                    does_email_exist =  User.query.filter_by(email=row.email.lower()).first()

                    if does_user_exist or does_email_exist:
                        flash(f"Could not register {row.username.lower()} under email {row.email.lower()}. User already exists. ")

                    elif not row.username:
                        flash(f"Could not register at row {row}. Username is required. ")
                    elif not row.password:
                        flash(f"Could not register {row.username.lower()}. Password is required. ")
                    elif config['registration_email_required'] and not row.email:
                        flash(f"Could not register {row.username.lower()}. Email is required. ")
                    elif config['registration_organization_required'] and not row.organization:
                        flash(f"Could not register {row.username.lower()}. Organization is required. ")
                    elif config['registration_phone_required'] and not row.phone:
                        flash(f"Could not register {row.username.lower()} under email {row.email.lower()}. Phone is required. ")


                    # set to default group if non is passed
                    if row.group == "" or None:
                        row.group = config['default_group']

                    else:

                        TEMP = {}
                        for item in config['user_registration_fields'].keys():
                            if config['user_registration_fields'][item]['input_type'] != 'hidden':
                                TEMP[item] = str(row[item]) if config['user_registration_fields'][item]['type'] == str else float(row[item])

                        try: 
                            new_user = User(
                                        email=row.email if row.email else "", 
                                        username=row.username.lower(), 
                                        password=generate_password_hash(row.password, method='sha256'),
                                        organization=row.organization if row.organization else "",
                                        phone=row.phone if row.phone else "",
                                        theme=row.theme if row.theme in ['light', 'dark'] else 'dark',
                                        created_date=created_date,
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
                                flash(f'Successfully created user \'{row.username.lower()}\'. They should check their email for an activation link. ')
                            else:
                                m = send_mail_async.delay(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}.", to_address=row.email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}.", to_address=row.email, logfile=log)
                                flash(f'Successfully created user \'{row.username.lower()}\'.')

                            log.info(f'{row.username.upper()} - successfully registered with email {row.email}.')
                        except Exception as e: 
                            # error = f"User is already registered with username \'{row.username.lower()}\' or email \'{row.email}\'." if row.email else f"User is already registered with username \'{row.username}\'. "
                            flash(f"Issue registering {row.username.lower()}. {e}")
                            log.error(f'{current_user.username.upper()} - failed to register new user {row.username.lower()} with email {row.email}.')
                    # else:
                    #     flash(f'Successfully created user \'{bulk_user_df.username.lower()}\'.')
                    #     m = send_mail_async.delay(subject=f"Successfully Registered {username}", content=f"This is a notification that {username} has been successfully registered for libreforms.", to_address=email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f"Successfully Registered {username}", content=f"This is a notification that {username} has been successfully registered for libreforms.", to_address=email, logfile=log)
                    #     return redirect(url_for("auth.add_users"))
                flash ("Finished uploading users from CSV.")

            else:
                flash(error)


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

    flash('Restart has been queued. ')
    log.info(f'{current_user.username.upper()} - successfully queued application restart.')
    restart_app_async.delay() # will not run if celery is not running..
    return redirect(url_for('admin.restart_application'))

