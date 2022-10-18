# define default page display and,
# if a display_overrides file exists, 
# use it to overwrite defaults
import os
from libreforms import __version__
from markupsafe import Markup

display = {}
display['site_name'] = "libreForms"

# remove the Markup designation if you don't want to treat this as safe.
display['homepage_msg'] = Markup("<p>Welcome to libreForms, an extensible form building abstraction \
                            layer implemented in Flask. Select a view from above to get started. \
                            Review the docs at <a href='https://github.com/signebedi/libreForms'> \
                            https://github.com/signebedi/libreForms</a>.</p>")
display['warning_banner'] = "" 
display['theme'] = "" # unused
display['favicon'] = "" # unused
display['image'] = "" # unused
display['favicon'] = "default_favicon.ico" 
display['default_org'] = "" 
display['version'] = __version__
display['privacy_policy'] = ''
display['user_registration_fields'] = None
display['allow_anonymous_registration'] = True
display['smtp_enabled'] = False
display['ldap_enabled'] = False
display['custom_sql_db'] = False
display['allow_anonymous_form_submissions'] = True
display['domain'] = None

if os.path.exists ("app/display_overrides.py"):
    import app.display_overrides
    for config in app.display_overrides.display.keys():
        display[config] = app.display_overrides.display[config]
