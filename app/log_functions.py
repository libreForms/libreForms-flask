import os, logging, logging.handlers

# we append the PID to the logfile, eee https://stackoverflow.com/a/48019592
class PIDFileHandler(logging.handlers.WatchedFileHandler):

    def __init__(self, filename, mode='a', encoding=None, delay=0):
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
    handler = logging.FileHandler(file_path, mode='a', encoding='utf-8')

    # we set a format for the log data
    formatter = logging.Formatter('%(asctime)s -  %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # we add the handler object to the list of log handlers
    log.handlers=[]
    log.addHandler(handler)

    # set log level as directed by end user
    log.setLevel(level=log_level)

    fh = PIDFileHandler(file_path)
    log.addHandler(fh)

    # we return the logging object
    return log



def clean_log():
    pass
