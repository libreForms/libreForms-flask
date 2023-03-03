""" 
tasks.py: tasks for the libreForms celery app

Whereas celeryd/__init__.py is where we reinstantiate the app 
context and push it to the celery object so that the daemons
we are running in the background (libreforms-celery, libreforms-
celerybeat, and libreforms-flower) can access the celery app;
this script is includes all the tasks we plan to run within 
view functions, and as such have no need of the app context
and would cause circular import errors if we did push the
app context here.

"""

__name__ = "celery.tasks"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.7.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from app import celery, log, mailer, mongodb, create_app
from flask import current_app
import os
from datetime import datetime

# here we define a tasks to send emails asynchonously - it's just a 
# celery wrapper for the function library defined in app.smtp.
@celery.task()
def send_mail_async(subject, content, to_address, cc_address_list=[], logfile=log):
    mailer.send_mail(   subject=subject, content=content, to_address=to_address, 
                        cc_address_list=cc_address_list, logfile=log)
    log.info(f'successfully sent an email to {to_address}')


# here we define an asynchronous wrapper function for the app.mongo.write_documents_to_collection 
# method, which we'll implement when the `write_documents_asynchronously` config is set, see
# https://github.com/libreForms/libreForms-flask/issues/180.
@celery.task(bind=True)
def write_document_to_collection_async(self, data, collection_name, reporter=None, modification=False, 
                                        digital_signature=None, approver=None, approval=None, approver_comment=None, ip_address=None):

    # self.delay()

    self.update_state(state='PENDING')
    # print('PENDING')

    document_id = mongodb.write_document_to_collection(data, collection_name, reporter=reporter, modification=modification, 
                                        digital_signature=digital_signature, approver=approver, approval=approval, 
                                        approver_comment=approver_comment, ip_address=ip_address)

    self.update_state(state='COMPLETE')
    # print('COMPLETE')

    return document_id


# here we define a tasks to send emails asynchonously - it's just a 
# celery wrapper for the function library defined in app.smtp.
@celery.task()
def restart_app_async():
    # if type == 'gunicorn': # we leave the door open here to support run methods other than gunicorn ...
    #     # here we try to restart gunicorn ... which might not be in use ...
    #     os.system("ps aux | grep gunicorn | awk '{ print $2 }' | xargs kill -HUP")
    #     # os.system('systemctl restart libreforms-gunicorn')

    with open ('log/restart.log','a') as f:
        f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")

    # else:
    #     import subprocess
    #     from werkzeug.serving import shutdown_server
    #     shutdown_server()  # Stop the current server instance
    #     subprocess.Popen(["flask", "run"])  # Start a new server instance using subprocess
