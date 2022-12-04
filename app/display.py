""" 
display.py: collection of default app configs



## display_overrides.py

Overrides of these defaults should be stored in a file called 
app/display_overrides.py, where adminstrators can overwrite 
individual configs by creating a `display` object as follows:

display = {
    'config_name': NEW_VALUE,
    ...
}

"""

__name__ = "app.display"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.0.1"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# define default page display and,
# if a display_overrides file exists, 
# use it to overwrite defaults
import os
from libreforms import __version__
from markupsafe import Markup
from flask import current_app

display = {}
display['site_name'] = "libreForms"

# remove the Markup designation if you don't want to treat this as safe.
display['homepage_msg'] = Markup("<p>Welcome to libreForms, an extensible form building abstraction \
                            layer implemented in Flask. Select a view from above to get started. \
                            Review the docs at <a href='https://github.com/signebedi/libreForms'> \
                            https://github.com/signebedi/libreForms</a>.</p>")
display['dark_mode'] = True 
display['warning_banner'] = "" 
display['theme'] = "" # unused
display['favicon'] = "" # unused
display['image'] = "" # unused
display['favicon'] = "default_favicon.ico" 
display['default_org'] = "" 
display['version'] = __version__
display['privacy_policy'] = ''


display['user_registration_fields'] = None

# these fields allow you to determine whether email, phone, 
# and organization are required fields at registration, see 
# https://github.com/signebedi/libreForms/issues/122

display['registration_email_required'] = True
display['registration_organization_required'] = False
display['registration_phone_required'] = False



display['allow_anonymous_registration'] = True


display['allow_password_resets'] = True


display['smtp_enabled'] = True
display['ldap_enabled'] = False


display['custom_sql_db'] = False


display['enable_email_verification'] = False


display['allow_anonymous_form_submissions'] = False
display['require_auth_users_to_initiate_external_forms'] = True

display['allow_bulk_registration'] = False

display['domain'] = None


display['allow_forms_access_to_user_list'] = False


display['enable_hcaptcha'] = False
display['hcaptcha_site_key'] = False
display['hcaptcha_secret_key'] = False


display['enable_rest_api'] = False
display['limit_rest_api_keys_per_user'] = False


display['enable_user_profile_log_aggregation'] = False


display['send_reports'] = False


display['libreforms_user_email'] = None


display['mongodb_user'] = 'root'
display['mongodb_host'] = 'localhost'
display['mongodb_port'] = 27017


display['default_group'] = 'default'
display['groups'] = None
# display['allow_all_groups_default'] = True # DEPRECATED, allowing access by default


if os.path.exists ("app/display_overrides.py"):
    import app.display_overrides
    for config in app.display_overrides.display.keys():
        display[config] = app.display_overrides.display[config]
