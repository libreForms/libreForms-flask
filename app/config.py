""" 
config.py: collection of default app configs

This script sets default configurations for the libreForms
web application. The values contained here are overriden by
an admin-supplied config_overrides.py file.


## config_overrides.py

The default application configuration should be modified with
app.config_overrides, where adminstrators can set unique configs 
by creating a `config` object as follows:

config = {
    'config_name': NEW_VALUE,
    ...
}

Please note that config_overrides.py must be created in order for the 
web application to function. In addition, it must include a field for
`libreforms_user_email` to set the email for the default `libreforms` 
user, otherwise the application will fail.

"""

__name__ = "app.config"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import os, secrets
from markupsafe import Markup

# Added based on https://github.com/signebedi/libreForms/issues/148 to
# support creating secrets and writing them to file if they don't exist.
def collect_secrets_from_file(filename):
    if not os.path.exists(filename):
        with open(filename, 'w') as f: 
            # create, write, and return secret key if doesn't exist
            secret_key = secrets.token_urlsafe(16)
            f.write(secret_key)
            return secret_key
    
    with open(filename, 'r') as f: 
        return f.readlines()[0].strip()

# create application config dictionary
config = {}

##########################
# Look-and-Feel
##########################

# set the default site name
config['site_name'] = "libreForms"

# this sets the welcome message for the website, so customization is expected;
# you can remove the Markup designation if you don't want to render this as HTML.
config['homepage_msg'] = Markup("<p>Welcome to libreForms, an extensible form building abstraction layer implemented in Flask. Select a view from above to get started. Review the docs at <a href='https://github.com/signebedi/libreForms'>https://github.com/signebedi/libreForms</a>.</p>")

# sometimes, the application needs to hardcode URL endpoints; in these cases, it 
# needs to set the application domain, which defaults to the bind address for the 
# gunicorn application. Overrides should generally include protocol and ports, eg:
    # 192.168.0.15:8000
    # http://libreforms.example.com
    # https://forms.mysite.org
config['domain'] = "0.0.0.0:8000"

# this sets the default theme mode (dark or light) for the web application, which
# can be overridden by the user when they modify their user profile; it is a bool,
# and a value of True will set the theme to dark mode, for more discussion, see
# https://github.com/signebedi/libreForms/issues/129.
config['dark_mode'] = True 

# some organizations may wish to set a privacy policy and/or warning banner, which 
# these configurations allow them to do; privacy_policy is rendered at the /privacy
# route, while the warning_banner is rendered on all pages.
config['privacy_policy'] = ''
config['warning_banner'] = ''

# this config, once implemented, will allow organizations to set a logo for the site,
# see https://github.com/signebedi/libreForms/issues/50.
config['image'] = "" # unused

# this config sets the favicon, which can be overridden
config['favicon'] = "default_favicon.ico" 

# this config allows admins to set the default organization for those registering for
# accounts, which is useful when standardization of this field is desired.
config['default_org'] = "" 

# this sets the app version
config['version'] = __version__


##########################
# User Registration / Auth
##########################

# this config sets any additional user fields that administrators want users 
# to set during registration, see https://github.com/signebedi/libreForms/issues/61.
config['user_registration_fields'] = {}

# this config, added per https://github.com/signebedi/libreForms/issues/83, requires
# administrators to set a unique email for the `libreforms` default user.
config['libreforms_user_email'] = None

# these configs define the groups available for users to fall under, and the default
# group that new users are part of; this application employs a one-to-one user:group
# mapping - every user can only have one group - so there is some potentially complex
# setups with this approach, and we probably need to create an admin view for user/group
# management, see https://github.com/signebedi/libreForms/issues/82. We also assign the 
# admin group, which is used to restrict access to the admin views like bulk user 
# registration, see https://github.com/signebedi/libreForms/issues/170.
config['default_group'] = 'default'
config['admin_group'] = 'admin'
config['groups'] = ['admin', 'default']

# these fields allow you to determine whether email, phone, and organization are required 
# fields at registration, see https://github.com/signebedi/libreForms/issues/122.
config['registration_email_required'] = True
config['registration_organization_required'] = False
config['registration_phone_required'] = False

# here we set various keys using collect_secrets_from_file to read keys from their
# corresponding files, or to create them if they don't exist.
config['secret_key'] = collect_secrets_from_file('secret_key')
config['signature_key'] = collect_secrets_from_file('signature_key')
config['approval_key'] = collect_secrets_from_file('approval_key')
config['disapproval_key'] = collect_secrets_from_file('disapproval_key')

# as a default, we will config a user's username as their 'signature' 
# when they have electronically signed a document; Nb. this must be a 
# field in the User database. For example, administrators may wish to
# display the user's full name (if this is specified as a custom field)
# instead of using usernames, which may not be sufficiently descriptive.
config['visible_signature_field'] = 'username'


# this config toggles whether users must re-enter their passwords when electronically 
# signing documents, see https://github.com/signebedi/libreForms/issues/167.
config['require_password_for_electronic_signatures'] = True

# this config determines whether anonymous users can register for user accounts using
# the auth/register endpoint; this should be set to false when users are created centrally,
# or when auth is externalized eg. using LDAP, see https://github.com/signebedi/libreForms/issues/7.
config['allow_anonymous_registration'] = True

# this config determines whether users can reset their passwords anonymously, using the 
# auth/forgot_password route; administrator password resets, as well as password resets
# through the user profile while authenticated, will still be supported.
config['allow_password_resets'] = True

# by default, the signing keys generated and managed in app.signing are 24 characters long,
# but these can be extended eg. to 48 when needed.
config['signing_key_length'] = 24

# this config, when set to True, will send verification emails when new users are registered;
# it will require users to verify their accounts prior to activation, for more details,
# see https://github.com/signebedi/libreForms/issues/58.
config['enable_email_verification'] = False

# this config determines whether the /external route is enabled; this is the basis for users
# submitting forms without authenticating first, see https://github.com/signebedi/libreForms/issues/67.
config['allow_anonymous_form_submissions'] = False

# this config, if set to True, only allows authenticated users to invite non-authenticated 
# users to complete form submissions anonymously, see https://github.com/signebedi/libreForms/issues/85
config['require_auth_users_to_initiate_external_forms'] = True

# this config determines whether users can be registered in bulk, see https://github.com/signebedi/libreForms/issues/64;
# note that this feature will by default restrict user's ability to do this to the admin group,
# see https://github.com/signebedi/libreForms/issues/170. 
config['allow_bulk_registration'] = False
config['limit_bulk_registration_to_admin_group'] = True

# this config allows forms to access the current user list as a field, which carries some 
# implicit security risk.
config['allow_forms_access_to_user_list'] = False

##########################
# Configure Add'l Features
##########################

# these configurations determine whether to enable / disable additional 
# (technically) optional features like SMTP and LDAP.
config['smtp_enabled'] = True
config['ldap_enabled'] = False

# setting some celery configurations here to give a single place for admins 
# to make modifications to the default broker and backend; both of which default 
# to rabbit-mq but can easily be changed to use redis by switching both values 
# to `redis://`, see https://flask.palletsprojects.com/en/2.0.x/patterns/celery/.
config['celery_broker'] = 'pyamqp://'
config['celery_backend'] = 'rpc://'

# this config enables support for sending emails asynchronously using Celery.
config['send_mail_asynchronously'] = False

# UNTESTED: when users want to specify a custom SQL database rather than the 
# default SQLite database created by the application.
config['custom_sql_db'] = False

# these configs determine whether to employ hCaptcha to verify low trust 
# environments, see https://github.com/signebedi/libreForms/issues/63.
config['enable_hcaptcha'] = False
config['hcaptcha_site_key'] = False
config['hcaptcha_secret_key'] = False

# these configurations determine whether RESTful API access is enabled
# for the application, see https://github.com/signebedi/libreForms/issues/75
# and https://github.com/signebedi/libreForms/issues/72. You can also set an
# integer to determine how many RESTful API keys each user can create.
config['enable_rest_api'] = False
config['limit_rest_api_keys_per_user'] = False

# this config determines whether users will see their logs aggregated in
# their user profiles, see https://github.com/signebedi/libreForms/issues/35.
config['enable_user_profile_log_aggregation'] = False

# this config determines whether periodic reports will be sent, see
# https://github.com/signebedi/libreForms/issues/73. 
config['send_reports'] = False

# UNTESTED: these configs specify the login credentials for the MongoDB 
# database, especially useful for externalized databases.
config['mongodb_user'] = 'root'
config['mongodb_host'] = 'localhost'
config['mongodb_port'] = 27017
config['mongodb_pw']   = None

# this config enables the health check routes defined in app.health_checks,
# see https://github.com/signebedi/libreForms/issues/171.
config['enable_health_checks']   = True

# these configs define the application behavior when dealing with persistent
# file uploads, see https://github.com/signebedi/libreForms/issues/10.
config['allowed_extensions'] = ['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif']
config['upload_folder'] = 'downloads/'
config['max_upload_size'] = 16 * 1000 * 1000


# here we overwrite the defaults above with any user-specified 
# configurations in app.config_overrides, if it exists.
if os.path.exists ("app/config_overrides.py"):
    from app.config_overrides import config as config_override
    for conf in config_override.keys():
        config[conf] = config_override[conf]
