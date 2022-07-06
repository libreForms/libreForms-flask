# import flask-related packages
from cmath import e
from fileinput import filename
from flask import Blueprint, g, flash, render_template, request, send_from_directory
from webargs import fields, flaskparser
from flask_login import current_user

# import custom packages from the current repository
import libreforms, mongodb
from app import display, log
from app.auth import login_required, session
from app.forms import parse_form_fields, reconcile_form_data_struct, progagate_forms, parse_options

# and finally, import other packages
import os
import pandas as pd


# read database password file, if it exists
if os.path.exists ("mongodb_pw"):
    with open("mongodb_pw", "r+") as f:
        mongodb_pw = f.read().strip()
else:  
    mongodb_pw=None
# initialize mongodb database
mongodb = mongodb.MongoDB(mongodb_pw)


def generate_signed_url(form=None):
    # placeholder for the logic of generating 
    # and propagating the signed URLs for a given form.
    pass


# here we read the current list of acceptible signed urls; 
# in the future, this should be a database, not a text file;
# this section is here mostly for debugging purposes.
if os.path.exists ("signed_urls"):
    signed_urls = pd.read_csv("signed_urls")
else:
    signed_urls = pd.DataFrame({'signed_urls':['t32HDBcKAAIVBBPbjBADCbCh']}) # this will be the default key


# this forks forms.py to provide slightly different functionality; yes, it allows you 
# to create forms, like in the regular forms source, but it presumes that the end user
# for these forms will not have login credentials; instead, you define the form with the
# _allow_external_access option set to True, and then the system allows those (in the future,
# only those with the correct group/role) to share a signed URL via email. Therefore, there
# is no home page for external forms; by their very nature, they are intended for single-form,
# one-time use -- like a questionnaire, petition, or voting system.

bp = Blueprint('external', __name__, url_prefix='/external')

# this creates the route to each of the forms
@bp.route(f'/<form_name>/<signed_url>', methods=['GET', 'POST'])
def external_forms(form_name, signed_url):

    # if "_allow_external_access" == True in form.options: 

    # else resolve to a not found error
    # here we capture the string-ified API key passed by the user
    signed_url = str(signed_url)
    
    # we added the strip() method to remove trailing whitespace from the api keys
    if signed_url in (signed_urls.signed_urls.str.strip()).values: 

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

            return render_template('app/index.html', 
                context=forms,                                          # this passes the form fields as the primary 'context' variable
                name=form_name,                                         # this sets the name of the page for the page header
                options=options, 
                display=display,
                suppress_navbar=True,
                signed_url=signed_url,
                type='external',
                filename = f'{form_name.lower().replace(" ","")}.csv' if options['_allow_csv_templates'] else False,
                )

        except Exception as e:
            return "Invalid link"

    else:
        return "Invalid link"


####
# leaving this, just in case the different base-route breaks the CSV download feature.
####
@bp.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory('static/tmp',
                               filename, as_attachment=True)
