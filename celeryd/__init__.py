""" 
celeryd/__init__.py: the init script for the libreForms celery app

This application has toyed with implementing celery at a number of
different points, to manage long-running background tasks & set up
scheduled tasks without needing to manage CRON. Because the web
application employs the Flask factory pattern, there are some 
complexities implementing celery - we borrow heavily from Miguel
Grinberg's approach to Celery using the factory pattern, described here:
https://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern

The celery app is created in app/__init__.py, but stored as a global 
variable. Then, we push the app context from within create_app().
Now, we'll import that here and treat this as the module - separate
from the main application context - from which celery will be 
invoked by systemd. For awhile, we attempted to run this script
from within app/__init__.py, but this approach proved to be 
insufficiently robust because, it seems, the celery object was
being accessed from systemd without passing the app context,
as create app was not being run.

One area that we still need to confirm: whether to create the celery
tasks within the application context, or outside it. Our initial hunch 
is that we should write these tasks within the app context, which we 
access here, but we'll continue to troubleshoot as this approach
inevitably evolves.

Even so, because of potential module name confusion (too many objects / 
modules can be access using the phrase `app.celery`), we opted to place
this script in the application working directory.

"""

__name__ = "celeryd"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


from app import celery, create_app, log, mailer, mongodb
from app.reporting import reportManager

app = create_app()
app.app_context().push()


# here we define a tasks to send emails asynchonously - it's just a 
# celery wrapper for the function library defined in app.smtp.
@celery.task()
def send_mail_async(subject, content, to_address, cc_address_list=[], logfile=log):
    mailer.send_mail(   subject=subject, content=content, to_address=to_address, 
                        cc_address_list=cc_address_list, logfile=log)


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

# create a reportManager object for sending reports that have come due
reports = reportManager()

@celery.task()
def send_reports(reports, *args):
    # select all reports whose conditions are met under reportManager.trigger, 
    # and pass these to the execution reportManager.handler
    pass

@celery.task()
def celery_beat_logger():
    log.info('LIBREFORMS - celery just had another hearbeat.')
    return 'LIBREFORMS - celery just had another hearbeat.'


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):

    # periodically calls send_reports 
    sender.add_periodic_task(3600.0, send_reports.s(reports.trigger()), name='send reports periodically')

    # periodically conduct a heartbeat check
    sender.add_periodic_task(3600.0, celery_beat_logger.s(), name='log that celery beat is working')