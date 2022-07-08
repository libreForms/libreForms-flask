# gunicorn.conf.py: the Gunicorn configuration file for the libreForms web application
# References: 
# https://github.com/benoitc/gunicorn/issues/2136
# https://github.com/benoitc/gunicorn/blob/master/examples/example_config.py
# 

import os, re

def pre_fork(server, worker):

    # cleanup any stray log files prior to forking hte work processes
    for log in os.listdir(logpath):
        if re.fullmatch(r"libreforms-[0-9]+.log", log):
                os.remove (os.path.join(logpath, log))

bind="0.0.0.0:8000"
workers = 3 
logpath='/opt/libreForms/log'
errorlog = os.path.join(logpath, "gunicorn.error")
accesslog = os.path.join(logpath, "gunicorn.access")
loglevel = "debug"

