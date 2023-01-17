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


from app import celery, create_app
from app.log_functions import set_logger
from app.reporting import reportManager

app = create_app()
app.app_context().push()

# we instantiate a log object that we'll use across the app
log = set_logger('log/libreforms-celery.log',__name__)


@celery.task()
def send_reports(reports, *args):
    # select all reports whose conditions are met under reportManager.trigger, 
    # and pass these to the execution reportManager.handler
    pass


@celery.task()
def celery_beat_logger():
    log.info('LIBREFORMS - celery just had another hearbeat.')


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):

    # periodically calls send_reports 
    # sender.add_periodic_task(3600.0, send_reports.s(reports), name='send reports periodically')
    sender.add_periodic_task(3600.0, celery_beat_logger.s(), name='log that celery beat is working')