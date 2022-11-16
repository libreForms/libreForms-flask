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

# the current_pids should be a list of the current flask and/or gunicorn pids.
# this feature is implemented more effectively in gunicorn/gunicorn.conf.py, as
# this is able to clean up stray files before forking worker processes.
def cleanup_stray_log_handlers(current_pids=None):
    for log in os.listdir('log'):
        if re.fullmatch(r"libreforms-[0-9]+.log", log):
                os.remove (os.path.join('log', log))


# here we define a log aggregation tool that pulls lines of code as an array / list
# type to pass eg. to user profiles. The `limit` kwarg expects some int. The `pull_from`
# kwarg expects either `start` (pulls up to `limit` from the start of the list) or 'end' 
# (pulls up to `limit` from the end of the list). 
def aggregate_log_data(keyword=None, file_path='log/libreforms.log',limit=None, pull_from='start'):
    if keyword:
        with open(file_path, "r") as logfile:
            TEMP = [x for x in logfile.readlines() if keyword in x]

            if limit:
                if len(TEMP) > limit:
                    if pull_from=='start':
                        return TEMP[:limit]
                    elif pull_from=='end':
                        return TEMP[-limit:]
                    else:
                        return None
                else:
                    return TEMP 
            else:
                return TEMP
    else:
        return None