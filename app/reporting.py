"""
reporting.py: backend report management logic

This script anticipates that there will be two kinds of `report` 
expected from a system like this: (1) system-wide reports, which can
be configured in the app config by setting the `send_reports` variable, 
and (2) user-specific reports, which the blueprint below can allow
users to configure and manage. It implements this on top of its own 
database table and allows administrators to define complex behavior.


# Reports database


class Report(db.Model):
    __tablename__ = 'report'
    report_id = db.Column(db.Integer, primary_key=True) 
    user_id = db.Column(db.Integer) # we link the report to the user_id of the user who created to report
    name = db.Column(db.String(100))
    filters = db.Column(db.String(100))
    frequency = db.Column(db.String(100))
    active = db.Column(db.Boolean)
    timestamp = db.Column(db.Float)
    start_at = db.Column(db.Float) # this is an optional timestamp for when we'd like this report to go into effect
    end_at = db.Column(db.Float) # this is an optional timestamp for when we'd like this report to stop sending / expire (set `active` > False)


This largely responds to the anticipated user experience. We want 
users to be able to define some complex reort behavior in the UI,
presuming admins have enabled the correct display variables:

    `enable_reports` > None or True
    `system_reports` > None or Dict
    `user_defined_reports` > True or False


# Scheduling


# Methods

At this time, email reports are the only supported method, but 
feasibly other methods of report conveyance can be devised, see 
https://github.com/signebedi/libreForms/issues/73 for more information.


# reportManager()





"""

__name__ = "app.reporting"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


# frequency of emails
    # daily
    # hourly
    # weekly
    # monthly
    # annually 
# time range applied to, relative to the time of the report
    # start time
    # end time
    ### OR ###
    # last week
    # last month
    # last year
    # last hour
    # all time
    
# form applied to
    # select option from current forms you have view access for

# conditions of forms to be met
    # form field value conditionality, as a dict, used in a `pd.DataFrame.loc` statement

class reportManager():
    def __init__(self, send_reports=True):
        if not send_reports:
            return None

        # create a reports object and enroll the 
        # reports defined in the app config
        self.reports = {}
        for key,value in send_reports.items():
            self.reports[key] = value

        #### ELSE FIND SOME WAY TO HANDLE THIS, system level report
        # 'some_name_for_report': {
        #     'type': 'timed',
        #     'trigger': "* * * * *",
        #     'start_date': datetime.datetime.now(),
        #     'method': 'email',
        #     'query': None,
        # },

    def create(self, frequency, time, forms, conditions, db):
        pass # create a new report


    def modify():
        pass # modify an existing report

    def trigger(self, db, conditions:dict):
        pass

    def handler(self, db):
        pass