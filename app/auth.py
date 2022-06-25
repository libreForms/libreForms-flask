import functools, re, datetime

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db
from app import display


def check_proper_regex(regex, msg):
 
    # pass the regular expression
    # and the string into the fullmatch() method
    if(re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email)):
        print("Valid Email")
 
    else:
        print("Invalid Email")


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

        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
            error = 'Invalid email.'
        elif not re.fullmatch(r'^[a-z0-9]{3}-[a-z0-9]{3}-[a-z0-9]{4}$', phone):
            error = 'Invalid phone number (xxx-xxx-xxxx).'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (username, password, organization, created_date, phone, email) VALUES (?, ?, ?, ?, ?, ?)",
                    (username, generate_password_hash(password), organization, created_date, phone, email),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User is already registered with username \'{username}\' or email \'{email}\'."
            else:
                flash(f'Successfully created user \'{username}\'.')
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html',
        site_name=display['site_name'],
        name="Register",
        display=display,)



@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            flash(f'Successfully logged in user \'{username}\'.')
            return redirect(url_for('home'))

        flash(error)

    return render_template('auth/login.html',
            site_name=display['site_name'],
            name="Login",
            display=display,)

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view


@bp.route('/profile', methods=('GET', 'POST'))
@login_required
def profile():

    if request.method == 'POST':
        user_id = session.get('user_id')
        new_password = request.form['new_password']
        current_password = request.form['current_password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()
    
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
                return redirect(url_for('auth.profile'))
            except db.IntegrityError:
                error = f"There was an error in processing your request."
            
        flash(error)


    return render_template('app/profile.html', 
        type="profile",
        name=display['site_name'],
        display=display,
    )