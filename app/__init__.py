
import os
from flask import Flask, render_template
import app.log_functions


# if application log path doesn't exist, make it
if not os.path.exists ("log/"):
    os.mkdir('log/')

# we instantiate a log object that 
# we'll propagate across the app

log = app.log_functions.set_logger('log/libreforms.log',__name__)
log.info('started libreforms web application.')

# define default page display and,
# if a site_overrides file exists, 
# use it to overwrite defaults

display = {}
display['site_name'] = "libreForms"
display['homepage_msg'] = "Welcome to libreForms, an extensible form building abstraction \
                            layer implemented in Flask. Select a view from above to get started. \
                            Review the docs at https://github.com/signebedi/libreForms."
display['warning_banner'] = "" 
display['theme'] = "" # unused
display['favicon'] = "" # unused
display['image'] = "" # unused
display['favicon'] = "default_favicon.ico" 
display['default_org'] = "" 

if os.path.exists ("app/site_overrides.py"):
    import app.site_overrides
    for config in app.site_overrides.display.keys():
        display[config] = app.site_overrides.display[config]
    log.info('found a site overrides file.')


def create_app(test_config=None):
 
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'app.sqlite'),
    )

    if os.path.exists ("secret_key"):
        with open("secret_key", "r+") as f:
            app.config["SECRET_KEY"] = f.read().strip()
        log.info('found a secret key file.')


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
        )

    from . import db
    db.init_app(app)

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

    return app