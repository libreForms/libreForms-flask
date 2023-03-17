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
__version__ = "1.8.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

##########################
# Import Dependencies
##########################

# basic dependencies
import os, re, json
import pandas as pd
import datetime

# Flask-specific dependencies
from flask import Flask, render_template, current_app, jsonify, request, \
                    abort, Response, send_from_directory, url_for
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
from app.scripts import prettify_time_diff


##########################
# Common Sense Checks - ensure any relevant assumptions are met before the app initializes
##########################

if config['default_user_email'] == None:
  raise Exception("Please specify an admin email for the libreforms user in the 'default_user_email' app config.")

if not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', config['default_user_email']):
    raise Exception("The email you specified in the'default_user_email' app config is invalid.")

# system breaks initially if configs are set that require SMTP, but SMTP isn't enabled.
if not config['smtp_enabled'] and (config['enable_email_verification'] or \
            config['enable_reports'] or config['allow_password_resets'] or \
            config['allow_anonymous_form_submissions']):

  raise Exception("Please enable SMTP if you'd like to enable email verification, allow password resets, send reports, or allow anonymous form submissions.")



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
log = config['logger']('log/libreforms.log',__name__)
log.info('LIBREFORMS - started libreforms web application.')


# here we create the celery object
celery = Celery(__name__, backend=config['celery_backend'], broker=config['celery_broker'])
log.info(f'LIBREFORMS - initialized celery object.')

# initialize mongodb database
mongodb = mongo.mongodb
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
# log object above and use to send mail. We prioritize looking for a file
# called smtp_crds in the config folder but, if we can't find it, we
# check for defaults
if config['smtp_enabled']: # we should do something with this later on

    # The method of using an SMTP credentials file is tentatively marked for 
    # deprecation in a future version of this application, see discussion at
    # https://github.com/libreForms/libreForms-flask/issues/217. 
    if os.path.exists (os.path.join(config['config_folder'], 'smtp_creds')):
        log.info(f"LIBREFORMS - found an SMTP credentials file at {os.path.join(config['config_folder'], 'smtp_creds')}.")
        smtp_creds = pd.read_csv(os.path.join(config['config_folder'], 'smtp_creds'), dtype=str) # expecting the CSV format: smtp_server,port,username,password,from_address

        # We assign the newly found values to the corresponding config, see discussion at
        # https://github.com/libreForms/libreForms-flask/issues/216.
        config['smtp_mail_server'] = smtp_creds.mail_server[0]
        config['smtp_port'] = smtp_creds.port[0]
        config['smtp_username'] = smtp_creds.username[0]
        config['smtp_password'] = smtp_creds.password[0]
        config['smtp_from_address'] = smtp_creds.from_address[0]

    try:

        log.info(f"LIBREFORMS - trying to connect to the following SMTP server {config['smtp_mail_server']}.")

        # now we assert that these values are not None, which is their default value.
        assert config['smtp_mail_server'] is not None
        assert config['smtp_port'] is not None
        assert config['smtp_username'] is not None
        assert config['smtp_password'] is not None
        assert config['smtp_from_address'] is not None

        # and then we establish the connection and send an email synchronously
        mailer = Mailer(mail_server=config['smtp_mail_server'],
                            port = config['smtp_port'],
                            username = config['smtp_username'],
                            password = config['smtp_password'],
                            from_address = config['smtp_from_address'])

        mailer.send_mail(subject=f"{config['site_name']} online", content=f"{config['site_name']} is now online at {config['domain']}.", to_address=config['default_user_email'], logfile=log)
    
    except Exception as e:

        log.error(f'LIBREFORMS - unable to connect to SMTP server, outgoing mail will not be enabled. {e}')
        # I think we need to stop the system here if we are trying to enable SMTP but no creds have been provided
        raise Exception(f"SMTP is enabled but could not connect. This may be because no SMTP credentials have been provided. Please see the documentation at https://libreforms.readthedocs.io/en/latest/#mail for more details. {e}")
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
def create_app(test_config=None, celery_app=False, db_init_only=False):
 
    # create the app object
    app = Flask(__name__, instance_relative_config=True)

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
        REPORT_SEND_RATE=config['report_send_rate'],
        USE_ELASTICSEARCH_AS_WRAPPER = config['use_elasticsearch_as_wrapper'],
        EXCLUDE_FORMS_FROM_SEARCH=config['exclude_forms_from_search'] if config['exclude_forms_from_search'] else [],
        ELASTICSEARCH_INDEX_REFRESH_RATE=config['elasticsearch_index_refresh_rate'],
        CELERY_CONFIG={
            'broker_url':config['celery_broker'],
            'result_backend':config['celery_backend'],
            'task_serializer':'json',
            'accept_content':['json'],
            'result_serializer':'json',
            'enable_utc':True,
        },
    )

    # here we configure the application to inherit the origin IP address of clients 
    # from the reverse proxy, see https://stackoverflow.com/a/23504684/13301284
    # and further dissuion here https://github.com/signebedi/libreForms/issues/175.
    # This should enable us to access the client IP address using request.remote_addr.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

    #  create any files / directories that haven't been created.
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

    # here we create files that will be used to trigger touch reload 
    # see https://github.com/libreForms/libreForms-flask/issues/233.
    with open ('libreforms.env', 'a'): pass
    with open ("log/restart.log", 'a'): pass

    ##########################
    # DB initialization -- initialize a context-bound db instance
    ##########################

    # initialize the database object defined outside the app context above
    db.init_app(app=app)


    # This application allows adminstrators to define fields beyond the default fields set in app.models.
    # In order to do this, administrators should define these additional fields in the app config using the
    # `user_registration_fields` key; see https://github.com/signebedi/libreForms/issues/61 for more details.
    # here we append any additional fields described in the `user_registration_fields` app config
    for key, value in config['user_registration_fields'].items():

        # print(key, value)

        # might eventually be worth adding support for unique fields...
        if value['type'] == str and not hasattr(User, key):
            setattr(User, key, db.Column(db.String(1000)))
            # print(key,value)

        elif value['type'] == int and not hasattr(User, key):
            setattr(User, key, db.Column(db.Integer))
            # print(key,value)


    # create the database if it doesn't exist; this, like many other
    # steps in this script, are replicated in etc/gunicorn.conf.py because
    # they need to occur before the application forks into multiple processes.
    with app.app_context():

        db.create_all()

        # create default user if doesn't exist
        # solution from https://stackoverflow.com/a/39288652
        user = db.session.query(User).filter_by(id=1)
        if user.count() < 1:
            initial_user = User(id=1,
                                username=config['default_user_username'], 
                                active=1,
                                theme='dark' if config['dark_mode'] else 'light',
                                group=config['admin_group'],
                                certificate=generate_symmetric_key(),
                                email=config['default_user_email'] if config['default_user_email'] and re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', config['default_user_email']) else None,
                                password='pbkdf2:sha256:260000$nQVWxd59E8lmkruy$13d8c4d408185ccc3549d3629be9cd57267a7d660abef389b3be70850e1bbfbf',
                                created_date='2022-06-01 00:00:00',)
            db.session.add(initial_user)
            db.session.commit()
            log.info(f'LIBREFORMS - created the default user {config["default_user_username"]}.' )

        if user.first().username != config['default_user_username']:

            # log.warning(f'LIBREFORMS - default user username `{user.first().username}` does not match admin-set default username `{config["default_user_username"]}`. Changing now. This breaks assumptions. ' )
            # user.first().username = config['default_user_username']
            # db.session.commit()
            # log.warning(f'LIBREFORMS - modified the default user username to {config["default_user_username"]}.' )

            raise Exception(f"The default user `{user.first().username}` does not match the default username set in the app config `{config['default_user_username']}`. This breaks assumptions. Please either modify the username by the `default_user_username` app config, or point the application to the correct database.")


    # if we only want to return the db instance, then we return here. To do this, you must
    # set the `db_init_only` kwarg to True in create_app(). For further discussion, see
    # https://github.com/libreForms/libreForms-flask/issues/238. 
    if db_init_only:
        return app

    ##########################
    # Configure Celery -- update the app to include the celery configurations
    ##########################

    # here we update the celery object (which we originally 
    # created outside the app context, see https://github.com/signebedi/libreForms/issues/73
    # and https://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern
    # for more explanation on this approach, which was driven by our use of the Flask factory 
    # pattern, which uses create_app) with the configs passed in the app config under `CELERY_CONFIG`. 
    celery.conf.update(app.config['CELERY_CONFIG'])


    # here we create our elastic search object; for further discussion, see
    # https://github.com/libreForms/libreForms-flask/issues/236. We want to
    # pass this to celery, so we include before returning the celery app object.
    if config['enable_search']:
        from elasticsearch_dsl import connections

        # configure Elasticsearch client
        connections.create_connection(hosts=[config['elasticsearch_host']])
        
        # add Elasticsearch client to app object
        app.elasticsearch = connections.get_connection()

        # log our success connecting to elasticsearch
        log.info('LIBREFORMS - connected to elasticsearch server.' )

    # # we define the elasticsearch indexing task here
    # @celery.task()
    # def elasticsearch_index_document(body, id, index="submissions"):
    #         # app = create_app(celery_app=True)

    #         # with app.app_context():
    #         #     app.elasticsearch.index(id, body, index=index)
    #         app.elasticsearch.index(id, body, index=index)

    #         return True

    # We create a config (yuck!) to reference the method elsewhere
    # app.config['UPDATE_ELASTIC_SEARCH'] = elasticsearch_index_document


    # to avoid circular import errors, we return the app here for the celery app context
    if celery_app:
        return app


    ##########################
    # Other imports -- other modules that we want to include within the app context
    ##########################


    # import any context-bound libraries
    from app.action_needed import standardard_total_notifications


    # this might be a little hackish, but we define a callable in app 
    # config so we can easily figure out how many notifications a given
    # user has at any given moment. I welcome feedback if there is a 
    # better way to call a context-bound function from the current_app. 
    app.config['NOTIFICATIONS'] = standardard_total_notifications


    # initialize hCaptcha object defined outside the app context, 
    # but only if hCaptcha is enabled in the app config
    if config['enable_hcaptcha']:
        hcaptcha.init_app(app)


    # create form post processing object if enabled, see 
    # https://github.com/libreForms/libreForms-flask/issues/201
    if config['enable_form_processing']:
        from app.form_processing import postProcessor
        app.config['FORM_PROCESSING'] = postProcessor()
    # else:
    #     # else define a callable that always returns None
    #     form_processing = lambda: None


    # here we employ some Flask-Login boilerplate to make 
    # user auth and session management a little easier. 
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))  


    ##########################
    # Routes and Blueprints - define default URL routes and import others from blueprints
    ##########################

    # app search index route
    # @app.route('/search/index/', methods=['POST']) ### If you keep the view, consider adding a signed URL to safeguard it
    # def index_search_engine():
    #     if request.method == 'POST':
    #         # print(request)

    #         try:
    #             # expects data to be formulated as follows:
    #             # data = json.dumps({
    #             #     'url': url_for('submissions.render_document', form_name=form_name, document_id=document_id), 
    #             #     'title': document_id,
    #             #     'content': render_template('app/index_friendly_submissions.html.jinja', form_name=form_name, submission=parsed_args),
    #             #     'page_id': document_id,
    #             # })

    #             page_id = request.json['page_id']
    #             data = request.json['data']

    #             app.elasticsearch.index(index="pages", id=page_id, body=data)
    #             return Response(json.dumps({'status':'success'}), status=config['success_code'], mimetype='application/json')

    #         except:
    #             return Response(json.dumps({'status':'failure'}), status=config['error_code'], mimetype='application/json')

    #     return abort(404)


    # # create a task status endpoint
    # @app.route('/status/<task_id>', methods=['GET'])
    # def taskstatus(task_id=None):
    #     try:
    #         task = celery.AsyncResult(task_id)
    #         response = {
    #             'state': task.state,
    #         }
    #         return jsonify(response)
    #     except :
    #         return abort(404)



    # define a route to show the application's privacy policy 
    # @app.route('/loading/<form_name>/<document_id>')
    # def loading(form_name, document_id):

    #     if mongodb.is_document_in_collection(form_name, document_id):

    #         return render_template('app/loading.html.jinja', 
    #             type="home",
    #             name='loading',
    #             notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
    #             config=config,
    #             user=current_user if current_user.is_authenticated else None,
    #             msg=f'Submitting form data for {form_name} form, document ID {document_id}'
    #         )

    #     else:
    #         return abort(404)

    # import the `forms` blueprint for form submission
    from .views import forms
    app.register_blueprint(forms.bp)

    # import the `auth` blueprint for user / session management
    from .views import auth
    app.register_blueprint(auth.bp)

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

    # if administrators have enabed user_defined_reports, then we import the `reports` 
    # blueprint, see https://github.com/signebedi/libreForms/issues/191.
    if config['user_defined_reports'] and config['enable_reports']:
        from .views import reports
        app.register_blueprint(reports.bp)

    if config['enable_search']:
        from .views import search
        app.register_blueprint(search.bp)

    if config['enable_admin_console']:
        from .views import admin
        app.register_blueprint(admin.bp)

    if config['enable_docs']:
        from .views import docs
        app.register_blueprint(docs.bp)

    if config['enable_cli']:
        from .views import cli
        app.register_blueprint(cli.bp, cli_group='libreforms')
        # app.cli.groups['libreforms'].help = 'libreforms command group help text'


    # define a home route
    @app.route('/')
    def home():

        if not config['enable_front_page_feed'] or not current_user.is_authenticated:

            return render_template('app/index.html.jinja', 
                homepage=True,
                type="home",
                name='Site',
                subtitle='Home',
                **forms.standard_view_kwargs(),
            )

        df = pd.DataFrame(columns = ['form', 'id', 'owner', 'timestamp'])
        import libreforms

        for form_name in libreforms.forms:

            # we start by verifying that this form's permissions allow it to be viewed 
            # by the current user.
            form_config = forms.propagate_form_configs(form_name)

            if any ((current_user.group in form_config['_deny_groups'],
                     current_user.group in form_config['_submission']['_deny_read'],)):
                continue

            temp = mongodb.new_read_documents_from_collection(form_name)

            if not isinstance(temp,pd.DataFrame):
                continue
            
            current_time = datetime.datetime.now()

            for index,row in temp.iterrows():

                last_edit = datetime.datetime.strptime(row[mongodb.metadata_field_names['timestamp']], "%Y-%m-%d %H:%M:%S.%f")
                time_since_last_edit = prettify_time_diff((current_time - last_edit).total_seconds())

                if all ((not form_config['_submission']['_enable_universal_form_access'],
                        current_user.username != row[mongodb.metadata_field_names['owner']] )):
                    continue
                # print(row._id, index, row)
                new_row = pd.DataFrame({    'form':[form_name], 
                                            'id': [Markup(f"<a href=\"{config['domain']}/submissions/{form_name}/{str(row['_id'])}\">{str(row['_id'])}</a>")], 
                                            'owner':[Markup(f"<a href=\"{config['domain']}/auth/profile/{row[mongodb.metadata_field_names['owner']]}\">{row[mongodb.metadata_field_names['owner']]}</a>")], 
                                            # 'timestamp':[row[mongodb.metadata_field_names['timestamp']]],})
                                            'timestamp':[time_since_last_edit],})

                df = pd.concat([df, new_row],
                        ignore_index=True)
            df.sort_values(by='timestamp', inplace=True, ignore_index=True, ascending=False)
        
            if len(df.index) > config['number_of_forms_in_feed']:
                df = df.iloc[:config['number_of_forms_in_feed']]

        return render_template('app/index.html.jinja', 
            homepage=True,
            type="home",
            name='Site',
            subtitle='Home',
            news_feed=df if config['enable_front_page_feed'] else None,
            **forms.standard_view_kwargs(),
        )

    # @app.route("/ip", methods=["GET"])
    # def get_my_ip():
    #     return jsonify({'ip': request.remote_addr}), 200

    # define a route to show the application's privacy policy,
    # if it has been enabled, see
    if config['enable_privacy_policy']:
        @app.route('/privacy')
        def privacy():
            return render_template('app/privacy.html.jinja', 
                type="home",
                name='Site',
                subtitle='Privacy',
                **forms.standard_view_kwargs(),
            )

    # add a route to the favicon
    @app.route('/favicon.ico')
    def site_favicon():
        if config['favicon']:
            directory_path, file_name = os.path.split(config['favicon'])
            return send_from_directory(directory_path, file_name)
        return send_from_directory(app.static_folder, 'default_favicon.ico')

    # add a route to the site logo
    @app.route('/site_logo')
    def site_logo():
        if config['site_logo']:
            directory_path, file_name = os.path.split(config['site_logo'])
            return send_from_directory(directory_path, file_name, mimetype="image/vnd.microsoft.icon")
        return abort(404)

    # return the app object with the above configurations
    return app



