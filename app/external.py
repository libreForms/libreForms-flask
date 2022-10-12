# import flask-related packages
from cmath import e
from fileinput import filename
from flask import Blueprint, g, flash, render_template, request, send_from_directory, abort
from webargs import fields, flaskparser
from flask_login import current_user

# import custom packages from the current repository
import libreforms, mongodb
from app import display, log, tempfile_path
from app.auth import login_required, session
from app.forms import parse_form_fields, reconcile_form_data_struct, progagate_forms, parse_options

# and finally, import other packages
import os
import pandas as pd



# signed URLs allow people to request / be invited to complete a form. 
# Scenario 1 (self initiated): anon. user goes to form page, provides email, and receives a signed link to complete. 
# Scenario 2 (invitation): current user invites another (by email) to complete a form, and the system sends a signed link over email

# we also want to consider the use case for API keys, which will be sufficiently similar to signed URLs to justify handling them
# in the same database. Signed URLs are single use, while API keys are multi use (meaning we can expect there will be fewer of them
# in circulation at any given time).

# Structure of the signed URL / API key
# 1. signature - nXhcCzeeY179SemdGtbRyWUC
# 2. timestamp - time of creation
# 3. expiration - 1 year default for API keys, 24 hours for signing keys . Do we want this to be relative (one year) or absolute (august 3rd, 2023, at 4:32.41 Zulu)
# 4. email address - yourName@example.com
# 5. scope - what resources does this give access to? form name? API? Read / Write?
# 6. active - bool, has this been marked expired? we want to keep it in the database for some time to avoid premature re-use.


# here we generate a 
def generate_key(length=24):
    key = ''
    while True:
        temp = os.urandom(1)
        if temp.isdigit() or temp.isalpha():
            key = key + temp.decode("utf-8") 
        if len(key) == length:
            return key


def write_key_to_database(form=None, api_key=False, expiration=None):
    key = generate_key()
    # open the database
    # MAKE SURE THIS ISN'T in the database

# this is a placeholder function that will periodically
# scan the keys in the database and flush any that have
# expired.
def flush_key_db():
    pass

def init_key_db():
    pass

if display['allow_anonymous_form_submissions']:

    # read database password file, if it exists
    if os.path.exists ("mongodb_creds"):
        with open("mongodb_creds", "r+") as f:
            mongodb_creds = f.read().strip()
    else:  
        mongodb_creds=None
    # initialize mongodb database
    mongodb = mongodb.MongoDB(mongodb_creds)

    # here we read the current list of acceptible signed urls; 
    # in the future, this should be a database, not a text file;
    # this section is here mostly for debugging purposes.
    if os.path.exists ("signed_urls"):
        signed_urls = pd.read_csv("signed_urls")
    else:
        signed_urls = pd.DataFrame({'signed_urls':['t32HDBcKAAIVBBPbjBADCbCh']}) # this will be the default key

    # here we add them in a format that makes them easily readable
    signed_urls = (signed_urls.signed_urls.str.strip()).values

    # we employ this function to abstract the verification process
    # for signed URLs
    def validate_signed_url(signed_url, signed_urls=signed_urls):

        # if "_allow_external_access" == True in form.options: 

        # we added the strip() method to remove trailing whitespace from the api keys
        if str(signed_url).strip() in signed_urls: 
            # in essence, the below pseudocode asks if the signed URL in question allows access to this particular form
            # if form == signed_urls.loc[signed_url == signed_url].form 
            
            return True

        else:
            return False



    # this forks forms.py to provide slightly different functionality; yes, it allows you 
    # to create forms, like in the regular forms source, but it presumes that the end user
    # for these forms will not have login credentials; instead, you define the form with the
    # _allow_external_access option set to True, and then the system allows those (in the future,
    # only those with the correct group/role) to share a signed URL via email. Therefore, there
    # is no home page for external forms; by their very nature, they are intended for single-form,
    # one-time use -- like a questionnaire, petition, or voting system.

    bp = Blueprint('external', __name__, url_prefix='/external')


    # this creates a route to request access
    @bp.route(f'/<form_name>', methods=['GET', 'POST'])
    def request_external_forms(form_name):
        # eventually, this view will enable users to request signed URLs.
        pass



    # this creates the route to each of the forms
    @bp.route(f'/<form_name>/<signed_url>', methods=['GET', 'POST'])
    def external_forms(form_name, signed_url):

        signed_url = str(signed_url)

        # we employ this method to ensure that the provided 
        # signed URL is a valid payload
        if validate_signed_url(signed_url): 

            try:
                options = parse_options(form_name)
                forms = progagate_forms(form_name)

                if request.method == 'POST':
                    parsed_args = flaskparser.parser.parse(parse_form_fields(form_name), request, location="form")
                    mongodb.write_document_to_collection(parsed_args, form_name, reporter=" ".join(("ANON", signed_url))) # we add ANON to the front to avoid collission with API keys
                    flash(str(parsed_args))

                    # possibly exchange the section below for an actual email/name depending on the
                    # data we store in the signed_urls database.
                    log.info(f'ANON {signed_url} - submitted \'{form_name}\' form.')

                return render_template('app/forms.html', 
                    context=forms,
                    name=form_name,             
                    options=options, 
                    display=display,
                    suppress_navbar=True,
                    signed_url=signed_url,
                    type='external',
                    filename = f'{form_name.lower().replace(" ","")}.csv' if options['_allow_csv_templates'] else False,
                    )

            except Exception as e:
                abort(404)
                return None

        else:
            abort(404)
            return None


    ####
    # leaving this, just in case the different base-route breaks the CSV download feature.
    ####
    @bp.route('/download/<path:filename>/<signed_url>')
    def download_file(filename, signed_url):
        if validate_signed_url(signed_url):
            
            # this is our first stab at building templates, without accounting for nesting or repetition
            df = pd.DataFrame (columns=[x for x in progagate_forms(filename.replace('.csv', '')).keys()])

            fp = os.path.join(tempfile_path, filename)
            df.to_csv(fp, index=False)

            return send_from_directory(tempfile_path,
                                    filename, as_attachment=True)

        else:
            abort(404)
            return None