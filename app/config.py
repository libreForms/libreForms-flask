""" 
config.py: collection of default app configs

This script sets default configurations for the
web application.



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

# define default page config and,
# if a config_overrides file exists, 
# use it to overwrite defaults
import os, secrets
from markupsafe import Markup
from flask import current_app

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

# remove the Markup designation if you don't want to render this as HTML.
config['homepage_msg'] = Markup("<p>Welcome to libreForms, an extensible form building abstraction layer implemented in Flask. Select a view from above to get started. Review the docs at <a href='https://github.com/signebedi/libreForms'>https://github.com/signebedi/libreForms</a>.</p>")
config['domain'] = None
config['dark_mode'] = True 
config['warning_banner'] = "" 
config['favicon'] = "" # unused
config['image'] = "" # unused
config['favicon'] = "default_favicon.ico" 
config['default_org'] = "" 
config['version'] = __version__
config['privacy_policy'] = ''
config['warning_banner'] = ''


##########################
# User Registration / Auth
##########################

config['user_registration_fields'] = None

config['libreforms_user_email'] = None

config['default_group'] = 'default'
config['groups'] = ['admin', 'default']

# these fields allow you to determine whether email, phone, 
# and organization are required fields at registration, see 
# https://github.com/signebedi/libreForms/issues/122

config['registration_email_required'] = True
config['registration_organization_required'] = False
config['registration_phone_required'] = False


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


# this config toggles whether users must re-enter their
# passwords when electronically signing documents, see 
# https://github.com/signebedi/libreForms/issues/167.
config['require_password_for_electronic_signatures'] = True


config['allow_anonymous_registration'] = True


config['allow_password_resets'] = True


# by default, the signing keys generated and managed in app.signing are
# 24 characters long.
config['signing_key_length'] = 24



##########################
# Configure Add'l Features
##########################

config['smtp_enabled'] = True
config['ldap_enabled'] = False

# setting some celery configurations here to give 
# a single place for admins to make modifications
config['celery_broker'] = 'pyamqp://'
config['celery_backend'] = 'rpc://'

config['custom_sql_db'] = False


config['enable_email_verification'] = False
config['send_mail_asynchronously'] = False

config['allow_anonymous_form_submissions'] = False
config['require_auth_users_to_initiate_external_forms'] = True

config['allow_bulk_registration'] = False


config['allow_forms_access_to_user_list'] = False


config['enable_hcaptcha'] = False
config['hcaptcha_site_key'] = False
config['hcaptcha_secret_key'] = False


config['enable_rest_api'] = False
config['limit_rest_api_keys_per_user'] = False


config['enable_user_profile_log_aggregation'] = False


config['send_reports'] = False



config['mongodb_user'] = 'root'
config['mongodb_host'] = 'localhost'
config['mongodb_port'] = 27017
config['mongodb_pw']   = None



if os.path.exists ("app/config_overrides.py"):
    from app.config_overrides import config as config_override
    for conf in config_override.keys():
        # print(conf, config_override[conf])
        config[conf] = config_override[conf]
