import os, re

def on_starting(logpath='/opt/libreforms/log'):
    for log in os.listdir(logpath):
        if re.fullmatch(r"libreforms-[0-9]+.log", log):
                os.remove (os.path.join(logpath, log))

workers = 3 
errorlog = "/opt/libreForms/log/gunicorn.error"
accesslog = "/opt/libreForms/log/gunicorn.access" 
loglevel = "debug"

# Server Hooks
on_starting = on_starting()