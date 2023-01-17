""" 
external.py: implementation of views external submission of forms



"""

__name__ = "app.views.external"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# import flask-related packages
import re, datetime
from cmath import e
from fileinput import filename
from flask import current_app, Blueprint, g, flash, render_template, request, send_from_directory, abort, redirect, url_for
from webargs import fields, flaskparser
from flask_login import current_user

# import custom packages from the current repository
import libreforms
from app import config, log, mailer, mongodb
from app.views.auth import login_required, session
from app.views.forms import define_webarg_form_data_types, checkGroup, reconcile_form_data_struct, \
    propagate_form_fields, propagate_form_configs, compile_depends_on_data, rationalize_routing_list
import app.signing as signing
from app.models import Signing, db


# and finally, import other packages
import os
import pandas as pd


# defining a decorator that applies a parent decorator 
# based on the truth-value of a condition
def conditional_decorator(dec, condition):
    def decorator(func):
        if not condition:
            # Return the function unchanged, not decorated.
            return func
        return dec(func)
    return decorator


if config['allow_anonymous_form_submissions']:


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
    # here we apply the login_required decorator if admins require users to be authenticated in order
    # to initiate external submissions, see 'require_auth_users_to_initiate_external_forms'.
    @conditional_decorator(login_required, config['require_auth_users_to_initiate_external_forms'])
    def request_external_forms(form_name):

        # first make sure this form existss
        try:
            forms = propagate_form_configs(form_name)
        except Exception as e:
            log.error(f'LIBREFORMS - {e}')
            return abort(404)

        if not checkGroup(group='anonymous', struct=propagate_form_configs(form_name)):
            flash(f'Your system administrator has disabled this form for anonymous users.')
            return redirect(url_for('home'))


        # if the appropriate configurations are set, all us to proceed
        if request.method == 'POST' and config["allow_anonymous_form_submissions"] and forms['_allow_anonymous_access']:
            email = request.form['email']
            
            if not email:
                error = f'Please enter a valid email.' 
            elif email and not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
                error = 'Invalid email.' 

            else:error=None

            if not error:
                try: 
                    key = signing.write_key_to_database(scope=f'external_{form_name.lower()}', expiration=48, active=1, email=email)
                    content = f"You may now submit form {form_name} at the following address: {config['domain']}/external/{form_name}/{key}. Please note this link will expire after 48 hours."
                    current_app.config['MAILER'](subject=f'{config["site_name"]} {form_name} Submission Link', content=content, to_address=email, logfile=log).apply_async()
                    flash("Form submission link successfully sent.")
                except Exception as e:
                    flash(e)
            else:
                flash(error)
                
        return render_template('app/external_request.html', 
            name=form_name,             
            config=config,
            suppress_navbar=True,
            user=current_user if config['require_auth_users_to_initiate_external_forms'] else None,
            type='external',
            )

    # this creates the route to each of the forms
    @bp.route(f'/<form_name>/<signature>', methods=['GET', 'POST'])
    def external_forms(form_name, signature):

        if not config['allow_anonymous_form_submissions']:
            flash('This feature has not been enabled by your system administrator.')
            return redirect(url_for('home'))

        if not checkGroup(group='anonymous', struct=propagate_form_configs(form_name)):
            flash(f'Your system administrator has disabled this form for anonymous users.')
            return redirect(url_for('home'))

        if not signing.verify_signatures(signature, redirect_to='home', 
                                            scope=f'external_{form_name.lower()}', abort_on_error=True):


            try:
                options = propagate_form_configs(form_name)
                forms = propagate_form_fields(form_name)

                if request.method == 'POST':
                    parsed_args = flaskparser.parser.parse(define_webarg_form_data_types(form_name), request, location="form")
                    
                    # we query quickly for the email address associated with this signing key
                    email = Signing.query.filter_by(signature=signature).first().email
                    
                    # we submit the document and store the returned Object ID as a document_id
                    document_id = mongodb.write_document_to_collection( parsed_args, form_name, reporter=" ".join((email, signature)),
                                                                        ip_address=request.remote_addr if options['_collect_client_ip'] else None) 

                    # if config['write_documents_asynchronously']:
                    #     import time, requests
                    #     while True:
                    #         requests.get(url_for('taskstatus', task_id=document_id.task_id))
                    #         print(r.task_id)
                    #         time.sleep(.1)

                    flash(f'{form_name} form successfully submitted, document ID {document_id}. ')
                    if config['debug']:
                        flash(str(parsed_args))

                    # possibly exchange the section below for an actual email/name depending on the
                    # data we store in the signed_urls database.
                    log.info(f'{Signing.query.filter_by(signature=signature).first().email} {signature} - submitted \'{form_name}\' form.')

                    # print(Signing.query.filter_by(signature=signature).first().email)

                    signing.expire_key(signature)

                    # here we build our message and subject, customized for anonymous users
                    subject = f'{config["site_name"]} {form_name} Submitted ({document_id})'
                    content = f"This email serves to verify that an anonymous user {signature} (linked to {email}) has just submitted the {form_name} form. {'; '.join(key + ': ' + str(value) for key, value in parsed_args.items() if key != 'Journal') if options['_send_form_with_email_notification'] else ''}"
                    
                    # and then we send our message
                    current_app.config['MAILER'](subject=subject, content=content, to_address=email, cc_address_list=rationalize_routing_list(form_name), logfile=log).apply_async()


                    return redirect(url_for('home'))

                return render_template('app/forms.html', 
                    context=forms,
                    name=form_name,             
                    options=options, 
                    config=config,
                    suppress_navbar=True,
                    signed_url=signature,
                    type='external',
                    depends_on=compile_depends_on_data(form_name, user_group='anonymous'),
                    filename = f'{form_name.lower().replace(" ","")}.csv' if options['_allow_csv_templates'] else False,
                    )

            except Exception as e:
                print(e)
                return abort(404)
                return None

        else:
            return abort(404)
            return None


    ####
    # leaving this, just in case the different base-route breaks the CSV download feature.
    ####
    @bp.route('/download/<signature>/<path:filename>')
    def download_file(filename, signature):

        if not config['allow_anonymous_form_submissions']:
            flash('This feature has not been enabled by your system administrator.')
            return redirect(url_for('home'))

        if not signing.verify_signatures(signature, redirect_to='home', 
                                             # the following is a little hacky, but allows us to avoid needing to reiterate the 
                                             # form_name in the URL...
                                            scope=f'external_{filename.replace(".csv", "").lower()}'):


            # this is our first stab at building templates, without accounting for nesting or repetition
            df = pd.DataFrame (columns=[x for x in propagate_form_fields(filename.replace('.csv', '')).keys()])

            # here we employ a context-bound temp directory to stage this file for download, see
            # discussion in app.tmpfiles and https://github.com/signebedi/libreForms/issues/169.
            from app.tmpfiles import temporary_directory
            with temporary_directory() as tempfile_path:

                # appending `template` to the start to avoid confusion with other downloads
                template_filename = "template_"+filename

                fp = os.path.join(tempfile_path, template_filename)
                df.to_csv(fp, index=False)

                return send_from_directory(tempfile_path,
                                    template_filename, as_attachment=True)
        else:
            return abort(404)

