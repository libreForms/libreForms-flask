"""
form_access.py: group- and user-based access controls to r/w own and other forms

This script contains the logic used to manage access to form data. Specifically,
there are two obvious ways that form access may be limited: first, what resources
(eg. one's own, and other users') a user should be able to access, and what level 
of access that user should have. Form configs deal with these questions in a 
sometimes-robust, sometimes-Byzantine manner. For example, the following form 
configs apply some form of access control to forms:

    "_allow_anonymous_access": False,           # read-form-schema
    '_deny_groups': [],                         # write-own-form-data
    '_enable_universal_form_access': False,     # read-other-form-data
    '_submission': {    
        '_enable_universal_form_access': False, # read-other-form-data
        '_deny_read': [],                       # read-other-form-data
        '_deny_write': [],                      # write-other-form-data (in tandem with _enable_universal_form_access)
    },

and can be userful here in developing the following `categories` of specific form access 
(nb. we accept an implied permission to view and edit your own forms, but that may change 
in the future, see eg. https://github.com/libreForms/libreForms-flask/issues/90):

    read-form-schema : are members of the group permitted to view the structure of the form
    write-own-form-data : are members of the group permitted to edit their own form submissions
    read-other-form-data : are members of the group permitted to view others' form submissions
    write-other-form-data : are members of the group permitted to edit others' form submissions

"""

__name__ = "app.form_access"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.5.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from app.views.forms import propagate_form_configs
from app.mongo import mongodb
from libreforms import forms
import json

# this mapper function helps map user groups to to their access restrictions, 
# to ensure that search results (and possible other parts of the application) 
# show correct results and avoid leakage / improper access; for more details, 
# see https://github.com/libreForms/libreForms-flask/issues/259. 
def form_access_single_group(group):

    # we create a mapping dict that pairs each form with its associated configs, 
    # which we'll search within. In effect, this will store a child key for each 
    # form defined in the form config. Then, each of these keys will store `all`
    # the form configs for that given form.
    full_options_mapping = {}

    # we create a second mapping dict that will collect the access controls for 
    # this specified `group`. Then, like the `full_options_mapping`, it will 
    # contain child keys for each form defined in the form config. Finally,
    # it will store the the configs that are `relevant` (not `all`) to access. 
    group_access_mapping = {}

    for form in forms:
        full_options_mapping[form] = propagate_form_configs(form)


        group_access_mapping[form] = {  'read-form-schema':True if group not in full_options_mapping[form]['_deny_groups'] else False,
                                        'write-own-form-data':True if group not in full_options_mapping[form]['_deny_groups'] else False,
                                        'read-other-form-data':True if group not in full_options_mapping[form]['_submission']['_deny_read'] and not full_options_mapping[form]['_submission']['_enable_universal_form_access'] else False,
                                        'write-other-form-data':True if group not in full_options_mapping[form]['_submission']['_deny_write'] and not full_options_mapping[form]['_submission']['_enable_universal_form_access'] else False,  }

    # we return a form-by-form mapping for the specific group
    return group_access_mapping


# This wrapper will return a dict of form names, mapped to True if the 
# passed `group` has access at `access_level`, and False if not; it also
# returns primarily a list of forms from which the group is excluded
def test_access_single_group(   group,
                                # access_level can be any of 
                                    # read-form-schema
                                    # write-own-form-data
                                    # read-other-form-data
                                    # write-other-form-data 
                                access_level):
    
    dict_mapping = {}
    exclude_list_mapping = []
    group_access_mapping = form_access_single_group(group)

    for form in group_access_mapping:
        # we really want this logic mapping to fail, 
        # otherwise we append hte list the `exclude_list`
        if not group_access_mapping[form][access_level]:
            dict_mapping[form] = True
        else:
            dict_mapping[form] = False
            exclude_list_mapping.append(form)

    return exclude_list_mapping, dict_mapping


# This will read the access_roster data for a given form, expecting 
# the following format of the row's data formatted as a string:
    # _access_roster = {
    #     'group_a': {
    #         'access':'read',
    #         'target':'user'
    #     }, 
    #     'user_b': {
    #         'access':'write',
    #         'target':'group'
    #     }, 
    # }
# see https://github.com/libreForms/libreForms-flask/issues/200.
# def parse_access_roster_from_row(row):
#     _access_roster = json.loads(row[mongodb.metadata_field_names['access_roster']].replace('\'', '"'))
#     return _access_roster


