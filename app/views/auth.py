""" 
auth.py: implementation of auth views and underlying logic



"""

__name__ = "app.views.auth"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


import functools, re, datetime, tempfile, os
import pandas as pd

from flask import current_app, Blueprint, flash, g, redirect, render_template, request, session, url_for, send_from_directory, abort
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from app import config, log, mailer
import app.signing as signing
from app.models import User, Signing, db
from flask_login import login_required, current_user, login_user
from app.log_functions import aggregate_log_data
from app.certification import generate_symmetric_key


if config['enable_hcaptcha']:
    from app import hcaptcha

bp = Blueprint('auth', __name__, url_prefix='/auth')

# failsafe code in case we need to pivot away from using Flask-hCaptcha
def hcaptcha_verify(SECRET_KEY=config['hcaptcha_secret_key'], VERIFY_URL = "https://hcaptcha.com/siteverify"):
    import json, requests
    # Retrieve token from post data with key 'h-captcha-response'.
    token =  request.form.get('h-captcha-response')

    # Build payload with secret key and token.
    data = { 'secret': SECRET_KEY, 'response': token }

    # Make POST request with data payload to hCaptcha API endpoint.
    response = requests.post(url=VERIFY_URL, data=data)

    # Parse JSON from response. Check for success or error codes.
    response_json = json.parse(response.content)
    return response_json["success"] if response_json.status_code == 200 else False

@bp.route('/forgot_password/<signature>', methods=('GET', 'POST'))
def reset_password(signature):

    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if not config['allow_password_resets']:
        flash('This feature has not been enabled by your system administrator.')
        return redirect(url_for('auth.forgot_password'))
    
    if not signing.verify_signatures(signature, redirect_to='auth.forgot_password', 
                                        scope="forgot_password"):

        if request.method == 'POST':
            password = request.form['password']
            signing_df = pd.read_sql_table("signing", con=db.engine.connect())
            email = signing_df.loc[ signing_df['signature'] == signature ]['email'].iloc[0]

            if not password:
                error = 'Password is required.'

            else: error = None

            if error is None:
                try:
                    user = User.query.filter_by(email=str(email)).first() ## get email from Signing table & collate to User table 
                    user.password=generate_password_hash(password, method='sha256')
                    db.session.commit()

                    signing.expire_key(signature)
                    flash("Successfully changed password. ")
                    log.info(f'{user.username.upper()} - successfully changed password.')
                    return redirect(url_for('auth.login'))
                except Exception as e:
                    flash (f"There was an error in processing your request. {e}")
                
            else:
                flash(error)
    
        return render_template('auth/forgot_password.html',
            site_name=config['site_name'],
            name="Reset Password", 
            reset=True,
            config=config)
        
    return redirect(url_for('auth.login'))



@bp.route('/forgot_password', methods=('GET', 'POST'))
def forgot_password():

    # we only make this view visible if the user isn't logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST' and config["smtp_enabled"]:
        email = request.form['email']

        if not User.query.filter_by(email=email.lower()).first():
            error = f'Email {email.lower()} is not registered.' 
                        
        else: error=None
        
        if config['enable_hcaptcha']:
            if not hcaptcha.verify():
                error = 'Captcha validation error.'

        if error is None:
            try: 
                key = signing.write_key_to_database(scope='forgot_password', expiration=1, active=1, email=email)
                content = f"A password reset request has been submitted for your account. Please follow this link to complete the reset. {config['domain']}/auth/forgot_password/{key}. Please note this link will expire after one hour."
                current_app.config['MAILER'](subject=f'{config["site_name"]} Password Reset', content=content, to_address=email, logfile=log)
                flash("Password reset link successfully sent.")
            except Exception as e:
                flash(e)
            
        else:
            flash(error)

    if config["smtp_enabled"]:
        return render_template('auth/forgot_password.html',
            site_name=config['site_name'],
            name="Forgot Password", 
            config=config)

    else:
        flash('This feature has not been enabled by your system administrator.')
        return redirect(url_for('auth.login'))

@bp.route('/register', methods=('GET', 'POST'))
def register():

    if not config['allow_anonymous_registration']:
        flash('This feature has not been enabled by your system administrator.')
        return redirect(url_for('auth.login'))

    # we only make this view visible if the user isn't logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))


    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        organization = request.form['organization']
        phone = request.form['phone']
        created_date = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        
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

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        
        # added these per https://github.com/signebedi/libreForms/issues/122
        # to give the freedom to set these as required fields
        elif config['registration_email_required'] and not email:
            error = 'Email is required.'
        elif config['registration_phone_required'] and not phone:
            error = 'Phone is required.'
        elif config['registration_organization_required'] and not organization:
            error = 'Organization is required.'

        elif not re.fullmatch(r"^\w\w\w\w+$", username) or len(username) > 36:
            error = 'username does not formatting standards, length 4 - 36 characters, alphanumeric and underscore characters only.'
        elif email and not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
            error = 'Invalid email.' 
        elif phone and not re.fullmatch(r'^[a-z0-9]{3}-[a-z0-9]{3}-[a-z0-9]{4}$', phone):
            error = 'Invalid phone number (xxx-xxx-xxxx).' 
        elif email and User.query.filter_by(email=email).first():
            error = 'Email is already registered.' 
        elif User.query.filter_by(username=username.lower()).first():
            error = f'Username {username.lower()} is already registered.' 
        elif config['enable_hcaptcha']:
            if not hcaptcha.verify():
                error = 'Captcha validation error.'

        if error is None:
            try:
                new_user = User(
                            email=email, 
                            username=username.lower(), 
                            password=generate_password_hash(password, method='sha256'),
                            organization=organization,
                            group=config['default_group'],
                            certificate=generate_symmetric_key(),
                            phone=phone,
                            theme='dark' if config['dark_mode'] else 'light', # we default to the application default
                            created_date=created_date,
                            active=0 if config["enable_email_verification"] else 1,
                            **TEMP, # https://stackoverflow.com/a/5710402
                        ) 
                db.session.add(new_user)
                db.session.commit()
                if config["enable_email_verification"]:
                    key = signing.write_key_to_database(scope='email_verification', expiration=48, active=1, email=email)
                    current_app.config['MAILER'](subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}. Please verify your email by clicking the following link: {config['domain']}/auth/verify_email/{key}. Please note this link will expire after 48 hours.", to_address=email, logfile=log)
                    flash(f'Successfully created user \'{username.lower()}\'. Please check your email for an activation link. ')
                else:
                    current_app.config['MAILER'](subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}.", to_address=email, logfile=log)
                    flash(f'Successfully created user \'{username.lower()}\'.')
                log.info(f'{username.upper()} - successfully registered with email {email}.')
            except:
                error = f"User is already registered with username \'{username.lower()}\' or email \'{email}\'." if email else f"User is already registered with username \'{username}\'."
                log.error(f'GUEST - failed to register new user {username.lower()} with email {email}.')
            else:
                # current_app.config['MAILER'](subject=f"Successfully Registered {username}", content=f"This is a notification that {username} has been successfully registered for libreforms.", to_address=email, logfile=log)
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html',
        site_name=config['site_name'],
        name="Register",
        config=config,)


@bp.route('/verify_email/<signature>', methods=('GET', 'POST'))
def verify_email(signature):

    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if not config['enable_email_verification']:
        flash('This feature has not been enabled by your system administrator.')
        return redirect(url_for('auth.login'))

    if not signing.verify_signatures(signature, 
                                redirect_to='auth.forgot_password', 
                                scope="email_verification"):


        signing_df = pd.read_sql_table("signing", con=db.engine.connect())
        email = signing_df.loc[ signing_df['signature'] == signature ]['email'].iloc[0]


        try:
            user = User.query.filter_by(email=str(email)).first() ## get email from Signing table & collate to User table 
            user.active=1
            db.session.commit()

            signing.expire_key(signature)
            flash(f"Successfully activated user {user.username}. ")
            log.info(f'{user.username.upper()} - successfully activated user.')
            return redirect(url_for('auth.login'))

        except Exception as e:
            flash (f"There was an error in processing your request. {e}")
        
    
    return redirect(url_for('auth.login'))

if config['enable_rest_api']:

    @bp.route('/register/api', methods=('GET', 'POST'))
    @login_required 
    def generate_api_key():

        if config['limit_rest_api_keys_per_user']:
            signing_df = pd.read_sql_table("signing", con=db.engine.connect())

            # note that this behavior will not apply when an email has not been specified for a given key, which
            # shouldn't be the case as long as emails are required fields at user registration; however, the `libreforms`
            # user, which ships by default with the application, does not have an email set - meaning that the default
            # user will not be constrained by this behavior. This can be viewed as a bug or a feature, depending on context.
            if len(signing_df.loc[(signing_df.email == current_user.email) & (signing_df.scope == 'api_key') & (signing_df.active == 1)]) >= config['limit_rest_api_keys_per_user']:
                flash(f'This user has already registered the number of API keys they are permitted. ')
                return redirect(url_for('auth.profile'))

        key = signing.write_key_to_database(scope='api_key', expiration=5640, active=1, email=current_user.email)
        current_app.config['MAILER'](subject=f'{config["site_name"]} API Key Generated', content=f"This email serves to notify you that the user {current_user.username} has just generated an API key for this email address at {config['domain']}. The API key is: {key}. Please note this key will expire after 365 days.", to_address=current_user.email, logfile=log)
        flash(f'Successfully generated API key {key} for \'{current_user.username.lower()}\'. They should check their email for further instructions. ')

        return redirect(url_for('auth.profile'))

    # this is a placeholder for a future method of registering API keys by non-authorized users ...
    # but for now, let's leave it disabled
    @bp.route('/register/api/<signature>', methods=('GET', 'POST'))
    def anonymous_generate_api_key(signature):

        return abort(404)
        # flash('This feature has not been enabled by your system administrator.')
        # return redirect(url_for('home'))

        # key = signing.write_key_to_database(scope='api_key', expiration=5640, active=1, email=current_user.email)
        # current_app.config['MAILER'](subject=f'{config["site_name"]} API Key Generated', content=f"This email serves to notify you that the user {current_user.username} has just generated an API key for this email address at {config['domain']}. The API key is: {key}. Please note this key will expire after 365 days.", to_address=current_user.email, logfile=log)
        # flash(f'Successfully generated API key {key} for \'{current_user.username.lower()}\'. They should check their email for further instructions. ')

        # return redirect(url_for('auth.profile'))


@bp.route('/register/bulk', methods=('GET', 'POST'))
@login_required
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
                                current_app.config['MAILER'](subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}. Please verify your email by clicking the following link: {config['domain']}/auth/verify_email/{key}. Please note this link will expire after 48 hours.", to_address=row.email, logfile=log)
                                flash(f'Successfully created user \'{row.username.lower()}\'. They should check their email for an activation link. ')
                            else:
                                current_app.config['MAILER'](subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {config['domain']}.", to_address=row.email, logfile=log)
                                flash(f'Successfully created user \'{row.username.lower()}\'.')

                            log.info(f'{row.username.upper()} - successfully registered with email {row.email}.')
                        except Exception as e:
                            # error = f"User is already registered with username \'{row.username.lower()}\' or email \'{row.email}\'." if row.email else f"User is already registered with username \'{row.username}\'. "
                            flash(f"Issue registering {row.username.lower()}. {e}")
                            log.error(f'{current_user.username.upper()} - failed to register new user {row.username.lower()} with email {row.email}.')
                    # else:
                    #     flash(f'Successfully created user \'{bulk_user_df.username.lower()}\'.')
                    #     current_app.config['MAILER'](subject=f"Successfully Registered {username}", content=f"This is a notification that {username} has been successfully registered for libreforms.", to_address=email, logfile=log)
                    #     return redirect(url_for("auth.add_users"))
                flash ("Finished uploading users from CSV.")

            else:
                flash(error)


            # return f"File saved successfully {filepath}"



    return render_template('auth/add_users.html',
        site_name=config['site_name'],
        notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
        name="Bulk Register",
        user=current_user,
        config=config,)


@bp.route('/login', methods=('GET', 'POST'))
def login():

    # we only make this view visible if the user isn't logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))



    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        remember = True if request.form.get('remember') else False

        error = None
        user = User.query.filter_by(username=username.lower()).first()

        if not user:
            error = 'Incorrect username.'
        elif not check_password_hash(user.password, password):
            log.info(f'{username.upper()} - password failure when logging in.')
            error = 'Incorrect password.'
        elif user.active == 0:
            flash('Your user is currently inactive. If you recently registered, please check your email for a verification link. ')
            return redirect(url_for('home'))


        if error is None:
            login_user(user, remember=remember)
            flash(f'Successfully logged in user \'{username.lower()}\'.')
            log.info(f'{username.upper()} - successfully logged in.')
            return redirect(url_for('home'))

        flash(error)

    return render_template('auth/login.html',
            site_name=config['site_name'],
            name="Login",
            config=config,)

@bp.before_app_request
def load_logged_in_user():
    user_id = current_user.get_id()

    if user_id is None:
        user = None
    else:
        user = User.query.filter_by(id=user_id).first()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@bp.route('/profile/edit', methods=('GET', 'POST'))
@login_required
def edit_profile():

    if request.method == 'POST':

        # print([x for x in list(request.form)])
        organization = request.form['organization']
        phone = request.form['phone']
        theme = request.form['theme']
        
        TEMP = {}
        for item in config['user_registration_fields'].keys():
            if config['user_registration_fields'][item]['input_type'] != 'hidden':

                if config['user_registration_fields'][item]['input_type'] == 'checkbox':
                    
                    TEMP[item] = str(request.form.getlist(item))

                else:
                    TEMP[item] = str(request.form[item]) if config['user_registration_fields'][item]['type'] == str else float(request.form[item])

        if phone == "" or None or "None":
            phone = None
        
        if organization == "" or None or "None":
            email = None
        
        if theme not in ['light', 'dark']:
            theme = 'dark'

        error = None

        # added these per https://github.com/signebedi/libreForms/issues/122
        # to give the freedom to set these as required fields
        if config['registration_phone_required'] and not phone:
            error = 'Phone is required.'
        elif config['registration_organization_required'] and not organization:
            error = 'Organization is required.'
        elif phone and not re.fullmatch(r'^[a-z0-9]{3}-[a-z0-9]{3}-[a-z0-9]{4}$', phone):
            error = 'Invalid phone number (xxx-xxx-xxxx).' 
        
        user = User.query.filter_by(email=current_user.email).first()
    
        if error is None:
            try:
                user.organization = organization 
                user.phone = phone 
                user.theme = theme 
                for item in TEMP:
                    setattr(user, item, TEMP[item])

                db.session.commit()

                flash("Successfully updated profile. ")
                log.info(f'{user.username.upper()} - successfully updated their profile.')
                return redirect(url_for('auth.profile'))
            except Exception as e:
                error = f"There was an error in processing your request. {e}"
            
        flash(error)

    return render_template('auth/register.html',
        site_name=config['site_name'],
        edit_profile=True,
        user=current_user,
        notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
        name="Profile",
        config=config,)

@bp.route('/profile', methods=('GET', 'POST'))
@login_required
def profile():

    if request.method == 'POST':
        user_id = current_user.get_id()
        new_password = request.form['new_password']
        current_password = request.form['current_password']

        error = None

        user = User.query.filter_by(id=user_id).first()
    
        if user is None:
            error = 'User does not exist.'
        elif not check_password_hash(user.password, current_password):
            error = 'Incorrect password.'

        if error is None:

            try:
                user.password=generate_password_hash(new_password, method='sha256')
                db.session.commit()

                flash("Successfully changed password. ")
                log.info(f'{user.username.upper()} - successfully changed password.')
                return redirect(url_for('auth.profile'))
            except:
                error = f"There was an error in processing your request."
            
        flash(error)


    return render_template('auth/profile.html', 
        type="profile",
        name=config['site_name'],
        config=config,
        notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
        user=current_user,
        log_data=aggregate_log_data(keyword=f'- {current_user.username.upper()} -', limit=1000, pull_from='end') if config['enable_user_profile_log_aggregation'] else None,
    )

# this is the download link for files in the temp directory
@bp.route('/download/<path:filename>')
@login_required
def download_bulk_user_template(filename='bulk_user_template.csv'):

    # this is our first stab at building templates, without accounting for nesting or repetition
    df = pd.DataFrame (columns=["username", "email", "password", "group", "phone", "organization",'theme'])

    # if we set custom user fields, add these here
    if config['user_registration_fields']:
        for x in config['user_registration_fields'].keys():

            # we only add the field if it is not a 'hidden' registration field
            if config['user_registration_fields'][x]['input_type'] != 'hidden':
                df[x] = None

    # here we employ a context-bound temp directory to stage this file for download, see
    # discussion in app.tmpfiles and https://github.com/signebedi/libreForms/issues/169.        
    from app.tmpfiles import temporary_directory
    with temporary_directory() as tempfile_path:
        fp = os.path.join(tempfile_path, filename)
        df.to_csv(fp, index=False)

        return send_from_directory(tempfile_path,
                                filename, as_attachment=True)