import os
from flask import Flask, render_template, session
import app.log_functions
# from flask_admin import Admin
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from libreforms import __version__
from app.display import display
import pandas as pd
from app.csv_files import init_tmp_fs, tempfile_init_tmp_fs
from app import smtp_config

db = SQLAlchemy()

tempfile_path = tempfile_init_tmp_fs()

# if application log path doesn't exist, make it
if not os.path.exists ("log/"):
    os.mkdir('log/')

# we instantiate a log object that 
# we'll propagate across the app

log = app.log_functions.set_logger('log/libreforms.log',__name__)
log.info('LIBREFORMS - started libreforms web application.')

# # non-destructively initialize a tmp file system for the app 
# init_tmp_fs(delete_first=False)

def create_app(test_config=None):
 
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(app.instance_path, "app.sqlite")}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # FLASK_ADMIN_SWATCH='darkly',
    )


    # admin = Admin(app, name='libreForms', template_mode='bootstrap4')
    # Add administrative views here


    if os.path.exists ("smtp_creds"):
        smtp_creds = pd.read_csv("smtp_creds", dtype=str) # expecting the CSV format: smtp_server,port,username,password,from_address
        SMTP_ENABLED=True # we should do something with this later on
        log.info(f'LIBREFORMS - found an SMTP credentials file using {smtp_creds.mail_server[0]}.')

        mailer = smtp_config.sendMail(mail_server=smtp_creds.mail_server[0],
                            port = smtp_creds.port[0],
                            username = smtp_creds.username[0],
                            password = smtp_creds.password[0],
                            from_address = smtp_creds.from_address[0])
        # mailer.send_mail(subject="online", content="online", to_address='', logfile=log)

    # if os.path.exists ("ldap_creds"):
        # ldap_creds = pd.read_csv("ldap_creds", dtype=str) # expecting CSV format
        # LDAP_ENABLED=True # we should do something with this later on
        # log.info(f'LIBREFORMS - found an LDAP credentials file using {ldap_creds.ldap_server[0]}.')



    # else: 
    #     log.warning('LIBREFORMS - no SMTP credentials file found, outgoing mail will not be enabled.')


    if os.path.exists ("secret_key"):
        with open("secret_key", "r+") as f:
            app.config["SECRET_KEY"] = f.read().strip()
        log.info('LIBREFORMS - found a secret key file.')


    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # define a home route
    @app.route('/')
    def home():
        return render_template('app/index.html', 
            homepage=True,
            site_name=display['site_name'],
            type="home",
            name=display['site_name'],
            display_warning_banner=True,
            display=display,
            user=current_user if current_user.is_authenticated else None,
        )


        # define a home route
    @app.route('/privacy')
    def privacy():
        return render_template('app/privacy.html', 
            site_name=display['site_name'],
            type="home",
            name='privacy',
            display=display,
            user=current_user if current_user.is_authenticated else None,
        )


    from .models import User

    # initialize the database
    db.init_app(app=app)

    # create the database if it doesn't exist
    if not os.path.exists(os.path.join('instance','app.sqlite')):
        db.create_all(app=app)

        # create default user if doesn't exist
        # solution from https://stackoverflow.com/a/39288652
        with app.app_context():
            if db.session.query(User).filter_by(username='libreforms').count() < 1:
                initial_user = User(id=1,
                                    username='libreforms', 
                                    password='pbkdf2:sha256:260000$nQVWxd59E8lmkruy$13d8c4d408185ccc3549d3629be9cd57267a7d660abef389b3be70850e1bbfbf',
                                    created_date='2022-06-01 00:00:00',)
                db.session.add(initial_user)
                db.session.commit()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))  

    from . import auth
    app.register_blueprint(auth.bp)

    from . import forms
    app.register_blueprint(forms.bp)

    from . import dashboards
    app.register_blueprint(dashboards.bp)

    from . import tables
    app.register_blueprint(tables.bp)

    from . import api
    app.register_blueprint(api.bp)

    from . import external
    app.register_blueprint(external.bp)

    return app



