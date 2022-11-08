import functools, re, datetime, tempfile, os
import pandas as pd

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from app import display, log, db, mailer, tempfile_path
import app.signing as signing
from app.models import User, Signing
from flask_login import login_required, current_user, login_user

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/forgot_password/<signature>', methods=('GET', 'POST'))
def reset_password(signature):

    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if not display['allow_password_resets']:
        flash('This feature has not been enabled by your system administrator.')
        return redirect(url_for('auth.forgot_password'))

    if not Signing.query.filter_by(signature=signature).first():
        flash('Invalid request key. ')
        return redirect(url_for('auth.forgot_password'))

    # if the signing key's expiration time has passed, then set it to inactive 
    if Signing.query.filter_by(signature=signature).first().expiration < datetime.datetime.timestamp(datetime.datetime.now()):
        signing.expire_key(signature)

    # if the signing key is set to inactive, then we prevent the user from proceeding
    # this might be redundant to the above condition - but is a good redundancy for now
    if Signing.query.filter_by(signature=signature).first().active== 0:
        flash('Invalid request key. ')
        return redirect(url_for('auth.forgot_password'))


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
        site_name=display['site_name'],
        display_warning_banner=True,
        name="Reset Password", 
        reset=True,
        display=display)



@bp.route('/forgot_password', methods=('GET', 'POST'))
def forgot_password():

    # we only make this view visible if the user isn't logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST' and display["smtp_enabled"]:
        email = request.form['email']

        if not User.query.filter_by(email=email.lower()).first():
            error = f'Email {email.lower()} is not registered.' 
        
        else: error = None

        if error is None:
            try: 
                key = signing.write_key_to_database(scope='forgot_password', expiration=1, active=1, email=email)
                content = f"A password reset request has been submitted for your account. Please follow this link to complete the reset. {display['domain']}/auth/forgot_password/{key}. Please note this link will expire after one hour."
                mailer.send_mail(subject=f'{display["site_name"]} Password Reset', content=content, to_address=email, logfile=log)
                flash("Password reset link successfully sent.")
            except Exception as e:
                flash(e)
            
        else:
            flash(error)

    if display["smtp_enabled"]:
        return render_template('auth/forgot_password.html',
            site_name=display['site_name'],
            display_warning_banner=True,
            name="Forgot Password", 
            display=display)

    else:
        flash('This feature has not been enabled by your system administrator.')
        return redirect(url_for('auth.login'))

@bp.route('/register', methods=('GET', 'POST'))
def register():

    if not display['allow_anonymous_registration']:
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
        for item in display['user_registration_fields'].keys():
            if display['user_registration_fields'][item]['input_type'] != 'hidden':
                TEMP[item] = str(request.form[item]) if display['user_registration_fields'][item]['type'] == str else float(request.form[item])

        if phone == "":
            phone = None
        
        if email == "":
            email = None

        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
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

        if error is None:
            try:
                new_user = User(
                            email=email, 
                            username=username.lower(), 
                            password=generate_password_hash(password, method='sha256'),
                            organization=organization,
                            phone=phone,
                            created_date=created_date,
                            active=0 if display["enable_email_verification"] else 1,
                            **TEMP, # https://stackoverflow.com/a/5710402
                        ) 
                db.session.add(new_user)
                db.session.commit()
                if display["enable_email_verification"]:
                    key = signing.write_key_to_database(scope='email_verification', expiration=48, active=1, email=email)
                    mailer.send_mail(subject=f'{display["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {display['domain']}. Please verify your email by clicking the following link: {display['domain']}/auth/verify_email/{key}. Please note this link will expire after 48 hours.", to_address=email, logfile=log)
                    flash(f'Successfully created user \'{username.lower()}\'. Please check your email for an activation link. ')
                else:
                    mailer.send_mail(subject=f'{display["site_name"]} User Registered', content=f"This email serves to notify you that the user {username} has just been registered for this email address at {display['domain']}.", to_address=email, logfile=log)
                    flash(f'Successfully created user \'{username.lower()}\'.')
                log.info(f'{username.upper()} - successfully registered with email {email}.')
            except:
                error = f"User is already registered with username \'{username.lower()}\' or email \'{email}\'." if email else f"User is already registered with username \'{username}\'."
                log.error(f'GUEST - failed to register new user {username.lower()} with email {email}.')
            else:
                # mailer.send_mail(subject=f"Successfully Registered {username}", content=f"This is a notification that {username} has been successfully registered for libreforms.", to_address=email, logfile=log)
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html',
        site_name=display['site_name'],
        display_warning_banner=True,
        name="Register",
        display=display,)


@bp.route('/verify_email/<signature>', methods=('GET', 'POST'))
def verify_email(signature):

    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if not display['enable_email_verification']:
        flash('This feature has not been enabled by your system administrator.')
        return redirect(url_for('auth.login'))

    if not Signing.query.filter_by(signature=signature).first():
        flash('Invalid request key. ')
        return redirect(url_for('auth.forgot_password'))

    # if the signing key's expiration time has passed, then set it to inactive 
    if Signing.query.filter_by(signature=signature).first().expiration < datetime.datetime.timestamp(datetime.datetime.now()):
        signing.expire_key(signature)

    # if the signing key is set to inactive, then we prevent the user from proceeding
    # this might be redundant to the above condition - but is a good redundancy for now
    if Signing.query.filter_by(signature=signature).first().active== 0:
        flash('Invalid request key. ')
        return redirect(url_for('auth.forgot_password'))

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

    # if key exists and is active:
    #     register User
    #     flash them a message
    #     redirect to login

    # else:
    #     invalid link

@bp.route('/register/bulk', methods=('GET', 'POST'))
@login_required
def bulk_register():

    if not display['allow_bulk_registration']:
        flash('This feature has not been enabled by your system administrator.')
        return redirect(url_for('home'))


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

                    for x in ["username", "email", "password"]: # a minimalist common sense check
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

                    else:
                        try: 
                            new_user = User(
                                        email=row.email, 
                                        username=row.username.lower(), 
                                        password=generate_password_hash(row.password, method='sha256'),
                                        # organization=row.organization if row.organization else "",
                                        # phone=row.phone if row.phone else "",
                                        created_date=created_date,
                                    )
                            db.session.add(new_user)
                            db.session.commit()
                            mailer.send_mail(subject=f'{display["site_name"]} User Registered', content=f"This email serves to notify you that the user {row.username} has just been registered for this email address at {display['domain']}.", to_address=row.email, logfile=log)
                            log.info(f'{row.username.upper()} - successfully registered with email {row.email}.')
                        except Exception as e:
                            # error = f"User is already registered with username \'{row.username.lower()}\' or email \'{row.email}\'." if row.email else f"User is already registered with username \'{row.username}\'. "
                            flash(f"Issue registering {row.username.lower()}. {e}")
                            log.error(f'{current_user.username.upper()} - failed to register new user {row.username.lower()} with email {row.email}.')
                    # else:
                    #     flash(f'Successfully created user \'{bulk_user_df.username.lower()}\'.')
                    #     mailer.send_mail(subject=f"Successfully Registered {username}", content=f"This is a notification that {username} has been successfully registered for libreforms.", to_address=email, logfile=log)
                    #     return redirect(url_for("auth.add_users"))
                flash ("Finished uploading users from CSV.")

            else:
                flash(error)


            # return f"File saved successfully {filepath}"



    return render_template('auth/add_users.html',
        site_name=display['site_name'],
        display_warning_banner=True,
        name="Bulk Register",
        user=current_user,
        display=display,)


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
            site_name=display['site_name'],
            name="Login",
            display_warning_banner=True,   
            display=display,)

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
        name=display['site_name'],
        display=display,
        user=current_user,
    )

# this is the download link for files in the temp directory
@bp.route('/download/<path:filename>')
@login_required
def download_bulk_user_template(filename='bulk_user_template.csv'):

    # this is our first stab at building templates, without accounting for nesting or repetition
    df = pd.DataFrame (columns=["username", "email", "password", "phone", "organization"])

    fp = os.path.join(tempfile_path, filename)
    df.to_csv(fp, index=False)

    return send_from_directory(tempfile_path,
                            filename, as_attachment=True)