import os, logging, logging.handlers

# we append the PID to the logfile 
class PIDFileHandler(logging.handlers.WatchedFileHandler):

    def __init__(self, filename, mode='a', encoding='utf-8', delay=0):
        filename = self._append_pid_to_filename(filename)
        super(PIDFileHandler, self).__init__(filename, mode, encoding, delay)

    def _append_pid_to_filename(self, filename):
        pid = os.getpid()
        path, extension = os.path.splitext(filename)
        return '{0}-{1}{2}'.format(path, pid, extension)

def set_logger(file_path, module, log_level=logging.INFO):

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
        format="%(asctime)s -  %(levelname)s - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        )

    # we return the logging object
    return log




def clean_log():
    pass
