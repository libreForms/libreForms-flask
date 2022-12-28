""" 
gunicorn.conf.py: the Gunicorn configuration file for the libreForms web application


References: 
    1. https://github.com/benoitc/gunicorn/issues/2136
    2. https://github.com/benoitc/gunicorn/blob/master/examples/example_config.py

"""

__name__ = "gunicorn.gunicorn.conf.py"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


import os, re, secrets
from app.config import config, collect_secrets_from_file
from app.log_functions import cleanup_stray_log_handlers
from app.certification import generate_symmetric_key

# here we add pre-fork tasks that need to be handled prior to setting up concurrent sessions
def pre_fork(server, worker):

    # we create the secret key for the application if it doesn't exist
    if not os.path.exists('secret_key'):
        with open('secret_key', 'w') as f: 
            secret_key = secrets.token_urlsafe(16)
            f.write(secret_key)

    # this approach from https://github.com/signebedi/libreForms/issues/148 allows us
    # to generate secret_key files pre-fork
    for filename in ['secret_key', 'signature_key', 'approval_key', 'disapproval_key']:
        collect_secrets_from_file(filename)



    # cleanup any stray log files prior to forking the work processes
    if not os.path.exists ("log/"):
        os.mkdir('log/')
    else:
        # if the log path exists, let's clean up old log handlers
        cleanup_stray_log_handlers()

    # create the app database if it doesn't exist
    if not os.path.exists(os.path.join('instance','app.sqlite')):
        from app import create_app    
        from app.models import User
        from flask_sqlalchemy import SQLAlchemy

        # create the database if one doesn't exist
        db = SQLAlchemy()

        app=create_app()

        # initialize the database
        db.init_app(app=app)     
        
        # here we append any additional fields described in the user_registration_fields variable
        if config['user_registration_fields']:
            for key, value in config['user_registration_fields'].items():

                # might eventually be worth adding support for unique fields...
                if value == str:
                    setattr(User, key, db.Column(db.String(1000)))
                    print (key, value)
                elif value == int:
                    setattr(User, key, db.Column(db.Integer))
                    print (key, value)
   

        # create database and default user if doesn't exist
        # solution from https://stackoverflow.com/a/39288652
        with app.app_context():
            
            db.create_all()

            if db.session.query(User).filter_by(username='libreforms').count() < 1:
                initial_user = User(id=1,
                                    username='libreforms', 
                                    active=1,
                                    theme='dark' if config['dark_mode'] else 'light',
                                    group='admin',
                                    certificate=generate_symmetric_key(),
                                    email=config['libreforms_user_email'] if config['libreforms_user_email'] and re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', config['libreforms_user_email']) else None,
                                    password='pbkdf2:sha256:260000$nQVWxd59E8lmkruy$13d8c4d408185ccc3549d3629be9cd57267a7d660abef389b3be70850e1bbfbf',
                                    created_date='2022-06-01 00:00:00',)
                db.session.add(initial_user)
                db.session.commit()
                db.session.close()




bind="0.0.0.0:8000"
workers = 3 
logpath='log'
errorlog = os.path.join(logpath, "gunicorn.error")
accesslog = os.path.join(logpath, "gunicorn.access")
loglevel = "debug"

