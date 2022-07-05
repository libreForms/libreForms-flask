import functools, re, datetime

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from app import display, log, db
from app.models import User
from flask_login import login_required, current_user, login_user

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
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
        elif email and not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
            error = 'Invalid email.' 
        elif phone and not re.fullmatch(r'^[a-z0-9]{3}-[a-z0-9]{3}-[a-z0-9]{4}$', phone):
            error = 'Invalid phone number (xxx-xxx-xxxx).' 
        elif User.query.filter_by(email=email).first():
            error = 'Email is already registered.' 
        elif User.query.filter_by(username=username).first():
            error = 'Username is already registered.' 

        if error is None:
            try:
                new_user = User(
                            email=email, 
                            username=username, 
                            password=generate_password_hash(password, method='sha256'),
                            organization=organization,
                            phone=phone,
                            created_date=created_date,
                        )
                db.session.add(new_user)
                db.session.commit()
                log.info(f'registered new user {username} with email {email}.')
            except db.IntegrityError:
                error = f"User is already registered with username \'{username}\' or email \'{email}\'." if email else f"User is already registered with username \'{username}\'."
                log.error(f'failed to register new user {username} with email {email}.')
            else:
                flash(f'Successfully created user \'{username}\'.')
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html',
        site_name=display['site_name'],
        display_warning_banner=True,
        name="Register",
        display=display,)



@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        remember = True if request.form.get('remember') else False

        error = None
        user = User.query.filter_by(username=username).first()

        if not user:
            error = 'Incorrect username.'
        elif not check_password_hash(user.password, password):
            # log.info(f'password failure when logging in user {username}.')
            error = 'Incorrect password.'

        if error is None:
            login_user(user, remember=remember)
            flash(f'Successfully logged in user \'{username}\'.')
            log.info(f'successfully logged in user {username}.')
            return redirect(url_for('home'))

        flash(error)

    return render_template('auth/login.html',
            site_name=display['site_name'],
            name="Login",
            display_warning_banner=True,   
            display=display,)

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

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
        user_id = session.get('user_id')
        new_password = request.form['new_password']
        current_password = request.form['current_password']

        error = None

        user = User.query.filter_by(id=user_id).first()
    
        if user is None:
            error = 'User does not exist.'
        elif not check_password_hash(user['password'], current_password):
            error = 'Incorrect password.'

        if error is None:

            try:
                db.execute(
                    "UPDATE user SET password=? WHERE id=?",
                    (generate_password_hash(new_password), user_id),
                )
                db.commit()
                flash("Successfully changed password")
                # log.info(f'successfully changed password for user {session.get("username")}.')
                return redirect(url_for('auth.profile'))
            except db.IntegrityError:
                error = f"There was an error in processing your request."
            
        flash(error)


    return render_template('app/profile.html', 
        type="profile",
        name=display['site_name'],
        display=display,
        user=current_user,
    )