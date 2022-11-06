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
from app import smtp

db = SQLAlchemy()


tempfile_path = tempfile_init_tmp_fs()

# if application log path doesn't exist, make it
if not os.path.exists ("log/"):
    os.mkdir('log/')

# we instantiate a log object that 
# we'll propagate across the app

log = app.log_functions.set_logger('log/libreforms.log',__name__)
log.info('LIBREFORMS - started libreforms web application.')


if display['custom_sql_db'] == True:
    if os.path.exists ("user_db_creds"):
        user_db_creds = pd.read_csv("user_db_creds", dtype=str) # expecting the CSV format: db_driver,db_user, db_pw, db_host, db_port
        db_driver = user_db_creds.db_driver[0] # eg. postgres, mysql
        db_user = user_db_creds.db_user[0]
        db_pw = user_db_creds.db_pw[0] # in the future, support other way to store secrets
        db_host = user_db_creds.db_host[0]
        db_port = user_db_creds.db_port[0]

    else:
        display['custom_sql_db'] = False
        log.warning('LIBREFORMS - no user db credentials file found, custom sql database will not be enabled.')


if os.path.exists ("smtp_creds"):
    smtp_creds = pd.read_csv("smtp_creds", dtype=str) # expecting the CSV format: smtp_server,port,username,password,from_address
    if display['smtp_enabled'] == True: # we should do something with this later on
        log.info(f'LIBREFORMS - found an SMTP credentials file using {smtp_creds.mail_server[0]}.')

        mailer = smtp.sendMail(mail_server=smtp_creds.mail_server[0],
                            port = smtp_creds.port[0],
                            username = smtp_creds.username[0],
                            password = smtp_creds.password[0],
                            from_address = smtp_creds.from_address[0])
        # mailer.send_mail(subject="online", content="online", to_address='', logfile=log)
else: 
    display['smtp_enabled'] = False
    log.warning('LIBREFORMS - no SMTP credentials file found, outgoing mail will not be enabled.')

# if os.path.exists ("ldap_creds"):
    # ldap_creds = pd.read_csv("ldap_creds", dtype=str) # expecting CSV format
    # if display['ldap_enabled'] == True: # we should do something with this later on
        # log.info(f'LIBREFORMS - found an LDAP credentials file using {ldap_creds.ldap_server[0]}.')


# # non-destructively initialize a tmp file system for the app 
# init_tmp_fs(delete_first=False)

def create_app(test_config=None):
 
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        # getting started on allowing other SQL databases than SQLite, but defaulting to that. 
        SQLALCHEMY_DATABASE_URI = f'{db_driver}://{db_host}:{db_pw}@{db_host}:{str(db_port)}/' if display['custom_sql_db'] == True else f'sqlite:///{os.path.join(app.instance_path, "app.sqlite")}',
        # SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(app.instance_path, "app.sqlite")}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # FLASK_ADMIN_SWATCH='darkly',
    )

    # admin = Admin(app, name='libreForms', template_mode='bootstrap4')
    # Add administrative views here

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


    # here we append any additional fields described in the display.user_registration_fields variable
    if display['user_registration_fields']:
        for key, value in display['user_registration_fields'].items():

            # might eventually be worth adding support for unique fields...
            if value['type'] == str:
                setattr(User, key, db.Column(db.String(1000)))
                # print(key,value)
            elif value['type'] == int:
                setattr(User, key, db.Column(db.Integer))
                # print(key,value)


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
    
    # borrowed from https://stackoverflow.com/a/17243132
    if display['user_registration_fields']:

        with app.app_context():

            def add_column(table_name, column, engine=db.engine):
                column_name = column.compile(dialect=engine.dialect)
                column_type = column.type.compile(engine.dialect)
                engine.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table_name, column_name, column_type))


            # borrow from https://www.geeksforgeeks.org/python-sqlalchemy-get-column-names-dynamically/
            with db.engine.connect() as conn:
                result = conn.execute(f"SELECT * FROM user")
                cols = []
                for elem in result.cursor.description:
                    cols.append(elem[0])

            engine=db.engine
            for key, value in display['user_registration_fields'].items():
                    if key not in cols:
                        if value['type'] == str:
                            column = db.Column(key, db.String(1000))
                            add_column("user", column)

                        elif value['type'] == int:
                            column = db.Column(key, db.Column(db.Integer), primary_key=True)
                            add_column("user", column)

    from app import signing
    with app.app_context():
        signing.write_key_to_database(scope=None, expiration=1, active=1, email=None)


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



