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
__version__ = "1.3.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


from app import celery, create_app, log, mailer, mongodb
from app.reporting import reportManager
from celeryd.tasks import send_mail_async, write_document_to_collection_async, send_report_async

app = create_app(celery_app=True)
app.app_context().push()

# create a reportManager object for sending reports that have come due
reports = reportManager()



@celery.task()
def celery_beat_logger():
    log.info('LIBREFORMS - celery just had another hearbeat.')
    return 'LIBREFORMS - celery just had another hearbeat.'


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):

    # periodically calls send_reports 
    # sender.add_periodic_task(3600.0, send_report_async.s(reports.trigger()), name='send reports periodically')

    # periodically conduct a heartbeat check
    sender.add_periodic_task(3600.0, celery_beat_logger.s(), name='log that celery beat is working')