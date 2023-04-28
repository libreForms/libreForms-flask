""" 
auth.py: implementation of auth views and underlying logic



"""

__name__ = "app.views.auth"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.9.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


import functools, re, datetime, tempfile, os, uuid, random, json
import pandas as pd
from urllib.parse import urlparse

from flask import current_app, Blueprint, flash, g, redirect, render_template, request, session, url_for, send_from_directory, abort, make_response, Response
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_required, login_user, logout_user, current_user


from app import config, log, mailer
import app.signing as signing
from app.models import User, Signing, db
from app.log_functions import aggregate_log_data
from app.certification import generate_symmetric_key
from celeryd.tasks import send_mail_async
from app.views.forms import standard_view_kwargs


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
        flash('This feature has not been enabled by your system administrator.', "warning")
        return redirect(url_for('auth.forgot_password'))
    
    if not signing.verify_signatures(signature, redirect_to='auth.forgot_password', 
                                        scope="forgot_password"):

        if request.method == 'POST':
            password = request.form['password']
            reenter_password = request.form['reenter_new_password']
            signing_df = pd.read_sql_table("signing", con=db.engine.connect())
            email = signing_df.loc[ signing_df['signature'] == signature ]['email'].iloc[0]

            if not password:
                error = 'Password is required. '
            elif not re.fullmatch(config['password_regex'], password):
                error = f'Invalid password. ({config["user_friendly_password_regex"]}) '
            elif password != reenter_password:
                error = 'Passwords do not match. '

            else: error = None

            if error is None:
                try:
                    user = User.query.filter_by(email=str(email)).first() ## get email from Signing table & collate to User table 
                    user.password=generate_password_hash(password, method='sha256')
                    db.session.commit()

                    signing.expire_key(signature)
                    flash("Successfully changed password. ", "success")
                    log.info(f'{user.username.upper()} - successfully changed password.')
                    return redirect(url_for('auth.login'))
                except Exception as e: 
                    transaction_id = str(uuid.uuid1())
                    log.warning(f"LIBREFORMS - {e}", extra={'transaction_id': transaction_id})
                    flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ")
                
            else:
                flash(error, "warning")
    
        return render_template('auth/forgot_password.html.jinja',
            name='User',
            subtitle='Reset Password',
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
            error = f'Email {email.lower()} is not registered. ' 
                        
        else: error=None
        
        if config['enable_hcaptcha']:
            if not hcaptcha.verify():
                error = 'Captcha validation error. '

        if error is None:
            try: 
                key = signing.write_key_to_database(scope='forgot_password', expiration=1, active=1, email=email)
                content = f"A password reset request has been submitted for your account. Please follow this link to complete the reset. {config['domain']}/auth/forgot_password/{key}. Please note this link will expire after one hour."
                m = send_mail_async.delay(subject=f'{config["site_name"]} Password Reset', content=content, to_address=email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} Password Reset', content=content, to_address=email, logfile=log)
                flash("Password reset link successfully sent.", "success")
            except Exception as e: 
                transaction_id = str(uuid.uuid1())
                log.warning(f"LIBREFORMS - {e}", extra={'transaction_id': transaction_id})
                flash(f"Could not send password reset link. Transaction ID: {transaction_id}. ", "warning")
            
        else:
            flash(error, "warning")

    if config["smtp_enabled"]:
        return render_template('auth/forgot_password.html.jinja',
            name='User',
            subtitle='Forgot Password',
            config=config)

    else:
        flash('This feature has not been enabled by your system administrator.', "warning")
        return redirect(url_for('auth.login'))

@bp.route('/register', methods=('GET', 'POST'))
def register():

    if not config['allow_anonymous_registration']:
        flash('This feature has not been enabled by your system administrator.', "warning")
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

        reenter_password = request.form['reenter_password']

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
        elif not password:
            error = 'Password is required. '
        
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
        elif password != reenter_password:
            error = 'Passwords do not match. '
        elif not re.fullmatch(config['password_regex'], password):
            error = f'Invalid password. ({config["user_friendly_password_regex"]}) '
        elif config['enable_hcaptcha']:
            if not hcaptcha.verify():
                error = 'Captcha validation error. '

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
                    m = send_mail_async.delay(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}. Please verify your email by clicking the following link: {config['domain']}/auth/verify_email/{key}. Please note this link will expire after 48 hours.", to_address=email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}. Please verify your email by clicking the following link: {config['domain']}/auth/verify_email/{key}. Please note this link will expire after 48 hours.", to_address=email, logfile=log)
                    flash(f'Successfully created user \'{username.lower()}\'. Please check your email for an activation link. ', "success")
                else:
                    m = send_mail_async.delay(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}.", to_address=email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {config['domain']}.", to_address=email, logfile=log)
                    flash(f'Successfully created user \'{username.lower()}\'.', "success")
                log.info(f'{username.upper()} - successfully registered with email {email}.')
            except Exception as e: 
                error = f"User is already registered with username \'{username.lower()}\' or email \'{email}\'." if email else f"User is already registered with username \'{username}\'. "
                log.error(f'LIBREFORMS - failed to register new user {username.lower()} with email {email}. {e}', extra={'transaction_id': transaction_id})
            else:
                # m = send_mail_async.delay(subject=f"Successfully Registered {username}", content=f"This is a notification that {username} has been successfully registered for libreforms.", to_address=email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f"Successfully Registered {username}", content=f"This is a notification that {username} has been successfully registered for libreforms.", to_address=email, logfile=log)
                return redirect(url_for("auth.login"))

        flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ", 'warning')


    return render_template('auth/register.html.jinja',
        name='User',
        subtitle='Register',
        config=config,)


@bp.route('/verify_email/<signature>', methods=('GET', 'POST'))
def verify_email(signature):

    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if not config['enable_email_verification']:
        flash('This feature has not been enabled by your system administrator.', "warning")
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
            flash(f"Successfully activated user {user.username}. ", "success")
            log.info(f'{user.username.upper()} - successfully activated user.')
            return redirect(url_for('auth.login'))

        except Exception as e: 
            transaction_id = str(uuid.uuid1())
            log.warning(f"LIBREFORMS - {e}", extra={'transaction_id': transaction_id})
            flash (f"There was an error in processing your request. Transaction ID: {transaction_id}. ", 'warning')
        
    
    return redirect(url_for('auth.login'))

if (config['enable_v1_rest_api'] or config['enable_v2_rest_api']) and config['allow_user_api_key_generation']:

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
                flash(f'This user has already registered the maximum number of API keys they are permitted. ', "warning")
                return redirect(url_for('auth.profile'))

        key = signing.write_key_to_database(scope='api_key', expiration=5640, active=1, email=current_user.email)
        m = send_mail_async.delay(subject=f'{config["site_name"]} API Key Generated', content=f"This email serves to notify you that the user {current_user.username} has just generated an API key for this email address at {config['domain']}. The API key is: {key}. Please note this key will expire after 365 days.", to_address=current_user.email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} API Key Generated', content=f"This email serves to notify you that the user {current_user.username} has just generated an API key for this email address at {config['domain']}. The API key is: {key}. Please note this key will expire after 365 days.", to_address=current_user.email, logfile=log)
        flash(f'Successfully generated API key {key} for \'{current_user.username.lower()}\'. They should check their email for further instructions. ', "success")

        return redirect(url_for('auth.profile'))

    # this is a placeholder for a future method of registering API keys by non-authorized users ...
    # but for now, let's leave it disabled
    # @bp.route('/register/api/<signature>', methods=('GET', 'POST'))
    # def anonymous_generate_api_key(signature):

    #     return abort(404)
        # flash('This feature has not been enabled by your system administrator.')
        # return redirect(url_for('home'))

        # key = signing.write_key_to_database(scope='api_key', expiration=5640, active=1, email=current_user.email)
        # m = send_mail_async.delay(subject=f'{config["site_name"]} API Key Generated', content=f"This email serves to notify you that the user {current_user.username} has just generated an API key for this email address at {config['domain']}. The API key is: {key}. Please note this key will expire after 365 days.", to_address=current_user.email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=f'{config["site_name"]} API Key Generated', content=f"This email serves to notify you that the user {current_user.username} has just generated an API key for this email address at {config['domain']}. The API key is: {key}. Please note this key will expire after 365 days.", to_address=current_user.email, logfile=log)
        # flash(f'Successfully generated API key {key} for \'{current_user.username.lower()}\'. They should check their email for further instructions. ')

        # return redirect(url_for('auth.profile'))

@bp.route('/mfa', methods=('GET', 'POST'))
def mfa():

    # we only make this view visible if the user isn't logged in
    if current_user.is_authenticated:
        return redirect(request.referrer or url_for('auth.login'))

    if not session.get('valid_credentials') or not session.get('user_email'):
        return redirect(url_for('auth.mfa'))

    if request.method == 'POST':

        # get MFA token from POST vars
        signature = request.form['signature']

        # validate MFA token and, if right, expire MFA token and create user session
        if not signing.verify_signatures(signature, redirect_to='auth.mfa', 
                                        scope="mfa"):

            signing_df = pd.read_sql_table("signing", con=db.engine.connect())
            email = signing_df.loc[ signing_df['signature'] == signature ]['email'].iloc[0]
            user = User.query.filter_by(email=str(email)).first() ## get email from Signing table & collate to User table 

            # we check to verify this is the user in question and clear the old session before fully logging user in
            session_email = session.get('user_email')
            if not email == session_email:
                flash(f'Invalid request key. Key not eligible for account associated with {session_email}.', "warning")
                return redirect(url_for('auth.mfa'))
            session.clear()

            # log the user in
            login_user(user)
            flash(f'Successfully logged in user \'{current_user.username.lower()}\'.', "success")
            log.info(f'{current_user.username.upper()} - successfully logged in.')
            signing.expire_key(signature)
            return redirect(url_for('home'))

    return render_template('auth/mfa.html.jinja',
            name='User',
            subtitle='Verify MFA',
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
            error = 'Incorrect username. '
        elif not check_password_hash(user.password, password):
            log.info(f'{username.upper()} - password failure when logging in.')
            error = 'Incorrect password. '
        elif user.active == 0:
            flash('Your user is currently inactive. If you recently registered, please check your email for a verification link. ', "warning")
            return redirect(url_for('home'))


        if error is None:

            if config['enable_email_login_mfa']:
                try: 
                    email = user.email

                    # we also check for existing MFA tokens for this user, and expire them if they are not already expired.
                    signatures = Signing.query.filter_by(email=email, scope="mfa", active=1).all()
                    if len(signatures) > 0:
                        for signature in signatures:
                            signature.active = 0
                        db.session.commit()

                    # then we create and distribute the MFA token
                    key = signing.write_key_to_database(scope='mfa', expiration=1, active=1, email=email)
                    subject = f'{config["site_name"]} Login MFA token'
                    content = f"A login attempt has just been made for this account at {config['domain']}. Use the following key to complete the login process:\n\n{key}\n\nPlease note this link will expire after one hour. If you believe this email was sent by mistake, please contact your system administrator."
                    m = send_mail_async.delay(subject=subject, content=content, to_address=email) if config['send_mail_asynchronously'] else mailer.send_mail(subject=subject, content=content, to_address=email, logfile=log)
                    flash("An MFA token has been sent to the email associated with your user account.", "success")

                    session['valid_credentials'] = True
                    session['user_email'] = email
                    
                    return redirect(url_for('auth.mfa'))

                except Exception as e: 
                    transaction_id = str(uuid.uuid1())
                    log.warning(f"LIBREFORMS - {e}", extra={'transaction_id': transaction_id})
                    flash(f"Could not send MFA token email. Transaction ID: {transaction_id}. ", "warning")
                    return redirect(url_for('auth.login'))

            login_user(user, remember=remember)
            flash(f'Successfully logged in user \'{username.lower()}\'.', "success")
            log.info(f'{username.upper()} - successfully logged in.')
            return redirect(url_for('home'))

        flash(error, "warning")

    return render_template('auth/login.html.jinja',
            name='User',
            subtitle='Login',
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
        # for x in list(request.form):
        #     print(x)

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

        user = User.query.filter_by(email=current_user.email).first()
    
        if error is None:
            try:
                user.organization = organization 
                user.phone = phone 
                user.theme = theme 
                for item in TEMP:
                    setattr(user, item, TEMP[item])

                db.session.commit()

                flash(f"Successfully updated profile. ", "success")
                log.info(f'{user.username.upper()} - successfully updated their profile.')
                return redirect(url_for('auth.profile'))
                
            except Exception as e: 
                transaction_id = str(uuid.uuid1())
                log.warning(f"LIBREFORMS - {e}", extra={'transaction_id': transaction_id})
                error = f"There was an error in processing your request. Transaction ID: {transaction_id}. "
            
        flash(error, "warning")

    return render_template('auth/register.html.jinja',
        edit_profile=True,
        name='User',
        subtitle='Edit Profile',
        user_data=current_user, # this is the data that populates the user fields
        **standard_view_kwargs(),
        )

@bp.route('/profile', methods=('GET', 'POST'))
@login_required
def profile():

    if request.method == 'POST':
        user_id = current_user.get_id()
        new_password = request.form['new_password']
        reenter_new_password = request.form['reenter_new_password']
        current_password = request.form['current_password']

        error = None

        user = User.query.filter_by(id=user_id).first()
    
        if user is None:
            error = 'User does not exist. '
        elif not check_password_hash(user.password, current_password):
            error = 'Incorrect password. '
        elif new_password != reenter_new_password:
            error = 'Passwords do not match. '
        elif new_password == current_password:
            error = 'Your new password cannot be the same as your old password. Please choose a different password. '
        elif not re.fullmatch(config['password_regex'], new_password):
            error = f'Invalid password. ({config["user_friendly_password_regex"]}) '

        if error is None:

            try:
                user.password=generate_password_hash(new_password, method='sha256')
                db.session.commit()

                flash("Successfully changed password. ", "success")
                log.info(f'{user.username.upper()} - successfully changed password.', "success")
                return redirect(url_for('auth.profile'))
            except Exception as e: 
                transaction_id = str(uuid.uuid1())
                log.warning(f"LIBREFORMS - {e}" , extra={'transaction_id': transaction_id})
                error = f"There was an error in processing your request. Transaction ID: {transaction_id}. "
            
        flash(error, "warning")


    return render_template('auth/profile.html.jinja', 
        type="profile",
        name='User',
        subtitle='Profile',
        api_keys=[x.signature for x in Signing.query.filter_by(email=current_user.email, scope="api_key").all()] if config['enable_user_profile_api_key_aggregation'] else None,
        log_data=aggregate_log_data(keyword=f'- {current_user.username.upper()} -', limit=1000, pull_from='end') if config['enable_user_profile_log_aggregation'] else None,
        **standard_view_kwargs(),
    )

@bp.route('/profile/<username>')
@login_required
def other_profiles(username):

    if username == current_user.username:
        return redirect(url_for('auth.profile'))

    if not config['enable_other_profile_views']:
        flash('This feature has not been enabled by your system administrator. ', "warning")
        return redirect(url_for('auth.profile'))

    try:
        # print(len(User.query.filter_by(username=username.lower())))
        # assert (len(User.query.filter_by(username=username.lower())) > 0)
        profile_user = User.query.filter_by(username=username.lower()).first()
        assert(profile_user.username) # assert that the user query has a username set
    except:
        flash('This user does not exist. ', "warning")
        return redirect(url_for('auth.profile'))

    return render_template('auth/other_profiles.html.jinja', 
        type="profile",
        name='User',
        subtitle=f'{username}',
        profile_user=profile_user,
        **standard_view_kwargs(),
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


############################
# Front-end field validation
############################

@bp.route(f'/lint', methods=['GET', 'POST'])
def lint_user_field():

    def validate_option(field, value):

        if field in ['username','email', 'organization', 'phone', 'password']:
            regex = config[f'{field}_regex']
            error_msg = config[f'user_friendly_{field}_regex']

        elif field in config['user_registration_fields']:
            if "regex" in config['user_registration_fields'][field]:
                regex = config['user_registration_fields'][field]["regex"]
            
                if "user_friendly_regex" in config['user_registration_fields'][field]:
                    error_msg = config['user_registration_fields'][field]['user_friendly_regex']
                else:
                    error_msg = f"Provided value does not meet validation requirements set by your system administrator."
            
            # if no regex has been passed, we must assume that the end user has not
            # set any restrictions on acceptable inputs
            else:
                return True

        else:
            return "This field cannot be verified"

        # print(regex)

        validator = lambda x: bool(re.compile(regex).match(str(x)))

        try:
            if field == 'username':
                user = User.query.filter_by(username=value).first()
                assert not user, "An account is already registered to this username."

            elif field == 'email':
                email = User.query.filter_by(email=value).first()
                assert not email, "An account is already registered to this email addresss."

            assert validator(value), error_msg

        except Exception as e:
            return str(e)

        return True

    if request.method == 'POST':
        # print(request)

        # string = request.json['string']
        field = request.json['field']
        value = request.json['value']

        # print(field, value)

        v = validate_option(field, value)

        if type(v) == bool:
            return Response(json.dumps({'status':'success'}), status=config['success_code'], mimetype='application/json')

        return Response(json.dumps({'status':'failure', 'msg': v}), status=config['error_code'], mimetype='application/json')

    return abort(404)


#####################
# SAML-related routes
#####################


if config['saml_enabled']:

    # import saml dependencies 
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.utils import OneLogin_Saml2_Utils

    def load_user_by_email(email, username=None, group=None):
        user = User.query.filter_by(email=email).first()
        # create the user if none exists
        if not user:

            # here we verify that the username doesn't exist in the database; 
            # if it does, we append a random digit to the end until we have a 
            # unique username
            base_username = username if username else email.split('@')[0]
            new_username = base_username
            while User.query.filter_by(username=new_username).first() is not None:
                random_digit = random.randint(0, 9)
                new_username = f"{base_username}{random_digit}"
        
            user = User(email=email,
                        username=new_username,
                        active=1,
                        group=group if group else config['default_group'],
                        theme='dark' if config['dark_mode'] else 'light', 
                        created_date=datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
            )
            db.session.add(user)
            db.session.commit()
        return user


    def prepare_saml_request(request):

        parsed_url = urlparse(config['domain'])
        host = parsed_url.netloc + parsed_url.path

        return {
            'https': 'on' if config['domain'].startswith('https://') else 'off',
            'http_host': host,
            'server_port': None,
            'script_name': request.path,
            'get_data': request.args.copy(),
            'post_data': request.form.copy(),
            'query_string': request.query_string
        }

    # this route is used to initiate SSO login FROM THE SP / CURRENT APPLICATION
    @bp.route('/sso', methods=['GET', 'POST'])
    def sso():
        req_data = prepare_saml_request(request)
        saml_auth = OneLogin_Saml2_Auth(req_data, current_app.config['SAML_AUTH'])
        return redirect(saml_auth.login())


    @bp.route('/acs', methods=['GET', 'POST'])
    def acs():
        req_data = prepare_saml_request(request)
        saml_auth = OneLogin_Saml2_Auth(req_data, current_app.config['SAML_AUTH'])
        saml_auth.process_response()

        errors = saml_auth.get_errors()
        if len(errors) == 0:
            if not saml_auth.is_authenticated():
                flash('SAML authentication failed.', 'warning')
                return redirect(url_for('auth.login'))

            attributes = saml_auth.get_attributes()
            email = attributes.get('email', [None])[0]
            username = attributes.get('username', [None])[0]
            group = attributes.get('group', [None])[0]

            if email:
                user = load_user_by_email(email, username, group)
                login_user(user)
                return redirect(url_for('home'))
            else:
                flash("SAML response doesn't contain an email attribute.", 'warning')
                return redirect(url_for('auth.login'))
        else:
            saml_response = saml_auth.get_last_response_xml()
            flash(f'SAML authentication error: {saml_auth.get_last_error_reason()}. SAML response: {saml_response}', 'warning')
            return redirect(url_for('auth.login'))


    @bp.route('/metadata', methods=['GET'])
    def metadata():
        req_data = prepare_saml_request(request)
        saml_auth = OneLogin_Saml2_Auth(req_data, current_app.config['SAML_AUTH'])
        metadata = saml_auth.get_settings().get_sp_metadata()
        errors = saml_auth.get_errors()
        if not errors:
            response = make_response(metadata, 200)
            response.headers['Content-Type'] = 'text/xml'
            return response
        else:
            return 'An error occurred while generating the metadata'


    @bp.route('/sls', methods=['GET', 'POST'])
    def sls():
        req_data = prepare_saml_request(request)
        saml_auth = OneLogin_Saml2_Auth(req_data, current_app.config['SAML_AUTH'])
        saml_auth.process_slo()

        errors = saml_auth.get_errors()
        if len(errors) == 0:
            if saml_auth.is_authenticated():
                # If the user is still authenticated, log them out locally.
                session.clear()

            # Redirect the user to the login page after successful logout
            return redirect(url_for('home'))
        else:
            saml_response = saml_auth.get_last_response_xml()
            flash(f'SAML authentication error: {saml_auth.get_last_error_reason()}. SAML response: {saml_response}', 'warning')
            return redirect(url_for('auth.login'))