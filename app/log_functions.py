import logging

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

    # we return the logging object
    return log


def clean_log():
    pass
