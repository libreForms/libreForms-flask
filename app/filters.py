
"""
filters.py: managing filters and triggers primary for sending reports

## Reports

This script anticipates that there will be two kinds of `report` 
expected from a system like this: (1) system-wide reports, which can
be configured in the app config by setting the `send_reports` variable, 
and (2) user-specific reports, which the blueprint below can allow
users to configure and manage. It implements this on top of its own 
database table and allows administrators to define complex behavior.

The reports table is defined in app.models.

This largely responds to the anticipated user experience. We want 
users to be able to define some complex reort behavior in the UI,
presuming admins have enabled the correct display variables:

    `enable_reports` > None or True
    `system_reports` > None or Dict
    `user_defined_reports` > True or False

There are a couple ways to deal with the issue of send intervals, which we discuss
further at https://github.com/libreForms/libreForms-flask/issues/218.
frequency of emails
    daily: 3600
    hourly: 86400
    weekly: 604800
    monthly: 2592000
    annually: 31536000 
    manual: NO TIME ASSIGNED

At this time, email reports are the only supported method, but 
feasibly other methods of report conveyance can be devised, see 
https://github.com/signebedi/libreForms/issues/73 for more information.


Report backend references:
1. https://github.com/libreForms/libreForms-flask/issues/191

Filter references:
1. https://github.com/libreForms/libreForms-flask/issues/204 (comparison operators)
2. https://github.com/libreForms/libreForms-flask/issues/213 (identity & membership operators)

"""

__name__ = "app.filters"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.3.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import libreforms
from app.mongo import mongodb
import pandas as pd

##########################
# Filters - conditions used to assess forms for inclusion in reports
##########################

# these are the operators supported in text, borrowed shamelessly from
# https://stackoverflow.com/a/45151961/13301284. 
def get_operators():
    return {
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
        '>=': lambda a, b: a >= b,
        '<=': lambda a, b: a <= b,
        '>': lambda a, b: a > b,
        '<': lambda a, b: a < b,
        # 'in': lambda a, b: a in b,
    }


# this function takes a string, and processes it into 
# filters / conditions
def preprocess_text_filters(string):
    return [x.strip() for x in string.split(',')]


# here we actually assess the truthfulness of a set of 
# filters; this is the method that we should call when
# validating a string stored as a report's filters.
# Worried this is a little bit computationally expensive..
def validate_filters(s):

    STRINGS = preprocess_text_filters(s)

    for string in STRINGS:
        operand1, comparison, operand2 = string.split()
        COMPARISONS = get_operators()

        # if the attempted comparison isn't supported, then
        # we fail
        if comparison not in COMPARISONS:
            return False

        # if any of the conditions assess false, then return False
        if not COMPARISONS[comparison](operand1, operand2):
            return False
        
    # if the above passes, then return True
    return True


def lint_filters(s, *args, **kwargs):

    STRINGS = preprocess_text_filters(s)

    for string in STRINGS:
        try:
            operand1, comparison, operand2 = string.split()
        except:
            return False
        COMPARISONS = get_operators()

        if comparison not in COMPARISONS:
            return False

    return True


def dummy_test(STRINGS = ['my_city_name == my_city_name','6001 >= 6005', 'my_city_name == your_city_name', '13 != 14', '1 < 4', 'vary in [varynice,telluride]']):

    for string in STRINGS:
        operand1, comparison, operand2 = string.split()
        COMPARISONS = get_operators()
        if comparison in COMPARISONS:
                print(string, COMPARISONS[comparison](operand1, operand2))
        else:
                print(string, "Unknown comparison")

##########################
# Reports - triggers and logic for initiating and sending reports
##########################


# this function will get a list of all current forms, and then create a dictionary 
# where each key corresponds to these form names, and each value is a dataframe 
# of all the submissions for that form.
def get_map_of_form_data(*args,**kwargs):
    
    # we start by initializing an empty dictionary
    TEMP = {}

    for form in libreforms.forms:
        TEMP[form] = mongodb.new_read_documents_from_collection(form)

        # use *args to drop fields with value if the dataframe is not empty;
        # for example, if you run get_map_of_form_data('Metadata','Journal'),
        # you will receive back a dictionary of dataframes, each of which will
        # have their 'Metadata' and 'Journal' fields dropped if they exist.
        if isinstance(TEMP[form], pd.DataFrame):
            TEMP[form].drop(columns=[x for x in args if x in TEMP[form].columns], inplace=True)

    return TEMP

def select_reports_by_time():

    # we map each human-readable `frequency` option to its corresponding interval
    # in seconds. Should we remove this from the application code, and simply add
    # as a field in the Report data model? That might save some complexity here...
    time_map = {
        'hourly': 3600,
        'daily': 86400,
        'weekly': 604800,
        'monthly': 2592000, # this we map to 30 days, though this may have problems...
        'annually': 31536000,
    }


# this is the synchronous function that will be used to send reports. It will be wrapped
# by a corresponding asynchronous celery function in celeryd.
def send_eligible_reports():
    pass

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
