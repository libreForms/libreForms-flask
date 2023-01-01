""" 
__init__.py: the init script for the libreForms Flask app

This application employs the Flask factory pattern, which moves 
the Flask app object into a function called create_app, which is
itself called in wsgi.py. In theory, this makes the application
easier to test with various different instances & settings, see
https://flask.palletsprojects.com/en/2.0.x/patterns/appfactories/.


In addition, the application relies heavily on SQL Alchemy (see
https://flask-sqlalchemy.palletsprojects.com/en/3.0.x/) and Celery 
(see https://flask.palletsprojects.com/en/2.1.x/patterns/celery/)
to make things work. It also leverages Flask-Login because this 
makes managing basic auth significantly more straightforward.


"""

__name__ = "app"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

##########################
# Import Dependencies
##########################

# basic dependencies
import os, re
import pandas as pd

# Flask-specific dependencies
from flask import Flask, render_template, current_app, jsonify, request, abort
from flask_login import LoginManager, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from celery import Celery
from markupsafe import Markup


# application-specific dependencies
from app import mongo, log_functions
from app.smtp import Mailer
from app.config import config
from app.models import db, User
from app.certification import generate_symmetric_key


##########################
# Common Sense Checks - ensure any relevant assumptions are met before the app initializes
##########################

if config['libreforms_user_email'] == None:
  raise Exception("Please specify an admin email for the libreforms user in the 'libreforms_user_email' app config.")

if not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', config['libreforms_user_email']):
    raise Exception("The email you specified in the'libreforms_user_email' app config is invalid.")

# system breaks initially if configs are set that require SMTP, but SMTP isn't enabled.
if not config['smtp_enabled'] and (config['enable_email_verification'] or \
            config['send_reports'] or config['allow_password_resets'] or \
            config['allow_anonymous_form_submissions']):

  raise Exception("Please enable SMTP if you'd like to enable email verification, allow password resets, send \
                        reports, or allow anonymous form submissions.")



##########################
# Objects and Configs- ensure that objects are created / configured before initializing app
##########################

# if application log path doesn't exist, make it; nb. this (and
# much of other logic in this section of code) is replicated in 
# in etc/gunicorn.conf.py to ensure it runs pre-fork in a 
# production setup.
if not os.path.exists ("log/"):
    os.mkdir('log/')
else:
    # if the log path exists, let's clean up old log handlers
    log_functions.cleanup_stray_log_handlers(os.getpid())

# we instantiate a log object that we'll use across the app
log = log_functions.set_logger('log/libreforms.log',__name__)
log.info('LIBREFORMS - started libreforms web application.')


# here we create the celery object
celery = Celery(__name__, backend=config['celery_backend'], broker=config['celery_broker'])
log.info(f'LIBREFORMS - initialized celery object.')

# initialize mongodb database
mongodb = mongo.MongoDB(user=config['mongodb_user'], 
                        host=config['mongodb_host'], 
                        port=config['mongodb_port'], 
                        dbpw=config['mongodb_pw'])
log.info(f'LIBREFORMS - connected to MongoDB.')

# create hCaptcha object if enabled
if config['enable_hcaptcha']:
    from flask_hcaptcha import hCaptcha
    hcaptcha = hCaptcha()
    log.info(f'LIBREFORMS - initialized hCaptcha object.')


# here we add code (that probably NEEDS REVIEW) to verify that
# it is possible to connect to a different / external database, see
    # https://github.com/signebedi/libreForms/issues/68
    # https://github.com/signebedi/libreForms/issues/69
# if this truly implemented, we should probably also add it to
# etc/gunicorn.conf.py to handle pre-fork 
if config['custom_sql_db'] == True:
    if os.path.exists ("user_db_creds"):
        user_db_creds = pd.read_csv("user_db_creds", dtype=str) # expecting the CSV format: db_driver,db_user, db_pw, db_host, db_port
        db_driver = user_db_creds.db_driver[0] # eg. postgres, mysql
        db_user = user_db_creds.db_user[0]
        db_pw = user_db_creds.db_pw[0] # in the future, support other way to store secrets
        db_host = user_db_creds.db_host[0]
        db_port = user_db_creds.db_port[0]
        log.info(f'LIBREFORMS - loaded custom SQL database settings.')

    else:
        config['custom_sql_db'] = False
        log.warning('LIBREFORMS - no user db credentials file found, custom sql database will not be enabled.')


# here we start up the SMTP `mailer` object that we'll propagate like the 
# log object above and use to send mail
if config['smtp_enabled']: # we should do something with this later on
    if os.path.exists (os.path.join(config['config_folder'], 'smtp_creds')):
        smtp_creds = pd.read_csv(os.path.join(config['config_folder'], 'smtp_creds'), dtype=str) # expecting the CSV format: smtp_server,port,username,password,from_address
        log.info(f'LIBREFORMS - found an SMTP credentials file using {smtp_creds.mail_server[0]}.')

        mailer = Mailer(mail_server=smtp_creds.mail_server[0],
                            port = smtp_creds.port[0],
                            username = smtp_creds.username[0],
                            password = smtp_creds.password[0],
                            from_address = smtp_creds.from_address[0])
        mailer.send_mail(subject=f"{config['site_name']} online", content=f"{config['site_name']} is now online at {config['domain']}.", to_address=config['libreforms_user_email'], logfile=log)
    else: 
        log.error('LIBREFORMS - no SMTP credentials file found, outgoing mail will not be enabled.')
        # I think we need to stop the system here if we are trying to enable SMTP but no creds have been provided
        raise Exception("SMTP is enabled but no SMTP credentials have been provided. Please see the documentation at https://github.com/signebedi/libreForms#mail for more details.")
else:
    # we want the mailer object to exist still but by passing `enabled` to False we 
    # prevent mail from being sent
    mailer=Mailer(enabled=False)
    log.info(f'LIBREFORMS - outgoing mail is not enabled.')


# if os.path.exists ("ldap_creds"):
    # ldap_creds = pd.read_csv("ldap_creds", dtype=str) # expecting CSV format
    # if config['ldap_enabled'] == True: # we should do something with this later on
        # log.info(f'LIBREFORMS - found an LDAP credentials file using {ldap_creds.ldap_server[0]}.')

# turn off pandas warnings to avoid a rather silly one being dropped in the 
# terminal, see https://stackoverflow.com/a/20627316/13301284. 
pd.options.mode.chained_assignment = None



##########################
# Flask App - define a Flask app using the create_app() / factory method with blueprints
##########################


# here we create the Flask app using the Factory pattern,
# see https://flask.palletsprojects.com/en/2.2.x/patterns/appfactories/
def create_app(test_config=None):
 
    # create the app object
    app = Flask(__name__, instance_relative_config=True)

    # import any context-bound libraries
    from app.action_needed import standardard_total_notifications
    from app.views.reports import reportManager

    # add some app configurations
    app.config.from_mapping(
        SECRET_KEY=config['secret_key'],
        # getting started on allowing other SQL databases than SQLite, but defaulting to that. 
        SQLALCHEMY_DATABASE_URI = f'{db_driver}://{db_host}:{db_pw}@{db_host}:{str(db_port)}/' if config['custom_sql_db'] == True else f'sqlite:///{os.path.join(app.instance_path, "app.sqlite")}',
        # SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(app.instance_path, "app.sqlite")}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER = config['upload_folder'],
        MAX_CONTENT_LENGTH = config['max_upload_size'],
        HCAPTCHA_ENABLED = config['enable_hcaptcha'],
        HCAPTCHA_SITE_KEY = config['hcaptcha_site_key'] if config['hcaptcha_site_key'] else None,
        HCAPTCHA_SECRET_KEY = config['hcaptcha_secret_key'] if config['hcaptcha_secret_key'] else None,
        
        CELERY_CONFIG={
            'broker_url':config['celery_broker'],
            'result_backend':config['celery_backend'],
            'task_serializer':'json',
            'accept_content':['json'],
            'result_serializer':'json',
            'enable_utc':True,
        },
        # this might be a little hackish, but we define a callable in app 
        # config so we can easily figure out how many notifications a given
        # user has at any given moment. I welcome feedback if there is a 
        # better way to call a context-bound function from the current_app. 
        NOTIFICATIONS=standardard_total_notifications, 
    )

    # here we configure the application to inherit the origin IP address of clients 
    # from the reverse proxy, see https://stackoverflow.com/a/23504684/13301284
    # and further dissuion here https://github.com/signebedi/libreForms/issues/175.
    # This should enable us to access the client IP address using request.remote_addr.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

    # here we update the celery object (which we originally 
    # created outside the app context, see https://github.com/signebedi/libreForms/issues/73
    # and https://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern
    # for more explanation on this approach, which was driven by our use of the Flask factory 
    # pattern, which uses create_app) with the configs passed in the app config under `CELERY_CONFIG`. 
    celery.conf.update(app.config)

    # if test_config is None:
    #     # load the instance config, if it exists, when not testing
    #     app.config.from_pyfile('config.py', silent=True)
    # else:
    #     # load the test config if passed in
    #     app.config.from_mapping(test_config)

    # create instance, config, and uploads folder to store instance-specific, 
    # configuration, and uploaded files.
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    try:
        os.makedirs(config['upload_folder'])
    except OSError:
        pass
    try:
        os.makedirs(config['config_folder'])
    except OSError:
        pass

    # initialize hCaptcha object defined outside the app context, 
    # but only if hCaptcha is enabled in the app config
    if config['enable_hcaptcha']:
        hcaptcha.init_app(app)


    # This application allows adminstrators to define fields beyond the default fields set in app.models.
    # In order to do this, administrators should define these additional fields in the app config using the
    # `user_registration_fields` key; see https://github.com/signebedi/libreForms/issues/61 for more details.
    # here we append any additional fields described in the `user_registration_fields` app config
    for key, value in config['user_registration_fields'].items():

        # might eventually be worth adding support for unique fields...
        if value['type'] == str:
            setattr(User, key, db.Column(db.String(1000)))
            # print(key,value)

        elif value['type'] == int:
            setattr(User, key, db.Column(db.Integer))
            # print(key,value)


    # initialize the database object defined outside the app context above
    db.init_app(app=app)


    # create the database if it doesn't exist; this, like many other
    # steps in this script, are replicated in etc/gunicorn.conf.py
    # because they need to occur before the application forks into multiple
    # processes.
    if not os.path.exists(os.path.join('instance','app.sqlite')):
        with app.app_context():
            db.create_all()

        # create default user if doesn't exist
        # solution from https://stackoverflow.com/a/39288652
        with app.app_context():
            if db.session.query(User).filter_by(username='libreforms').count() < 1:
                initial_user = User(id=1,
                                    username='libreforms', 
                                    active=1,
                                    theme='dark' if config['dark_mode'] else 'light',
                                    group=config['admin_group'],
                                    certificate=generate_symmetric_key(),
                                    email=config['libreforms_user_email'] if config['libreforms_user_email'] and re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', config['libreforms_user_email']) else None,
                                    password='pbkdf2:sha256:260000$nQVWxd59E8lmkruy$13d8c4d408185ccc3549d3629be9cd57267a7d660abef389b3be70850e1bbfbf',
                                    created_date='2022-06-01 00:00:00',)
                db.session.add(initial_user)
                db.session.commit()


    # here we employ some Flask-Login boilerplate to make 
    # user auth and session management a little easier. 
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))  



    ##########################
    # Celery Tasks - define and implement context-bound celery tasks
    ##########################

    # here we define a tasks to send emails asynchonously - it's just a 
    # celery wrapper for the function library defined in app.smtp.
    @celery.task()
    def send_mail_asynch(subject, content, to_address, cc_address_list=None, logfile=log):
        mailer.send_mail(   subject=subject, content=content, to_address=to_address, 
                            cc_address_list=cc_address_list, logfile=log)
    
    # maybe a little hackish, but if we set `send_mail_asynchronously`, which defaults to True,
    # then we configure the application to send mail asynchronously using the current_app;
    # otherwise, we fall back to synchronous mail
    app.config['MAILER'] = send_mail_asynch if config['send_mail_asynchronously'] else mailer.send_mail

    # here we define an asynchronous wrapper function for the app.mongo.write_documents_to_collection 
    # method, which we'll implement when the `write_documents_asynchronously` config is set, see
    # https://github.com/libreForms/libreForms-flask/issues/180.
    @celery.task(bind=True)
    def write_document_to_collection_async(self, data, collection_name, reporter=None, modification=False, 
                                            digital_signature=None, approver=None, approval=None, approver_comment=None, ip_address=None):

        # self.delay()

        self.update_state(state='PENDING')
        # print('PENDING')

        document_id = mongodb.write_document_to_collection(data, collection_name, reporter=reporter, modification=modification, 
                                            digital_signature=digital_signature, approver=approver, approval=approval, 
                                            approver_comment=approver_comment, ip_address=ip_address)

        self.update_state(state='COMPLETE')
        # print('COMPLETE')

        return document_id

    # maybe a little hackish, but if we set `write_documents_asynchronously`, which defaults to True,
    # then we configure the application to write document to MongoDB asynchronously using the current_app;
    # otherwise, we fall back to synchronous submission method
    app.config['MONGODB_WRITER'] = write_document_to_collection_async if config['write_documents_asynchronously'] else mongodb.write_document_to_collection


    # create a report manager object to send scheduled email reports, see 
    # app.views.reports and https://github.com/signebedi/libreForms/issues/73
    reports = reportManager(send_reports=config['send_reports'])

    @celery.task()
    def send_reports(reports, *args):
        # select all reports whose conditions are met under reportManager.trigger, 
        # and pass these to the execution reportManager.handler
        pass

    @celery.on_after_configure.connect
    def setup_periodic_tasks(sender, **kwargs):

        # periodically calls send_reports 
        sender.add_periodic_task(3600.0, send_reports.s(reports), name='send reports periodically')


    # create a task status endpoint
    @app.route('/status/<task_id>', methods=['GET'])
    def taskstatus(task_id=None):
        try:
            task = celery.AsyncResult(task_id)
            response = {
                'state': task.state,
            }
            return jsonify(response)
        except:
            return abort(404)


    ##########################
    # Routes and Blueprints - define default URL routes and import others from blueprints
    ##########################

    # define a home route
    @app.route('/')
    def home():
        return render_template('app/index.html', 
            homepage=True,
            site_name=config['site_name'],
            type="home",
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            name=config['site_name'],
            config=config,
            user=current_user if current_user.is_authenticated else None,
        )

    # @app.route("/ip", methods=["GET"])
    # def get_my_ip():
    #     return jsonify({'ip': request.remote_addr}), 200

    # define a route to show the application's privacy policy 
    @app.route('/privacy')
    def privacy():
        return render_template('app/privacy.html', 
            site_name=config['site_name'],
            type="home",
            name='privacy',
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            config=config,
            user=current_user if current_user.is_authenticated else None,
        )


    # define a route to show the application's privacy policy 
    # @app.route('/loading/<form_name>/<document_id>')
    # def loading(form_name, document_id):

    #     if mongodb.is_document_in_collection(form_name, document_id):

    #         return render_template('app/loading.html', 
    #             site_name=config['site_name'],
    #             type="home",
    #             name='loading',
    #             notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
    #             config=config,
    #             user=current_user if current_user.is_authenticated else None,
    #             msg=f'Submitting form data for {form_name} form, document ID {document_id}'
    #         )

    #     else:
    #         return abort(404)

    # import the `auth` blueprint for user / session management
    from .views import auth
    app.register_blueprint(auth.bp)

    # import the `forms` blueprint for form submission
    from .views import forms
    app.register_blueprint(forms.bp)

    # import the `submissionss` blueprint for post-submission form view / management
    from .views import submissions
    app.register_blueprint(submissions.bp)

    # import the `dashboard` blueprint for data visualization
    from .views import dashboards
    app.register_blueprint(dashboards.bp)

    # import the `table` blueprint for tabular views of form data
    from .views import tables
    app.register_blueprint(tables.bp)

    # import the `api` blueprint for RESTful API support
    if config['enable_rest_api']:
        from .views import api
        app.register_blueprint(api.bp)

    # if administrators have enabled anonymous / external form submission, then we
    # import the `external` blueprint to create the external access endpoint
    if config['allow_anonymous_form_submissions']:
        from .views import external
        app.register_blueprint(external.bp)

    # if administrators have enabled health checks, then we import the `health`
    # blueprint, see https://github.com/signebedi/libreForms/issues/171.
    if config['enable_health_checks']:
        from .views import health_check
        app.register_blueprint(health_check.bp)


    # import the `reports` blueprint for 
    from .views import reports
    app.register_blueprint(reports.bp)

    # return the app object with the above configurations
    return app



