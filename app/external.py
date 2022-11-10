# import flask-related packages
import re, datetime
from cmath import e
from fileinput import filename
from flask import Blueprint, g, flash, render_template, request, send_from_directory, abort, redirect, url_for
from webargs import fields, flaskparser
from flask_login import current_user

# import custom packages from the current repository
import libreforms, mongodb
from app import display, log, tempfile_path, mailer
from app.auth import login_required, session
from app.forms import parse_form_fields, reconcile_form_data_struct, progagate_forms, parse_options
import app.signing as signing
from app.models import Signing


# and finally, import other packages
import os
import pandas as pd



if display['allow_anonymous_form_submissions']:

    # read database password file, if it exists
    if os.path.exists ("mongodb_creds"):
        with open("mongodb_creds", "r+") as f:
            mongodb_creds = f.read().strip()
    else:  
        mongodb_creds=None
    # initialize mongodb database
    mongodb = mongodb.MongoDB(mongodb_creds)

    # this forks forms.py to provide slightly different functionality; yes, it allows you 
    # to create forms, like in the regular forms source, but it presumes that the end user
    # for these forms will not have login credentials; instead, you define the form with the
    # _allow_anonymous_access option set to True, and then the system allows those (in the future,
    # only those with the correct group/role) to share a signed URL via email. Therefore, there
    # is no home page for external forms; by their very nature, they are intended for single-form,
    # one-time use -- like a questionnaire, petition, or voting system.

    bp = Blueprint('external', __name__, url_prefix='/external')


    # this creates a route to request access
    @bp.route(f'/<form_name>', methods=['GET', 'POST'])
    def request_external_forms(form_name):

        # first make sure this form existss
        try:
            forms = parse_options(form_name)
        except Exception as e:
            log.error(f'LIBREFORMS - {e}')
            abort(404)

        # if the appropriate configurations are set, all us to proceed
        if request.method == 'POST' and display["allow_anonymous_form_submissions"] and forms['_allow_anonymous_access']:
            email = request.form['email']
            
            if not email:
                error = f'Please enter a valid email.' 
            elif email and not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
                error = 'Invalid email.' 

            else:error=None

            if not error:
                try: 
                    key = signing.write_key_to_database(scope=f'external_{form_name.lower()}', expiration=1, active=1, email=email)
                    content = f"You may now submit form {form_name} at the following address: {display['domain']}/external/{form_name}/{key}. Please note this link will expire after one hour."
                    mailer.send_mail(subject=f'{display["site_name"]} {form_name} Submission Link', content=content, to_address=email, logfile=log)
                    flash("Form submission link successfully sent.")
                except Exception as e:
                    flash(e)
            else:
                flash(error)
                
        return render_template('app/external_request.html', 
            name=form_name,             
            display=display,
            suppress_navbar=True,
            type='external',
            )

    # this creates the route to each of the forms
    @bp.route(f'/<form_name>/<signature>', methods=['GET', 'POST'])
    def external_forms(form_name, signature):

        if not display['allow_anonymous_form_submissions']:
            flash('This feature has not been enabled by your system administrator.')
            return redirect(url_for('home'))

        if not Signing.query.filter_by(signature=signature).first():
            flash('Invalid request key. ')
            return redirect(url_for('home'))

        # if the signing key's expiration time has passed, then set it to inactive 
        if Signing.query.filter_by(signature=signature).first().expiration < datetime.datetime.timestamp(datetime.datetime.now()):
            signing.expire_key(signature)

        # if the signing key is set to inactive, then we prevent the user from proceeding
        # this might be redundant to the above condition - but is a good redundancy for now
        if Signing.query.filter_by(signature=signature).first().active == 0:
            flash('Invalid request key. ')
            return redirect(url_for('home'))

        # if the signing key is not scoped (that is, intended) for this purpose, then 
        # return an invalid error
        if not Signing.query.filter_by(signature=signature).first().scope == f'external_{form_name.lower()}':
            flash('Invalid request key. ')
            return redirect(url_for('home'))

        try:
            options = parse_options(form_name)
            forms = progagate_forms(form_name)

            if request.method == 'POST':
                parsed_args = flaskparser.parser.parse(parse_form_fields(form_name), request, location="form")
                mongodb.write_document_to_collection(parsed_args, form_name, reporter=" ".join((Signing.query.filter_by(signature=signature).first().email, signature))) 
                flash(str(parsed_args))

                # possibly exchange the section below for an actual email/name depending on the
                # data we store in the signed_urls database.
                log.info(f'{Signing.query.filter_by(signature=signature).first().email} {signature} - submitted \'{form_name}\' form.')

                print(Signing.query.filter_by(signature=signature).first().email)

                signing.expire_key(signature)

                return redirect(url_for('home'))

            return render_template('app/forms.html', 
                context=forms,
                name=form_name,             
                options=options, 
                display=display,
                suppress_navbar=True,
                signed_url=signature,
                type='external',
                filename = f'{form_name.lower().replace(" ","")}.csv' if options['_allow_csv_templates'] else False,
                )

        except Exception as e:
            print(e)
            abort(404)
            return None

        else:
            abort(404)
            return None


    ####
    # leaving this, just in case the different base-route breaks the CSV download feature.
    ####
    @bp.route('/download/<path:filename>/<signature>')
    def download_file(filename, signature):

        if not display['allow_anonymous_form_submissions']:
            flash('This feature has not been enabled by your system administrator.')
            return redirect(url_for('home'))

        if not Signing.query.filter_by(signature=signature).first():
            flash('Invalid request key. ')
            return redirect(url_for('home'))

        # if the signing key's expiration time has passed, then set it to inactive 
        if Signing.query.filter_by(signature=signature).first().expiration < datetime.datetime.timestamp(datetime.datetime.now()):
            signing.expire_key(signature)

        # if the signing key is set to inactive, then we prevent the user from proceeding
        # this might be redundant to the above condition - but is a good redundancy for now
        if Signing.query.filter_by(signature=signature).first().active == 0:
            abort(404)

        # if the signing key is not scoped (that is, intended) for this purpose, then 
        # return an invalid error
        if not Signing.query.filter_by(signature=signature).first().scope == f'external_{(filename.split(".")[0]).lower()}':
            abort(404)

        # this is our first stab at building templates, without accounting for nesting or repetition
        df = pd.DataFrame (columns=[x for x in progagate_forms(filename.replace('.csv', '')).keys()])

        fp = os.path.join(tempfile_path, filename)
        df.to_csv(fp, index=False)

        return send_from_directory(tempfile_path,
                                filename, as_attachment=True)

