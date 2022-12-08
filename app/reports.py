""" 
tables.py: generate email and other forms of reports



"""

__name__ = "app.reports"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.0.2"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from crontab import CronTab
from croniter import croniter
from datetime import datetime
from app import log, mailer, display, tempfile_path


# import flask-related packages
from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user
from markupsafe import Markup

# import custom packages from the current repository
import libreforms as libreforms
from app.auth import login_required
from app import display, log, mongodb

# and finally, import other packages
import os
import pandas as pd

bp = Blueprint('reports', __name__, url_prefix='/reports')



# class reportHandler():
#     def __init__(self) -> None:

#         # we create a local key mapping that will each correspond to a 
#         # event handling object
#         self.jobs = {}

#     # this code is a bit messy. We start by writing timed reports from the
#     # 'send_reports' display configuration to the system crontab  
#     def set_cron_jobs(self, job_list = display['send_reports']):

#         for key in job_list.keys():

#             if job_list[key]['type'] == 'timed':

#                 # base = job_list[key]['start_date'] if job_list[key]['start_date'] else datetime.datetime.now()
#                 # iter = croniter(job_list[key]['trigger'], base)

#                 # with CronTab(user=True) as cron:
#                 #     self.jobs[key] = cron.new(command='echo hello_world >> /home/sig/Code/libreForms/log/temp.log')
#                 #     self.jobs[key].setall(job_list[key]['trigger'])
#                 #     self.jobs[key].schedule(date_from = base)
#                     # self.jobs[key].run_scheduler(iter)

#                 log.info(f'LIBREFORMS - wrote {key} report to CRON.')

#             else:
#                 self.jobs[key] = None






# base = datetime(2010, 1, 25, 4, 46)
# iter = croniter('*/5 * * * *', base)  # every 5 minutes
# print(iter.get_next(datetime))   # 2010-01-25 04:50:00
# print(iter.get_next(datetime))   # 2010-01-25 04:55:00
# print(iter.get_next(datetime))   # 2010-01-25 05:00:00
# iter = croniter('2 4 * * mon,fri', base)  # 04:02 on every Monday and Friday
# print(iter.get_next(datetime))   # 2010-01-26 04:02:00
# print(iter.get_next(datetime))   # 2010-01-30 04:02:00
# print(iter.get_next(datetime))   # 2010-02-02 04:02:00
# iter = croniter('2 4 1 * wed', base)  # 04:02 on every Wednesday OR on 1st day of month
# print(iter.get_next(datetime))   # 2010-01-27 04:02:00
# print(iter.get_next(datetime))   # 2010-02-01 04:02:00
# print(iter.get_next(datetime))   # 2010-02-03 04:02:00
# iter = croniter('2 4 1 * wed', base, day_or=False)  # 04:02 on every 1st day of the month if it is a Wednesday
# print(iter.get_next(datetime))   # 2010-09-01 04:02:00
# print(iter.get_next(datetime))   # 2010-12-01 04:02:00
# print(iter.get_next(datetime))   # 2011-06-01 04:02:00
# iter = croniter('0 0 * * sat#1,sun#2', base)  # 1st Saturday, and 2nd Sunday of the month
# print(iter.get_next(datetime))   # 2010-02-06 00:00:00
# iter = croniter('0 0 * * 5#3,L5', base)  # 3rd and last Friday of the month
# print(iter.get_next(datetime))   # 2010-01-29 00:00:00
# print(iter.get_next(datetime))   # 2010-02-19 00:00:00