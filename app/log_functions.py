""" 
log_functions.py: a collection of log operations for a multi worker Flask app

This script defines a set of operations to create, manage, and access log
information for a Flask application. It is redundant with a few other 
features, including the Gunicorn log, the behavior of which is defined in 
gunicorn/gunicorn.conf.py. It leverages Python's standard logging library 
and employs various log handlers to ensure the log files generated conform
to the requirements of the application - adding features that account for
log rotation and a multi-process application.

# Log Handlers

We've added some log handlers to deal with a few of the application's 
underlying quirks. 

    1. class PIDFileHandler(logging.handlers.WatchedFileHandler)

        Gunicorn handles its multiworker approach fine at its own level by 
        creating a gunicorn access and error logs, see gunicorn/gunicorn.conf.py. 
        But when we want to handle multiple processes at the application's level,
        we create PID-linked logfiles to manage potential concurrent-write issues.

        You can see more discussion about this in the application's Github
        issues https://github.com/signebedi/libreForms/issues/26.


    2. logging.handlers.RotatingFileHandler(file_path, 
        maxBytes=10*1024*1024, backupCount=10, encoding='utf-8')

        This file handler seeks to set up some log rotation, where the 
        max log file size is set to 10MiB.


# set_logger(file_path, module, pid=os.getpid(), log_level=logging.INFO)

Create a logging object for the current PID

In the base application, this method is run at app startup to create an
object called `log` for logging within the current PID, see app/__init__.py.
Setting the `file_path` to 'log/libreforms.log', the `module` to __name__,
and `pid` simply gets the current PID. The `log_level` defaults to INFO.


# cleanup_stray_log_handlers(current_pid=None)

Remove stray, obsolete process-mapped logfiles

In the base application, this method is run at app startup to remove stray
logfiles generated previously by PIDFileHandler, see Log Handlers section 
above. This method is implemented in app/__init__.py, passing the current
PID to tell the method not to delete the logfile for the current app instance.
It might not be necessary to pass the current PID if we run this before 
instantiating a logfile for the current app instance...

This is also run in gunicorn/gunicorn.conf.py but, because it is run before 
Gunicorn forks into multiple worker processes, we don't need to pass the PID.

You can see more discussion about this method in the application's Github
issues https://github.com/signebedi/libreForms/issues/32.


# aggregate_log_data(keyword:str=None, file_path:str='log/libreforms.log',
                        limit:int=None, pull_from:str='start')

Select and return from the logfile using an optional string keyword

In the base application, this method is used to generate a list of log
entries for a given user in their profile, see app/auth.py. The `limit`
parameter takes an integer and selects only that number of entries; the
`pull_from` field takes either 'start' or 'end', and is used when `limit`
is passed to decide whether to select the log entries from the start of 
the logfile or the end. If no `keyword` specified, return the entire log.
To avoid spillage, we pass a bool option `exclude_pid` while strips out 
PID numbers from each log entry by default

Further, the base web application toggles the visibility of user logs on
their profiles by setting the `enable_user_profile_log_aggregation` config
to True. 

In the future, we should consider handling (1) rotated log files (eg. still 
including them), (2) adding support for pagination in the user profile, and 
(3) potentially adding a search bar for a user's logs.


You can see more discussion about this method in the application's Github
issues https://github.com/signebedi/libreForms/issues/35.

"""

__name__ = "app.log_functions"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi",]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import os, re, logging, logging.handlers
from flask import current_app

# we append the PID to the logfile 
class PIDFileHandler(logging.handlers.WatchedFileHandler):

    def __init__(self, filename, mode='a', encoding='utf-8', delay=0):
        filename = self._append_pid_to_filename(filename)
        super(PIDFileHandler, self).__init__(filename, mode, encoding, delay)

    def _append_pid_to_filename(self, filename):
        pid = os.getpid()
        path, extension = os.path.splitext(filename)
        return '{0}-{1}{2}'.format(path, pid, extension)

def set_logger(file_path, module, pid=os.getpid(), log_level=logging.INFO):

    # we make sure the log file_path exists
    with open(file_path, "a") as logfile:
        logfile.write("")

    # we instantiate the logging object
    log = logging.getLogger(module)

    # we create a file handler object
    # handler = logging.FileHandler(file_path, mode='a', encoding='utf-8')

    # we set a format for the log data
    # formatter = logging.Formatter('%(asctime)s -  %(levelname)s - %(message)s')
    # handler.setFormatter(formatter)

    # we add the handler object to the list of log handlers
    # log.handlers=[]
    # log.addHandler(handler)

    # set log level as directed by end user
    # log.setLevel(level=log_level)

    # set a log rotator the will create up to 10 log files of 10mb (max size) each
    # rotation_handler = logging.handlers.RotatingFileHandler(f'{file_path}a', mode='a', maxBytes=10*1024*1024, backupCount=10)
    # rotation_handler = logging.handlers.RotatingFileHandler(f'{file_path}a', mode='a', maxBytes=10, backupCount=10)
    # log.addHandler(rotation_handler)

    # add the concurrency file handlers
    # fh = PIDFileHandler(file_path)
    # log.addHandler(fh)

    logging.basicConfig(
        handlers= [
            logging.handlers.RotatingFileHandler(file_path, maxBytes=10*1024*1024, backupCount=10, encoding='utf-8'), 
            PIDFileHandler(file_path),
        ],
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s - "+str(pid),
        datefmt='%Y-%m-%d %H:%M:%S',
        )

    # we return the logging object
    return log

# the current_pids should be the current flask and/or gunicorn pids.
# this feature is implemented effectively in gunicorn/gunicorn.conf.py, as
# this is able to clean up stray files before forking worker processes.
def cleanup_stray_log_handlers(current_pid=None):
    for log in os.listdir('log'):
        if re.fullmatch(r"libreforms-[0-9]+.log", log):
            if not current_pid or str(current_pid) not in log:
                os.remove (os.path.join('log', log))


# here we define a log aggregation tool that pulls lines of code as an array / list
# type to pass eg. to user profiles. The `limit` kwarg expects some int. The `pull_from`
# kwarg expects either `start` (pulls up to `limit` from the start of the list) or 'end' 
# (pulls up to `limit` from the end of the list). If no keyword specified, return the 
# entire log as a list.
def aggregate_log_data(keyword:str=None, file_path:str='log/libreforms.log',
                        limit:int=None, pull_from:str='start', exclude_pid:bool=True):

    with open(file_path, "r") as logfile:

        if keyword:

            TEMP = [x for x in logfile.readlines() if keyword in x]

            # added this to strip out PIDs if we pass the `exclude_pid` option
            TEMP = [" -".join(x.split(' -')[:-1]) for x in TEMP] if exclude_pid else TEMP 

            if limit and len(TEMP) > limit and pull_from=='start':
                return TEMP[:limit]
            elif limit and len(TEMP) > limit and pull_from=='end':
                return TEMP[-limit:]
            else:
                return TEMP

        else:
            # added this to strip out PIDs if we pass the `exclude_pid` option
            return [" -".join(x.split(' -')[:-1]) for x in logfile.readlines()] if exclude_pid else [x for x in logfile.readlines()]