"""
reporting.py: backend report management logic

This script anticipates that there will be two kinds of `report` 
expected from a system like this: (1) system-wide reports, which can
be configured in the app config by setting the `send_reports` variable, 
and (2) user-specific reports, which the blueprint below can allow
users to configure and manage. It implements this on top of its own 
database table and allows administrators to define complex behavior.


# Reports table

The reports table is defined in app.models.

This largely responds to the anticipated user experience. We want 
users to be able to define some complex reort behavior in the UI,
presuming admins have enabled the correct display variables:

    `enable_reports` > None or True
    `system_reports` > None or Dict
    `user_defined_reports` > True or False


# Scheduling / Send Intervals

There are a couple ways to deal with the issue of send intervals, which we discuss
further at https://github.com/libreForms/libreForms-flask/issues/218.
frequency of emails
    daily
    hourly
    weekly
    monthly
    annually 
    manual
time range applied to, relative to the time of the report
    start time
    end time
    ### OR ###
    last week
    last month
    last year
    last hour
    all time


# Methods

At this time, email reports are the only supported method, but 
feasibly other methods of report conveyance can be devised, see 
https://github.com/signebedi/libreForms/issues/73 for more information.


# reportManager()





"""

__name__ = "app.reporting"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.3.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

    
time_map = {
    'hourly': 3600,
    'daily': 86400,
    'weekly': 604800,
    'monthly': 2592000, # this we map to 30 days, though this may have problems...
    'annually': 31536000,
}
# form applied to
    # select option from current forms you have view access for

# conditions of forms to be met
    # form field value conditionality, as a dict, used in a `pd.DataFrame.loc` statement

# class reportManager():
#     def __init__(self, send_reports=True):
#         if not send_reports:
#             return None

#         # create a reports object and enroll the 
#         # reports defined in the app config
#         self.reports = {}
        
#         # for key,value in send_reports.items():
#         #     self.reports[key] = value

#         #### ELSE FIND SOME WAY TO HANDLE THIS, system level report
#         # 'some_name_for_report': {
#         #     'type': 'timed',
#         #     'trigger': "* * * * *",
#         #     'start_date': datetime.datetime.now(),
#         #     'method': 'email',
#         #     'query': None,
#         # },

#     def create(self, frequency, time, forms, conditions, db):
#         return None # create a new report


#     def modify():
#         return None # modify an existing report

#     def trigger(self, db, conditions:dict):
#         return None

#     def handler(self, db):
#         return None
