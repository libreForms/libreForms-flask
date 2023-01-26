
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


from flask import url_for

from app.mongo import mongodb
from app.config import config
import libreforms

from datetime import datetime
import pandas as pd
import re

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
# def preprocess_text_filters(string):
#     return [x.strip() for x in string.split(',')]


# here we actually assess the truthfulness of a set of 
# filters; this is the method that we should call when
# validating a string stored as a report's filters.
# Worried this is a little bit computationally expensive..
# def validate_filters(s):

#     STRINGS = preprocess_text_filters(s)

#     for string in STRINGS:
#         operand1, comparison, operand2 = string.split()
#         COMPARISONS = get_operators()

#         # if the attempted comparison isn't supported, then
#         # we fail
#         if comparison not in COMPARISONS:
#             return False

#         # if any of the conditions assess false, then return False
#         if not COMPARISONS[comparison](operand1, operand2):
#             return False
        
#     # if the above passes, then return True
#     return True


def lint_filters(s, *args, **kwargs):

    try:
        STRINGS = new_preprocess_text_filters(s)
    except:
        return False

    for string in STRINGS:
        try:
            operand1, comparison, operand2 = string.split()
        except:
            return False
        COMPARISONS = get_operators()

        if comparison not in COMPARISONS:
            return False

    return True


# def dummy_test(STRINGS = ['my_city_name == my_city_name','6001 >= 6005', 'my_city_name == your_city_name', '13 != 14', '1 < 4', 'vary in [varynice,telluride]']):

#     for string in STRINGS:
#         operand1, comparison, operand2 = string.split()
#         COMPARISONS = get_operators()
#         if comparison in COMPARISONS:
#                 print(string, COMPARISONS[comparison](operand1, operand2))
#         else:
#                 print(string, "Unknown comparison")


def new_preprocess_text_filters(s = "$(a == '7'),$(c == 'pig'),"):

    # start by stripping trailing / leading whitespace
    s = s.strip()

    # drop any trailing commas
    s = s[:-1] if s[-1] == ',' else s

    # assert that the string ends with a parenthesis
    assert (s[-1] == ')' and not s[-2:-1] in ['))', ',)'])

    # this one might take some explaining. In essence, we are assuming 
    # the previous check passed (and that therefore the string ends with 
    # a parenthetical). Then, we take a substring of all characters except
    # the very last character. We then assert that there are no other trailing
    # parentheses found later than the last leading parenthesis. Obviously,
    # if there are fewer than two trailing parentheses, then this logic won't
    # work ... so we create an exception for those cases. Previously, we used
    # the following assertion, but this did not work when there are multiple
    # parenthetical statements:
        # assert (s[:-1].find('(') > s[:-1].find(')') or s.count(')') < 2)
    # However, we realized that if we split on the trailing parentheticals:
        # ['(' in x for x in s[:-1].split(')')]
    # that we could make the assertion statement work, see below
    assert (all(['$(' in x for x in s[:-1].split(')')] or s.count(')') < 2))

    # we use regular expressions to group each parenthetical statement, see
    # https://stackoverflow.com/a/29438510/13301284.
    STRINGS = [''.join(tup.strip()) for tup in re.findall(r'\$\((.+?)\)', s)]

    # now we need to handle types, which we support strings and numbers.


    return STRINGS


def generate_pandas_query_string(STRINGS):
    return " & ".join(STRINGS)



##########################
# Reports - triggers and logic for initiating and sending reports
##########################

# this function will get a list of all current forms, and then create a dictionary 
# where each key corresponds to these form names, and each value is a dataframe 
# of all the submissions for that form.
def get_map_of_form_data(*args, add_hyperlink=False):
    
    # we start by initializing an empty dictionary
    TEMP = {}

    for form in libreforms.forms:
        TEMP[form] = mongodb.new_read_documents_from_collection(form)


        # use *args to drop fields with value if the dataframe is not empty;
        # for example, if you run get_map_of_form_data('Metadata','Journal'),
        # you will receive back a dictionary of dataframes, each of which will
        # have their 'Metadata' and 'Journal' fields dropped if they exist.
        if isinstance(TEMP[form], pd.DataFrame):

            # we add a hyperlink field if it's been requested
            if add_hyperlink:
                TEMP[form]['Hyperlink'] = TEMP[form].apply(lambda row: config['domain']+url_for('submissions.render_document', form_name=form, document_id=row['_id']), axis=1)

            TEMP[form].drop(columns=[x for x in args if x in TEMP[form].columns], inplace=True)

    return TEMP

# selects user-generated reports that have 'come due', that is, have reached the the time
# based trigger to be sent out.
def select_user_reports_by_time():

    # import the database instance
    from app import db
    from app.models import Report

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

    # read in report data
    df = pd.read_sql_table(Report.__tablename__, con=db.engine.connect())

    # drop where inactive is set to False
    df = df[df['active']!=1]

    # drop where frequency is set to 'manual'
    df = df[df['frequency']!='manual']

    # drop where there is an end_at specified, and it has passed
    df = df[(df['end_at']!=0) | (df['end_at']>=datetime.timestamp(datetime.now()))]

    # drop where there is an start_at specified, and it has not yet arrived
    df = df[(df['start_at']!=0) | (df['start_at']<=datetime.timestamp(datetime.now()))]

    # here we do some (rather inefficient, admittedly; we should find a way
    # to optimize this if performance becomes an issue). First, we map the timestamps
    # to the human readable `frequency` field.
    df['int_frequency'] = df.apply(lambda row: time_map[row['frequency']], axis=1)

    # then, we calculate how long it has been since the report was last run
    df['time_since_last_run'] = df['last_run_at'] - datetime.timestamp(datetime.now())

    # we select rows that are 'due'; that is, the time elapsed since they were
    # last run is equal to or greater than the frequency at which they are sent.
    df = df[df['time_since_last_run']>=df['int_frequency']]
    
    # finally, we reindex the dataframe; this might not actually be necessary but 
    # is a good failsafe to ensure we can assume the structure of each dataframes 
    # index in future operations.
    df.reset_index(drop=True, inplace=True)

    # finally, we return the dataframe
    return df

# this is the synchronous function that will be used to send reports. It will be wrapped
# by a corresponding asynchronous celery function in celeryd.
def send_eligible_reports():

    # first, we select all the reports that are due to be sent
    report_df = select_user_reports_by_time()

    # next, we select the form data that should be sent, dropping 
    # the fields we don't want included.
    form_df = get_map_of_form_data('Journal', 'Metadata', 'IP_Address', 'Approver', 
                                        'Approval', 'Approver_Comment', 'Signature', '_id', add_hyperlink=True)




    for index, row in report_df.iterrows():
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
#         #     'start_at': datetime.datetime.now(),
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
