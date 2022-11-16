from crontab import CronTab
from croniter import croniter
from datetime import datetime
from app import db, log, mailer, display, tempfile_path


class reportHandler():
    def __init__(self) -> None:

        # we create a local key mapping that will each correspond to a 
        # event handling object
        self.jobs = {}

    # this code is a bit messy. We start by writing timed reports from the
    # 'send_reports' display configuration to the system crontab  
    def set_cron_jobs(self, job_list=display['send_reports']):

        for key in job_list.keys():

            if job_list[key]['type'] == 'timed':

                # with CronTab(user=True) as cron:
                    # self.jobs[key] = cron.new(command='echo hello_world')
                    # self.jobs[key].setall(job_list[key]['trigger'])

                log.info(f'LIBREFORMS - wrote {key} report to CRON.')

            else:
                self.jobs[key] = None




