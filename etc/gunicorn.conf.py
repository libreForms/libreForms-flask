""" 
gunicorn.conf.py: the Gunicorn configuration file for the libreForms web application


References: 
    1. https://github.com/benoitc/gunicorn/issues/2136
    2. https://github.com/benoitc/gunicorn/blob/master/examples/example_config.py

"""

__name__ = "etc.gunicorn.conf.py"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.6.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


import os, re, secrets
from app.config import config as appconfig, collect_secrets_from_file
from app.log_functions import cleanup_stray_log_handlers
from app.certification import generate_symmetric_key

# here we add pre-fork tasks that need to be handled prior to setting up concurrent sessions
def pre_fork(server, worker):

    # this approach from https://github.com/signebedi/libreForms/issues/148 allows us
    # to generate secret_key files pre-fork
    for filename in ['secret_key', 'signature_key', 'approval_key', 'disapproval_key']:
        collect_secrets_from_file(filename)
        # print (collect_secrets_from_file(filename))

    # cleanup any stray log files prior to forking the work processes
    if not os.path.exists ("log/"):
        os.mkdir('log/')
    else:
        # if the log path exists, let's clean up old log handlers
        cleanup_stray_log_handlers()
        # print('cleanup')

    # create the app database if it doesn't exist
    if not os.path.exists(os.path.join('instance','app.sqlite')):
        from app import create_app    
        from app.models import User, db

        app=create_app()
        # print('create app')

        # initialize the database
        db.init_app(app=app)
        # print('init app')
        
        # here we append any additional fields described in the user_registration_fields variable
        for key, value in appconfig['user_registration_fields'].items():

            # might eventually be worth adding support for unique fields...
            if value == str:
                setattr(User, key, db.Column(db.String(1000)))
                # print (key, value)
            elif value == int:
                setattr(User, key, db.Column(db.Integer))
                # print (key, value)
   

        # create database and default user if doesn't exist
        # solution from https://stackoverflow.com/a/39288652
        with app.app_context():
            
            db.create_all()

            if db.session.query(User).filter_by(username='libreforms').count() < 1:
                initial_user = User(id=1,
                                    username='libreforms', 
                                    active=1,
                                    theme='dark' if appconfig['dark_mode'] else 'light',
                                    group=appconfig['admin_group'],
                                    certificate=generate_symmetric_key(),
                                    email=appconfig['libreforms_user_email'] if appconfig['libreforms_user_email'] and re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', appconfig['libreforms_user_email']) else None,
                                    password='pbkdf2:sha256:260000$nQVWxd59E8lmkruy$13d8c4d408185ccc3549d3629be9cd57267a7d660abef389b3be70850e1bbfbf',
                                    created_date='2022-06-01 00:00:00',)
                db.session.add(initial_user)
                db.session.commit()
                db.session.close()

            # print('db done')




bind="0.0.0.0:8000"
workers = 3 
logpath='log'
errorlog = os.path.join(logpath, "gunicorn.error")
accesslog = os.path.join(logpath, "gunicorn.access")
loglevel = "debug"

