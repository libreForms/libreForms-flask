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

    class PIDFileHandler(logging.handlers.WatchedFileHandler)


    logging.handlers.RotatingFileHandler(file_path, 
        maxBytes=10*1024*1024, backupCount=10, encoding='utf-8')

# set_logger(file_path, module, pid=os.getpid(), log_level=logging.INFO)

# cleanup_stray_log_handlers(current_pid=None)

# aggregate_log_data(keyword:str=None, file_path:str='log/libreforms.log',
                        limit:int=None, pull_from:str='start')


"""

__name__ = "log_functions.py"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi",]
__version__ = "1.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import os, re, logging, logging.handlers

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
                        limit:int=None, pull_from:str='start'):

    with open(file_path, "r") as logfile:

        if keyword:

            TEMP = [x for x in logfile.readlines() if keyword in x]

            if limit and len(TEMP) > limit and pull_from=='start':
                return TEMP[:limit]
            elif limit and len(TEMP) > limit and pull_from=='end':
                return TEMP[-limit:]
            else:
                return TEMP

        else:
            return [x for x in logfile.readlines()]