""" 
__init__.py: the parent script for the web application



"""

__name__ = "app"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.0.1"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


import os, re, secrets
from flask import Flask, render_template, session
import app.log_functions
# from flask_admin import Admin
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from libreforms import __version__
from app.display import display
import pandas as pd
from app.csv_files import init_tmp_fs, tempfile_init_tmp_fs
from app import smtp, mongo
from celery import Celery
from app.models import db
from app.certification import generate_symmetric_key


# def make_celery():
#     celery = Celery(__name__, broker='redis://localhost:6379/0')

#     class ContextTask(celery.Task):
#         def __call__(self, *args, **kwargs):
#             with app.app_context():
#                 return self.run(*args, **kwargs)

#     celery.Task = ContextTask
#     return celery

# celery = make_celery()
# celery = Celery(__name__, broker='redis://localhost:6379/0')

celery = Celery(__name__, broker='redis://localhost:6379/0')

# defining a decorator that applies a parent decorator 
# based on the truth-value of a condition
def conditional_decorator(dec, condition):
    def decorator(func):
        if not condition:
            # Return the function unchanged, not decorated.
            return func
        return dec(func)
    return decorator

if display['libreforms_user_email'] == None:
  raise Exception("Please specify an admin email for the libreforms user in the 'libreforms_user_email' app config.")

if not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', display['libreforms_user_email']):
    raise Exception("The email you specified in the'libreforms_user_email' app config is invalid.")

# system breaks initially if configs are set that require SMTP, but SMTP isn't enabled.
if not display['smtp_enabled'] and (display['enable_email_verification'] or \
            display['send_reports'] or display['allow_password_resets'] or \
            display['allow_anonymous_form_submissions']):

  raise Exception("Please enable SMTP if you'd like to enable email verification, allow password resets, send \
                        reports, or allow anonymous form submissions.")


# initialize mongodb database
mongodb = mongo.MongoDB(
                        user=display['mongodb_user'], 
                        host=display['mongodb_host'], 
                        port=display['mongodb_port'], 
                        dbpw=display['mongodb_pw'], 
                    )

# create hCaptcha object if enabled
if display['enable_hcaptcha']:
    from flask_hcaptcha import hCaptcha
    hcaptcha = hCaptcha()

# we instantiate a tempfile path for the current worker instance, 
# which we'll use to store tempfiles, uploads, etc.
tempfile_path = tempfile_init_tmp_fs()

# if application log path doesn't exist, make it
if not os.path.exists ("log/"):
    os.mkdir('log/')
else:
    # if the log path exists, let's clean up old log handlers
    app.log_functions.cleanup_stray_log_handlers(os.getpid())

# we instantiate a log object that 
# we'll propagate across the app
log = app.log_functions.set_logger('log/libreforms.log',__name__)
log.info('LIBREFORMS - started libreforms web application.')

# turn off pandas warnings to avoid a rather silly one being dropped in the 
# terminal, see https://stackoverflow.com/a/20627316/13301284. 
pd.options.mode.chained_assignment = None

# here we add code (that probably NEEDS REVIEW) to verify that
# it is possible to connect to a different / external database, see
    # https://github.com/signebedi/libreForms/issues/68
    # https://github.com/signebedi/libreForms/issues/69
# if this truly implemented, we should probably also add it to
# gunicorn/gunicorn.conf.py to handle pre-fork 

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


# here we start up the SMTP `mailer` object that we'll propagate like the 
# log object above and use to send mail
if display['smtp_enabled']: # we should do something with this later on
    if os.path.exists ("smtp_creds"):
        smtp_creds = pd.read_csv("smtp_creds", dtype=str) # expecting the CSV format: smtp_server,port,username,password,from_address
        log.info(f'LIBREFORMS - found an SMTP credentials file using {smtp_creds.mail_server[0]}.')

        mailer = smtp.sendMail(mail_server=smtp_creds.mail_server[0],
                            port = smtp_creds.port[0],
                            username = smtp_creds.username[0],
                            password = smtp_creds.password[0],
                            from_address = smtp_creds.from_address[0])
        mailer.send_mail(subject=f"{display['site_name']} online", content=f"{display['site_name']} is now online at {display['domain']}.", to_address=display['libreforms_user_email'], logfile=log)
    else: 
        log.error('LIBREFORMS - no SMTP credentials file found, outgoing mail will not be enabled.')
        # I think we need to stop the system here if we are trying to enable SMTP but no creds have been provided
        raise Exception("SMTP is enabled but now SMTP credentials have been provided. Please see the \
            documentation at https://github.com/signebedi/libreForms#mail for more details.")
else:
    # we want the mailer object to exist still but by passing `enabled` to False we 
    # prevent mail from being sent
    mailer=smtp.sendMail(enabled=False)

# if os.path.exists ("ldap_creds"):
    # ldap_creds = pd.read_csv("ldap_creds", dtype=str) # expecting CSV format
    # if display['ldap_enabled'] == True: # we should do something with this later on
        # log.info(f'LIBREFORMS - found an LDAP credentials file using {ldap_creds.ldap_server[0]}.')


# here we create the Flask app using the Factory pattern,
# see https://flask.palletsprojects.com/en/2.2.x/patterns/appfactories/
def create_app(test_config=None):
 
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # add some app configurations
    app.config.from_mapping(
        SECRET_KEY=display['secret_key'],
        # getting started on allowing other SQL databases than SQLite, but defaulting to that. 
        SQLALCHEMY_DATABASE_URI = f'{db_driver}://{db_host}:{db_pw}@{db_host}:{str(db_port)}/' if display['custom_sql_db'] == True else f'sqlite:///{os.path.join(app.instance_path, "app.sqlite")}',
        # SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(app.instance_path, "app.sqlite")}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # FLASK_ADMIN_SWATCH='darkly',
        HCAPTCHA_ENABLED = display['enable_hcaptcha'],
        HCAPTCHA_SITE_KEY = display['hcaptcha_site_key'] if display['hcaptcha_site_key'] else None,
        HCAPTCHA_SECRET_KEY = display['hcaptcha_secret_key'] if display['hcaptcha_secret_key'] else None,
        CELERY_CONFIG={
            'CELERY_BROKER_URL':'redis://localhost:6379/0',
            'CELERY_RESULT_BACKEND':'redis://localhost:6379/0'
        },
    )


    celery.conf.update(app.config)

    # admin = Admin(app, name='libreForms', template_mode='bootstrap4')
    # Add administrative views here

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

    # initialize hCaptcha if enabled
    if display['enable_hcaptcha']:
        hcaptcha.init_app(app)

    from .models import User

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

    # initialize the database
    db.init_app(app=app)

    
    # #  THIS CAN PROBABLY BE DEPRECATED BECAUSE WE ARE ABLE TO CREATE THE 
    # #  TABLE WITH THE CORRECT COLUMNS BY RUNNING THE CODE ABOVE...
    # # borrowed from https://stackoverflow.com/a/17243132
    # if display['user_registration_fields']:

    #     with app.app_context():

    #         # we create a method that we'll run to modify the user table
    #         # to include any additional fields 
    #         def add_column(table_name, column, engine=db.engine):
    #             column_name = column.compile(dialect=engine.dialect)
    #             column_type = column.type.compile(engine.dialect)
    #             engine.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table_name, column_name, column_type))


    #         # borrow from https://www.geeksforgeeks.org/python-sqlalchemy-get-column-names-dynamically/
    #         with db.engine.connect() as conn:
    #             result = conn.execute(f"SELECT * FROM {User.__tablename__}")
    #             cols = []
    #             for elem in result.cursor.description:
    #                 cols.append(elem[0])

    #         engine=db.engine
    #         for key, value in display['user_registration_fields'].items():
    #                 if key not in cols:
    #                     if value['type'] == str:
    #                         column = db.Column(key, db.String(1000))
    #                         add_column(User.__tablename__, column)

    #                     elif value['type'] == int:
    #                         column = db.Column(key, db.Column(db.Integer), primary_key=True)
    #                         add_column(User.__tablename__, column)


    # create the database if it doesn't exist
    if not os.path.exists(os.path.join('instance','app.sqlite')):
        db.create_all(app=app)

        # create default user if doesn't exist
        # solution from https://stackoverflow.com/a/39288652
        with app.app_context():
            if db.session.query(User).filter_by(username='libreforms').count() < 1:
                initial_user = User(id=1,
                                    username='libreforms', 
                                    active=1,
                                    theme='dark' if display['dark_mode'] else 'light',
                                    group='admin',
                                    certificate=generate_symmetric_key(),
                                    email=display['libreforms_user_email'] if display['libreforms_user_email'] and re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', display['libreforms_user_email']) else None,
                                    password='pbkdf2:sha256:260000$nQVWxd59E8lmkruy$13d8c4d408185ccc3549d3629be9cd57267a7d660abef389b3be70850e1bbfbf',
                                    created_date='2022-06-01 00:00:00',)
                db.session.add(initial_user)
                db.session.commit()

    # this is just some debug code
    # from app import signing
    # with app.app_context():
        # from app import reports       
        # signing.write_key_to_database(scope=None, expiration=0, active=1, email=None)
        # print(signing.flush_key_db())
        # signing.expire_key(key="iqmwd44IKhsoE0HWjKGZohaN")
        # print(pd.read_sql_table("signing", con=db.engine.connect()))

        # signing_df = pd.read_sql_table("signing", con=db.engine.connect())
        # print(signing_df)
        # print(signing_df.loc[ signing_df.active == 1 ].expiration.min())
 
        # next_expiration = datetime.datetime.fromtimestamp (
        #     signing_df.loc[ signing_df.active == 1 ].expiration.min()
        # # if there are no signing keys, then we check every minute
        # ) if len(signing_df.index > 0) else datetime.datetime.now()+datetime.timedelta(minutes=1)
        # print(next_expiration)

        # time.sleep((next_expiration - datetime.datetime.now()).total_seconds())

        # import asyncio
        # asyncio.run(signing.sleep_until_next_expiration())

        # import datetime, time, threading
        # import app.signing as signing
        # # signing.sleep_until_next_expiration()

        # x = threading.Thread(target=signing.sleep_until_next_expiration)
        # x.start()

        # from app.signing import flushTimer
            
        # i = threading.Thread(target=sleep_until_next_expiration(
        #     signing_df)
        #     ).start()

        # t = flushTimer(signing_df)
        # reporter = reports.reportHandler()
        # reporter.set_cron_jobs()


    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))  


    # here we import the logic needed to determine notification
    from app.action_needed import aggregate_notification_count
    from app.submissions import aggregate_approval_count


    # define a home route
    @app.route('/')
    def home():
        return render_template('app/index.html', 
            homepage=True,
            site_name=display['site_name'],
            type="home",
            notifications=aggregate_notification_count(
                len(aggregate_approval_count(select_on=getattr(current_user,display['visible_signature_field'])).index)
            ),
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


    if display ['allow_anonymous_form_submissions']:
        from . import external
        app.register_blueprint(external.bp)

    from . import reports
    app.register_blueprint(reports.bp)

    from . import submissions
    app.register_blueprint(submissions.bp)

    return app



