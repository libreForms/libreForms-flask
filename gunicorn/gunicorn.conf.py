# gunicorn.conf.py: the Gunicorn configuration file for the libreForms web application
# References: 
# https://github.com/benoitc/gunicorn/issues/2136
# https://github.com/benoitc/gunicorn/blob/master/examples/example_config.py
# 

import os, re, secrets
from app.csv_files import init_tmp_fs
from app.display import display
from app.log_functions import cleanup_stray_log_handlers

# here we add pre-fork tasks that need to be handled prior to setting up concurrent sessions
def pre_fork(server, worker):

    if not os.path.exists('secret_key'):
        with open('secret_key', 'w') as f: 
            secret_key = secrets.token_urlsafe(16)
            f.write(secret_key)

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
        
        # here we append any additional fields described in the display.user_registration_fields variable
        if display['user_registration_fields']:
            for key, value in display['user_registration_fields'].items():

                # might eventually be worth adding support for unique fields...
                if value == str:
                    setattr(User, key, db.Column(db.String(1000)))
                    print (key, value)
                elif value == int:
                    setattr(User, key, db.Column(db.Integer))
                    print (key, value)
   
        
        db.create_all(app=app)

        # create default user if doesn't exist
        # solution from https://stackoverflow.com/a/39288652
        with app.app_context():
            if db.session.query(User).filter_by(username='libreforms').count() < 1:
                initial_user = User(id=1,
                                    username='libreforms', 
                                    active=1,
                                    group='admin',
                                    email=display['libreforms_user_email'] if display['libreforms_user_email'] and re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', display['libreforms_user_email']) else None,
                                    password='pbkdf2:sha256:260000$nQVWxd59E8lmkruy$13d8c4d408185ccc3549d3629be9cd57267a7d660abef389b3be70850e1bbfbf',
                                    created_date='2022-06-01 00:00:00',)
                db.session.add(initial_user)
                db.session.commit()
                db.session.close()


    # destructively initialize a tmp file system for the app 
    # init_tmp_fs(delete_first=True)



bind="0.0.0.0:8000"
workers = 3 
logpath='log'
errorlog = os.path.join(logpath, "gunicorn.error")
accesslog = os.path.join(logpath, "gunicorn.access")
loglevel = "debug"

