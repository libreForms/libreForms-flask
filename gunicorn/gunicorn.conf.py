# gunicorn.conf.py: the Gunicorn configuration file for the libreForms web application
# References: 
# https://github.com/benoitc/gunicorn/issues/2136
# https://github.com/benoitc/gunicorn/blob/master/examples/example_config.py
# 

import os, re
from app.csv_files import init_tmp_fs

# here we add pre-fork tasks that need to be handled prior to setting up concurrent sessions
def pre_fork(server, worker):

    # cleanup any stray log files prior to forking hte work processes
    for log in os.listdir(logpath):
        if re.fullmatch(r"libreforms-[0-9]+.log", log):
                os.remove (os.path.join(logpath, log))

    # create the database if it doesn't exist
    if not os.path.exists(os.path.join('instance','app.sqlite')):

        # create the user database if one doesn't exist
        from app import create_app    
        from app.models import User
        from flask_sqlalchemy import SQLAlchemy
        db = SQLAlchemy()

        app=create_app()

        # initialize the database
        db.init_app(app=app)        
        
        db.create_all(app=app)

        # create default user if doesn't exist
        # solution from https://stackoverflow.com/a/39288652
        with app.app_context():
            if db.session.query(User).filter_by(username='libreforms').count() < 1:
                initial_user = User(id=1,
                                    username='libreforms', 
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

