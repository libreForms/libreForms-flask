import functools, re, datetime

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from app import display, log, db, app
from app.models import User
from flask_login import login_required, current_user, login_user

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/forgot_password', methods=('GET', 'POST'))
def forgot_password():

    if request.method == 'POST' and display["smtp_enabled"]:
        email = request.form['email']

        if not User.query.filter_by(email=email.lower()).first():
            error = f'Email {email.lower()} is not registered.' 
        else:
            pass



    return render_template('auth/forgot_password.html',
        site_name=display['site_name'],
        display_warning_banner=True,
        name="Forgot Password", 
        display=display)

    # if X && app.config["SMTP_ENABLED"]:
    #     send_mail(self, subject=None, content=None, to_address=None, logfile=None):



@bp.route('/register', methods=('GET', 'POST'))
def register():

    if not display['allow_anonymous_registration']:
        return render_template('404.html',
            site_name=display['site_name'],
            display_warning_banner=True,
            name="404", 
            display=display)

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
                        )
                db.session.add(new_user)
                db.session.commit()
                log.info(f'{username.upper()} - successfully registered with email {email}.')
            except:
                error = f"User is already registered with username \'{username.lower()}\' or email \'{email}\'." if email else f"User is already registered with username \'{username}\'."
                log.error(f'GUEST - failed to register new user {username.lower()} with email {email}.')
            else:
                flash(f'Successfully created user \'{username.lower()}\'.')
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html',
        site_name=display['site_name'],
        display_warning_banner=True,
        name="Register",
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

                flash("Successfully changed password")
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