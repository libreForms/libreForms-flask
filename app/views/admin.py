"""
admin.py: admin console and logic


At it's core, the admin console is a place for admin users to manage the app's behavior. This 
is rooted in a three-step approach for app configuration: `app.config`, `app.config_overrides`,
and `libreforms.env`. The `app.config` file sets the application defaults. The `app.config_overrides`
file, as the name suggests, can be used to override the default configurations. So it takes a higher
precedence than the default `app.configs` file. Finally, the system searchs for a `libreforms.env` 
file, which takes precedence over the other two files. This admin script will work primarily with 
that libreforms.env file and, when you're running gunicorn, will automatically reload the WSGI
server when it detects changes to that file. We are still working through how to get the 
werkzeug WSGI server to reload when it detects changes to that file, too. For further discussion, 
see https://github.com/libreForms/libreForms-flask/issues/255.

Generally, the admin console will try to provide the following features, though some of the
features themselves are `far horizon` features that are not currently planned in the libreForms-flask
backlog, see https://github.com/libreForms/libreForms-flask/issues/39.

    Database externalization
    Add LDAP / OAuth Authentication
    SMTP Configuration
    File System Configuration (set max file upload size)
    User and Group/Role Configuration
    Log Access
    REST API privileges (read-only or full CRUD)
    External forms (allowed or not)
    Data backup, rotation, management, retention, restore-from-backup
    Look and Feel (display overrides)
    Signing Key rotation

References:
- Edit configs using dotenv https://github.com/libreForms/libreForms-flask/issues/233
- Add admin console support https://github.com/libreForms/libreForms-flask/issues/28
- Add `log` view https://github.com/libreForms/libreForms-flask/issues/80
- Add `signing key` view https://github.com/libreForms/libreForms-flask/issues/81
- Add `user / group management` view https://github.com/libreForms/libreForms-flask/issues/82
- Add `data migration` view https://github.com/libreForms/libreForms-flask/issues/130
- Facilitate form ~deletion~ https://github.com/libreForms/libreForms-flask/issues/186
- Add `form management` view https://github.com/libreForms/libreForms-flask/issues/187
- Add `mail server` view https://github.com/libreForms/libreForms-flask/issues/234
"""

__name__ = "app.views.admin"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.6.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from flask import current_app, Blueprint, g, flash, abort, render_template, \
    request, send_from_directory, send_file, redirect, url_for
from app.views.auth import login_required, session
from flask_login import current_user


# borrows from and extends the functionality of flask_login.login_required, see
# https://github.com/maxcountryman/flask-login/blob/main/src/flask_login/utils.py.
def is_admin():
    if not current_user.is_authenticated and current_user.is_authenticated != config['admin_group']:
        return current_app.login_manager.unauthorized()
    


def login_required(func):
    """
    If you decorate a view with this, it will ensure that the current user is
    logged in and authenticated before calling the actual view. (If they are
    not, it calls the :attr:`LoginManager.unauthorized` callback.) For
    example::
        @app.route('/post')
        @login_required
        def post():
            pass
    If there are only certain times you need to require that your user is
    logged in, you can do so with::
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
    ...which is essentially the code that this function adds to your views.
    It can be convenient to globally turn off authentication when unit testing.
    To enable this, if the application configuration variable `LOGIN_DISABLED`
    is set to `True`, this decorator will be ignored.
    .. Note ::
        Per `W3 guidelines for CORS preflight requests
        <http://www.w3.org/TR/cors/#cross-origin-request-with-preflight-0>`_,
        HTTP ``OPTIONS`` requests are exempt from login checks.
    :param func: The view function to decorate.
    :type func: function
    """

    @wraps(func)
    def decorated_view(*args, **kwargs):
        if request.method in EXEMPT_METHODS or current_app.config.get("LOGIN_DISABLED"):
            pass
        elif not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()

        # flask 1.x compatibility
        # current_app.ensure_sync is only available in Flask >= 2.0
        if callable(getattr(current_app, "ensure_sync", None)):
            return current_app.ensure_sync(func)(*args, **kwargs)
        return func(*args, **kwargs)

    return decorated_view



bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/all')

# the admin handler view will verify that a user has access to the assciated 
# resource before redirecting them to it
def admin_handler(view_name):
    pass