from crontab import CronTab
from app import db, log, mailer, display


class reportHandler():
    def __init__(self) -> None:

        with CronTab(user=True) as cron:
            job = cron.new(command='echo hello_world')
            job.setall()
        print('cron.write() was just executed')





