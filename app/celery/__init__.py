""" 
celery/__init__.py: the init script for the libreForms celery app

This application has toyed with implementing celery at a number of
different points, to manage long-running background tasks & set up
scheduled tasks without needing to manage CRON. Because the web
application employs the Flask factory pattern, there are some 
complexities implementing celery - we borrow heavily from Miguel
Grinberg's approach to Celery using the factory pattern, described here:
https://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern


"""

__name__ = "celery"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"
