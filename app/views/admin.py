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

    Database externalization
    Add LDAP / OAuth Authentication
    SMTP Configuration
    File System Configuration (set max file upload size)
    User and Group/Role Configuration
    Log Access
    REST API privileges (read-only or full CRUD)
    External forms (allowed or not)
    Data backup, rotation, management, retention, restore-from-backup
    Look and Feel (display overrides)
    Signing Key rotation

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
"""

__name__ = "app.views.admin"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.6.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from flask import current_app, Blueprint, g, flash, abort, render_template, \
    request, send_from_directory, send_file, redirect, url_for
from app.views.auth import login_required, session
from app.config import config
from flask_login import current_user
from functools import wraps
import string
from app.views.forms import standard_view_kwargs
from app.log_functions import aggregate_log_data

# requirements for bulk email management
from app.models import User, db
from app.certification import generate_symmetric_key
import app.signing as signing
from werkzeug.utils import secure_filename
import pandas as pd
import os, tempfile, datetime
from app import log
from werkzeug.security import generate_password_hash
from celeryd.tasks import send_mail_async

# borrows from and extends the functionality of flask_login.login_required, see
# https://github.com/maxcountryman/flask-login/blob/main/src/flask_login/utils.py.
def is_admin(func):

    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_app.config.get("LOGIN_DISABLED"):
            pass
        elif not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()

        elif not current_user.group == config['admin_group']:
            return abort(404)

        # flask 1.x compatibility
        # current_app.ensure_sync is only available in Flask >= 2.0
        if callable(getattr(current_app, "ensure_sync", None)):
            return current_app.ensure_sync(func)(*args, **kwargs)

        return func(*args, **kwargs)

    return decorated_view


def compile_admin_views_for_menu():
    
    views = []

    for view in [key for key in current_app.view_functions if key.startswith('admin')]:
        v = view.replace('admin_','')
        v = v.replace('admin.','')
        v = v.replace('_',' ')
        v = string.capwords(v)
        views.append([view,v])

    # print (views)
    return views

bp = Blueprint('admin', __name__, url_prefix='/admin')


# this is the redirect point for the admin left-hand menu.
# the admin handler view may be a good point to verify that a user 
# has access to the associated resource before redirecting them to it
# @is_admin
# @bp.route('/handler/<view_name>')
# def admin_handler(view_name):
#     return redirect(url_for(f'admin.{view_name}'))


@is_admin
@bp.route('/')
def admin_home():


    return render_template('admin/admin_home.html',
        name='Admin',
        subtitle='Home',
        type="admin",
        menu=compile_admin_views_for_menu(),
        **standard_view_kwargs(),
        )


@is_admin
@bp.route('/logs', methods=('GET', 'POST'))
def log_management():

    return render_template('admin/log_management.html',
        name='Admin',
        subtitle='Logs',
        type="admin",
        menu=compile_admin_views_for_menu(),
        log_data=aggregate_log_data(keyword=f'- {current_user.username.upper()} -', limit=1000, pull_from='end') if config['enable_user_profile_log_aggregation'] else None,
        **standard_view_kwargs(),
        )

@is_admin
@bp.route('/register/bulk', methods=('GET', 'POST'))
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
                    log.warning(f"LIBREFORMS - {e}")
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



    return render_template('admin/add_users.html',
        name='Admin',
        subtitle='Bulk Register',
        type="admin",
        menu=compile_admin_views_for_menu(),
        **standard_view_kwargs(),
        )
