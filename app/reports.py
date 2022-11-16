from crontab import CronTab
from app import db, log, mailer, display


class reportHandler():
    def __init__(self, ) -> None:
        self.jobs = {}

    def set_cron_jobs(self, job_list=display['send_reports']):

        for key in job_list.keys():

            with CronTab(user=True) as cron:
                self.jobs[key] = cron.new(command='echo hello_world')
                self.jobs[key].setall(job_list[key]['trigger'])

            log.info(f'LIBREFORMS - wrote {key} report to CRON.')





