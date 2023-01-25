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
__version__ = "1.3.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from app import celery, log, mailer, mongodb, create_app
from flask import current_app

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

# @celery.task()
# def elasticsearch_index_document(body, id, client, index="submissions"):
#         # app = create_app(celery_app=True)

#         # with app.app_context():
#         #     app.elasticsearch.index(id, body, index=index)
#         client.index(id, body, index=index)

#         return True
    # expects data to be formulated as follows:
    # data = json.dumps({
    #     'form_name': form_name,
    #     'title': document_id,
    #     'url': url_for('submissions.render_document', form_name=form_name, document_id=document_id), 
    #     'content': render_template('app/index_friendly_submissions.html', form_name=form_name, submission=parsed_args),
    # })

    # try:
    #     app.elasticsearch.index(id, body, index=index)
    #     return True
    # except Exception as e:
    #     return e


@celery.task()
def send_report_async(report=None, *args):
    # select all reports whose conditions are met under reportManager.trigger, 
    # and pass these to the execution reportManager.handler
    return True