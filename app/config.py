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
`default_user_` to set the email for the default `libreforms` 
user, otherwise the application will fail.

"""

__name__ = "app.config"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import os, secrets, dotenv
from ast import literal_eval
from markupsafe import Markup
from datetime import datetime, timedelta
from app.log_functions import v1_set_logger, v2_set_logger
# from app.log_functions import v2_set_logger

# Added based on https://github.com/signebedi/libreForms/issues/148 to
# support creating secrets and writing them to file if they don't exist.
def collect_secrets_from_file(filename):
    filepath = os.path.join(config['config_folder'], filename)
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f: 
            # create, write, and return secret key if doesn't exist
            secret_key = secrets.token_urlsafe(16)
            f.write(secret_key)
            return secret_key
    
    with open(filepath, 'r') as f: 
        return f.readlines()[0].strip()



# create application config dictionary
config = {}

##########################
# Look-and-Feel
##########################

# set the default site name
config['site_name'] = "libreForms"

# set the last restarted timestamp
config['last_restart'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 

# this sets the welcome message for the website, so customization is expected;
# you can remove the Markup designation if you don't want to render this as HTML.
# The authenticated_homepage_msg config allows admins to set a custom msg for logged
# in users, see https://github.com/libreForms/libreForms-flask/issues/489.
config['homepage_msg'] = Markup("<p>Welcome to <code>libreForms-flask</code>, an implementation of the <a href='https://github.com/libreForms/spec'>libreForms API</a> in Flask. Select a view from above to get started. You can view the app source at <a href='https://github.com/libreForms/libreForms-flask'>https://github.com/libreForms/libreForms-flask</a>. You can view the docs at <a href='https://libreforms.readthedocs.io/en/latest/'>https://libreforms.readthedocs.io/en/latest/</a>.</p>")
config['authenticated_homepage_msg'] = False

# this sets the pre-login message for the website, which will be visible to users when they
# sign into the system, see https://github.com/libreForms/libreForms-flask/issues/353
config['pre_login_msg'] = None

# sometimes, the application needs to hardcode URL endpoints; in these cases, it 
# needs to set the application domain, which defaults to the bind address for the 
# gunicorn application. Overrides should generally include protocol and ports, eg:
    # 192.168.0.15:8000
    # http://libreforms.example.com
    # https://forms.mysite.org
config['domain'] = "0.0.0.0:8000"

# this config sets the working directory for the libreforms application, which allows us
# to decouple the application from the /opt directory, replacing it with references to 
# this config, see https://github.com/libreForms/libreForms-flask/issues/121.
config['working_directory'] = "/opt/libreForms"

# this sets the default theme mode (dark or light) for the web application, which
# can be overridden by the user when they modify their user profile; it is a bool,
# and a value of True will set the theme to dark mode, for more discussion, see
# https://github.com/signebedi/libreForms/issues/129.
config['dark_mode'] = True 

# some organizations may wish to set a privacy policy and/or warning banner, which 
# these configurations allow them to do; privacy_policy is rendered at the /privacy
# route, while warning_banner is rendered on all pages if `warning_banner_on_every_page`
# is set to True.
config['enable_privacy_policy'] = False
config['privacy_policy'] = ''
config['warning_banner_on_every_page'] = False
config['warning_banner'] = ''

# this config allows organizations to set a logo for the site,
# see https://github.com/signebedi/libreForms/issues/50. The
# site_logo_height config sets the height in pixels for the logo.
config['site_logo'] = None
config['site_logo_height'] = 20

# this config sets the favicon, which can be overridden but defaults to app/static/
# default_favicon.ico
config['favicon'] = None

# this config allows admins to set the default organization for those registering for
# accounts, which is useful when standardization of this field is desired.
config['default_org'] = "" 

# this sets the app version
config['version'] = __version__


# placing the app in debug mode here will enable some greater verbosity of output, 
# eg. during form submission.
config['debug'] = False


##########################
# Configure Add'l Features
##########################

# this configuration will turn on features that are still being tested
# by the development team and may therefore not yet be fully stable, 
# see https://github.com/libreForms/libreForms-flask/issues/417
config['enable_wtforms_test_features'] = False


# these configurations determine whether to enable / disable additional 
# (technically) optional features like SMTP 
config['smtp_enabled'] = True

# these configurations are used to capture the SMTP credentials for the 
# application's outgoing mail server. There are two ways that these creds
# can be provided. First, by creating a file at config/smtp_creds, which
# expects a CSV format: smtp_server,port,username,password,from_address
# followed by a single row of comma-separated values. Second, you can 
# override these values in the config_overrides file.
config['smtp_mail_server'] = None 
config['smtp_port'] = None 
config['smtp_username'] = None 
config['smtp_password'] = None 
config['smtp_from_address'] = None 


# this configuration is used to set custom logic at the bottom of user profiles.
# nb. this will show up for ALL USERS and ALL GROUPS by default, and be universally
# readable. See https://github.com/libreForms/libreForms-flask/issues/474. If you 
# choose to pass a function here, a user object and mongodb object (so, a single 
# user and all the mongodb form data) will be passed to it. So, you should 
# assign a callable here that takes those two positional arguments.
config['user_profile_custom_logic'] = None 


# setting some celery configurations here to give a single place for admins 
# to make modifications to the default broker and backend; both of which default 
# to rabbit-mq but can easily be changed to use redis by switching both values 
# to `redis://`, see https://flask.palletsprojects.com/en/2.0.x/patterns/celery/.
config['celery_broker'] = 'pyamqp://guest@localhost//'
config['celery_backend'] = 'rpc://'

# this config enables support for sending emails asynchronously using Celery.
config['send_mail_asynchronously'] = True


# this config enables support for writing forms to MongoDB asynchronously using
# Celery. See discussion at https://github.com/libreForms/libreForms-flask/issues/180.
config['write_documents_asynchronously'] = True


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
# and https://github.com/signebedi/libreForms/issues/72. After adding the v2
# API, we created two configs to enable v1 and v2 separately, see discussion
# of tradeoffs at https://github.com/libreForms/libreForms-flask/issues/371.
# You can also set `limit_rest_api_keys_per_user` as an integer to determine 
# how many RESTful API keys each user can create. You can also set the 
# `allow_user_api_key_generation` config to allow users to generate API keys,
# see https://github.com/libreForms/libreForms-flask/issues/359. You can also
# allow users to see their API keys on their profiles by setting the app 
# config enable_user_profile_api_key_aggregation to True, see
# https://github.com/libreForms/libreForms-flask/issues/394.
config['enable_v1_rest_api'] = False
config['enable_v2_rest_api'] = False
config['limit_rest_api_keys_per_user'] = False
config['allow_user_api_key_generation'] = False
config['enable_user_profile_api_key_aggregation'] = False


# this config determines whether users will see their logs aggregated in
# their user profiles, see https://github.com/signebedi/libreForms/issues/35.
config['enable_user_profile_log_aggregation'] = False

# these config determines whether periodic reports will be sent, see
# https://github.com/signebedi/libreForms/issues/73. The `enable_reports`
# config will enable forms to be sent if it assesses to True. In addition,
# the `system_reports` config defaults to None, but can be configured to 
# send system reports (eg. complex reports with a routing list, instead of
# single-user reports). The `user_defined_reports` will allow users to create
# reports when it assesses to True. The `report_send_rate` config is a float 
# defining the interval (in seconds) we want to set between sending reports.
config['enable_reports'] = True
config['system_reports'] = None
config['user_defined_reports'] = True
config['report_send_rate'] = 3600.0

# UNTESTED: these configs specify the login credentials for the MongoDB 
# database, especially useful for externalized databases.
config['mongodb_user'] = 'root'
config['mongodb_host'] = 'localhost'
config['mongodb_port'] = 27017
config['mongodb_pw']   = None

# this config enables the health check routes defined in app.views.health_checks,
# see https://github.com/signebedi/libreForms/issues/171. For the alive and
# ready conditions, we set some basic conditions to check before returning
# a positive response, borrowed somewhat from https://stackoverflow.com/a/22738458/13301284.
# Successes return 200 by default, while errors return 503, per the discussion
# at https://stackoverflow.com/a/48005358/13301284. The ready condition defaults to
# None, which causes the view function to check database connections instead.
config['enable_health_checks'] = True
config['alive_condition'] = lambda: None
config['ready_condition'] = None
config['success_code'] = 200
config['error_code'] = 503

# these configs define the application behavior when dealing with persistent
# file uploads, see https://github.com/signebedi/libreForms/issues/10.
config['allowed_extensions'] = ['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif']
config['upload_folder'] = 'uploads/'
config['max_upload_size'] = 16 * 1000 * 1000

# these configs define the application behavior when dealing with ephemeral csv and 
# excel uploads, see https://github.com/libreForms/libreForms-flask/issues/184
# and https://github.com/libreForms/libreForms-flask/issues/378.
config['allow_form_uploads_as_excel'] = False
config['max_form_upload_size'] = 50 * 1000 

# this config sets the relative path to the config folder, which will be used
# to store instance-specific configurations, see additional discussion at
# https://github.com/signebedi/libreForms/issues/173
config['config_folder'] = 'config/'

# make the config directory if it doesn't exist
try:
    os.makedirs(config['config_folder'])
except OSError:
    pass

# these configs are used to add audio accessibility features in the UI. These are
# defined further at https://github.com/libreForms/libreForms-flask/issues/283.
config['enable_audio_accessibility'] = False
config['use_tmp_audio_accessibility'] = False
config['path_to_accessibility_audio'] = 'static'

# this config enables the use of elasticsearch by setting the `enable_search` 
# option to a value that assesses to True. This will add a search bar to the
# application frontend. The `exclude_forms_from_search` option defaults to 
# False, but can take a list of form names to exclude. The `elasticsearch_index_refresh_rate`
# field is a float defining the interval (in seconds) we want to set between each time the 
# elasticsearch index is updated. Nb. we add 50 seconds to this when selecting forms to index,
# in case there are delays in the celery task being run, as this only has the potential,
# low risk effect of reindexing forms that have already been indexed. For further discussion,
# see https://github.com/libreForms/libreForms-flask/issues/236. We added the option to 
# `use_elasticsearch_as_wrapper`, which will turn on celeryd.index_new_documents and start
# trying to index documents, see https://github.com/libreForms/libreForms-flask/issues/254.
# The `fuzzy_search` option turns fuzzy matching off, if it assesses to false, otherwise
# should be set to an option parsable by the search engine (monogdb or elasticsearch). For
# example, in elasticsearch, fuzziness can be set to "AUTO" or any int. The `limit_search_results_length`
# app config can be used to set a max number of search results to show; for further discussion,
# see https://github.com/libreForms/libreForms-flask/issues/265.
config['enable_search'] = False
config['exclude_forms_from_search'] = None
config['use_elasticsearch_as_wrapper'] = False
config['elasticsearch_host'] = 'localhost'
config['elasticsearch_index_refresh_rate'] = 600.0
config['fuzzy_search'] = False # | "AUTO" | 5 | 80 < examples for elasticsearch, elasticsearch, and fuzzywuzzy
config['limit_search_results_length'] = None

# this config determines whether to enable form post processing, which defaults to True,
# see https://github.com/libreForms/libreForms-flask/issues/201.
config['enable_form_processing'] = True

# this config determines whether the application render user documentation pages, but will disable
# them by default. In addition, if `require_login_for_docs` is set to True, then only logged in users
# will be able to see the documentation. The `docs_body` field stores the information that will be
# presented to end users on the docs page. For further discussion of this feature, see 
# https://github.com/libreForms/libreForms-flask/issues/197. After some consideration, we tell the app to 
# ignore override the `docs_body` defined here with the contents of app/static/docs/docs.html, if that 
# file exists; we further allow admins to configure this in the admin:docs_management view, see
# https://github.com/libreForms/libreForms-flask/issues/374 for further discussion Note that the 
# `allow_docs_pdf_download` config requires you to install pdf-specific requirements by running 
# `pip install -r requirements/pdf.txt`. See https://github.com/libreForms/libreForms-flask/issues/368 
# further discussion. We added the app config for `add_assets_to_user_docs`, which will essentially 
# post-process image links in user docs and point them to the static/docs/ directory, see 
# https://github.com/libreForms/libreForms-flask/issues/369.
config['enable_docs'] = False
config['docs_body'] = Markup("<h4>Sample Documentation</h4><br/><hr/><p>If you are seeing this, that means that your system administrators have enabled documentation views for the web application, but have not written their own docs. It's highly recommended that they do so!</p>")
config['require_login_for_docs'] = True
config['allow_docs_pdf_download'] = False
config['pdf_download_font_size'] = 12
config['add_assets_to_user_docs'] = True


# this config determines whether to show the five most recent forms visible to the 
# current user, see https://github.com/libreForms/libreForms-flask/issues/199.
config['enable_front_page_feed'] = False
config['number_of_forms_in_feed'] = 5

# this config determines whether to enable the libreforms CLI interface, which is defined
# further at https://github.com/libreForms/libreForms-flask/issues/123.
config['enable_cli'] = True

# as part of the restructure in https://github.com/libreForms/libreForms-flask/issues/356,
# we define v1 and v2 loggers. Whereas v1 logging retains log rotation using basic config,
# v2 adds a transaction_id that, if passed to v1, will simply do nothing. Therefore, v1 is 
# marked for eventual deprecation.
# config['logger'] = v1_set_logger
config['logger'] = v2_set_logger



##########################
# User Registration / Auth
##########################

# this config sets any additional user fields that administrators want users 
# to set during registration, see https://github.com/signebedi/libreForms/issues/61.
config['user_registration_fields'] = {}

# this config, added per https://github.com/signebedi/libreForms/issues/83, requires
# administrators to set a unique email for the `libreforms` default user.
config['default_user_email'] = None
config['default_user_username'] = 'libreforms'


# these configs allow admins to configure SAML authentication, see 
# https://github.com/libreForms/libreForms-flask/issues/7
config['saml_enabled'] = False
config['saml_idp_entity_id'] = None
config['saml_idp_sso_url'] = None
config['saml_idp_slo_url'] = None
config['saml_idp_x509_cert'] = None
config['saml_strict'] = True
config['saml_debug'] = False
config['saml_name_id_format'] = "urn:oasis:names:tc:SAML:2.0:nameid-format:unspecified"
config['saml_sp_x509_cert'] = ""
config['saml_sp_private_key'] = ""


# these configs set the system-wide regular expressions that will be used to validate
# user registration fields like username, email, and phone, for further discussion see
# https://github.com/libreForms/libreForms-flask/issues/348. In addition, we are
config['username_regex'] = r"^\w\w\w\w+$"
config['user_friendly_username_regex'] = "4-36 alphanumeric characters"
config['email_regex'] = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
config['user_friendly_email_regex'] = "name@example.com"
config['phone_regex'] = r'^[0-9]{3}-[0-9]{3}-[0-9]{4}$'
config['user_friendly_phone_regex'] = "xxx-xxx-xxxx"
config['password_regex'] =  r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+[\]{};\'\\:"|,.<>/?])[A-Za-z\d!@#$%^&*()_+[\]{};\'\\:"|,.<>/?]{8,}$'
config['user_friendly_password_regex'] = "8+ characters, must include uppercase, lowercase, digit, and special character"
config['organization_regex'] =  r".*"
config['user_friendly_organization_regex'] = ""


# this config sets the max session length as a datetime timedelta object,
# see https://github.com/libreForms/libreForms-flask/issues/395. By default,
# we set a six-hour max inactivity time before the session is cleared. You
# can also set this value to False (or, really, any non-timedelta type) and
# the application will not set a max session time.
config['session_length'] = timedelta(hours=6)

# these configs implement security controls generally related to local password
# based authentication. For futher discussion of max password age policies, see
# https://github.com/libreForms/libreForms-flask/issues/388. For setting max 
# password attemps, see https://github.com/libreForms/libreForms-flask/issues/396.
# For password reuse, see https://github.com/libreForms/libreForms-flask/issues/389;
# set `disable_password_reuse` to eg. 90 to allow reuse of passwords more than 90 
# days old, else set it to True to always prevent password reuse. 
config['max_password_age'] = False # set to an int like 365
config['max_login_attempts'] = False # set to an int like 3
config['disable_password_reuse'] = True # set to an int like 90 or True

# this config allows admins to set a max period of inactivity (eg. time passing between
# logins) until account disabled, see https://github.com/libreForms/libreForms-flask/issues/408.
config['max_account_inactivity'] = False # set to an int like 30


# these configs define the groups available for users to fall under, and the default
# group that new users are part of; this application employs a one-to-one user:group
# mapping - every user can only have one group - so there is some potentially complex
# setups with this approach, and we probably need to create an admin view for user/group
# management, see https://github.com/signebedi/libreForms/issues/82. We also assign the 
# admin group, which is used to restrict access to the admin views like bulk user 
# registration, see https://github.com/signebedi/libreForms/issues/170.
config['default_group'] = 'default'
config['admin_group'] = 'admin'
config['groups'] = ['admin', 'default', 'manager']

# these configs define the admin console behavior. The `enable_admin_console` config
# creates the route to the admin view, which by default is limited to users in the
# `admin_group` defined above. For additional discussion of admin console setup and
# configuration, see https://github.com/libreForms/libreForms-flask/issues/28.
config['enable_admin_console'] = True

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


# this config determines whether users will be sent MFA tokens in their email to enable them to
# login to the web app. It requires the `smtp_enabled` to be set to True. For further discussion,
# see https://github.com/libreForms/libreForms-flask/issues/328.
config['enable_email_login_mfa'] = False

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


# this config determines whether other profiles can be viewed in the web application,
# see https://github.com/libreForms/libreForms-flask/issues/298. Future work may improve this
# by adding some access control restrictions to what groups can see profiles, and how much
# information can be seen, see https://github.com/libreForms/libreForms-flask/issues/300.
config['enable_other_profile_views'] = False

# this config determines whether the application will try to render usernames as badges, 
# for aesthetic and potentially funtional purposes, see the following for further discussion:
# https://github.com/libreForms/libreForms-flask/issues/299. Please note this may not work as
# expected / desired when `visible_signature_field` has been changed, but this can probably be fixed.
config['parse_usernames_as_badges'] = True



# this configuration determines whether to send an email notification when administrators change
# their passwords, disable their accounts, or disable signing keys associated with their emails,
# see https://github.com/libreForms/libreForms-flask/issues/379.
config['notify_users_on_admin_action'] = True


# here we overwrite the defaults above with any user-specified 
# configurations in app.config_overrides, if it exists.
if os.path.exists ("app/config_overrides.py"):
    from app.config_overrides import config as config_override
    for conf in config_override.keys():
        config[conf] = config_override[conf]


# here we overwrite the defaults above with any dotenv configurations,
# which take precendence over both base configs and config overrides.
if os.path.exists ("libreforms.env"):
    dotenv_file = dotenv.find_dotenv('libreforms.env')

    # dotenv.load_dotenv(dotenv_file)
    # for key,value in config.items():
    #     config[key] = os.environ[key.upper()] if key in os.environ else value

    dotenv_configs = dotenv.dotenv_values(dotenv_file)
    # print(dotenv_configs)

    for key,value in dotenv_configs.items():
        value = literal_eval(value) if value in ['True','False'] else value
        # print(key,value,type(value))
        config[key.lower()] = value
        # print(key.lower(), config[key.lower()])