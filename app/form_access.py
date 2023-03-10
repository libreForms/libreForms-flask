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
__version__ = "1.8.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from app.views.forms import propagate_form_configs
from app.mongo import mongodb
# from app.models import db, User
# import json
import pandas as pd

# this mapper function helps map user groups to to their access restrictions, 
# to ensure that search results (and possible other parts of the application) 
# show correct results and avoid leakage / improper access; for more details, 
# see https://github.com/libreForms/libreForms-flask/issues/259. 
def form_access_single_group(group,forms=None):

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
    
    if not forms:
        from libreforms import forms

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

def unpack_access_roster(   username:str,
                            # user:User, 
                            form_name:str=None, 
                            document_id:str=None, 
                            permission:str=None): # the `permission` kwarg optionally tests for a permission for the user in the access roster, if passed

    document = mongodb.get_document_as_dict(collection_name=form_name, document_id=document_id)
    access_roster = document[mongodb.metadata_field_names['access_roster']]

    # return false if the user is not in the access roster keys - that way, we can assume that
    # the user passed to the function is not authorized whenever this returns false.
    if username not in access_roster:
        return False

    # this is unique behavior. If the function call receives a `permission` kwarg, then test
    # for that permission as a string in the access roster keys for the current user, and 
    # return true if found, otherwise false. This is a quick check for a specific permission
    # level, that we want to be able to assess for its truth value. 
    if permission:
        return True if permission in access_roster[username] else False
 
    # If no permission is passed, then return all the current user's permissions
    # as a list / string, see https://github.com/libreForms/libreForms-flask/issues/200.
    return access_roster[username]


# this is a second stab at the access roster - this one inverts the data structure in a way to make
# this method callable at runtime, without a persistent access roster to give form access more
# dynamism, see https://github.com/libreForms/libreForms-flask/issues/295. Example data structure:
#       {
#           'read':['a','b','c'],
#           'write':['a','b','c'],
#           'delete':['a','b','c'], 
#           'approve':['a','b','c'],
#       }
def v2_unpack_access_roster(    permission:str=None, 
                                username:str=None, 
                                # you can pass a mongodb artifact as `document` and form config data as 
                                # `form_config`. This is the recommended approach to minimize complexity
                                document=None,
                                form_config=None,
                                # if you pass the form_name and document_id, and don't pass a document or 
                                # form_config, then this function will fall back on querying for this data.
                                # In most cases, this will be unnecessarily complex because we anticipate
                                # that code will usually already have the form config and document in memory
                                # when calling this method; but there are some cases where this is not feasible.
                                form_name:str=None,
                                document_id:str=None,):

    #########################
    # Collect the input data
    #########################

    # the structure of this method necessitates that either a form_config object or form name is passed; likewise,
    # it requires that either a document or document_id is passed. If these requireents are not met, return None.
    if (not form_config and not form_name) or (not document and not document_id):
        return None

    if not form_config:
        # here we propagate the form config if it has not been passed
        from app.views.forms import propagate_form_configs
        form_config = propagate_form_configs(form_name)

    if not document:
        # here we get the document details from mongodb if a document object has not been passed 
        document = mongodb.get_document_as_dict(collection_name=form_name, document_id=document_id)

    ########################
    # Compile access roster
    ########################

    # first we create the data structure skel
    access_roster = {
                        'read':[],
                        'write':[],
                        'delete':[], 
                        'approve':[],
                    }


    # read owner and approver details from form.

    # read approver details from form config and, if approval for the 
    # given form is not enabled, then continue without setting any approvers


    ###########################
    # Structure the output data
    ###########################

    # this method is intended to do a few things - though  we could alternatively write a single function 
    # with several wrappers to tailor functionality. Irrespective of the eventual form, we want to at least
    # think through the different use cases and the return data structure that they would entail. First, (1)
    # in cases where no information or permission level have been passed, it is clear from context that there
    # is no structuring of the data possible - and such structuring is probably not desired. In these cases,
    # we simply return the full `access_roster` object from above, and allow the lower level application logic 
    # parse and restructure it however needed. Next, (2) are cases where a username has been passed, but no
    # permission level. In these instances, it is not really possible to return True / False because there is 
    # no condition (permission-level) to assess the username that was passed. Instead, we should consider 
    # returning EITHER (a) a dict that maps the different permission levels (read, write, delete, approve) to
    # a bool that assesses True when the passed username is contained in that permission level's list OR (b)
    # a simple list of permission levels in which the passed username is contained. Third, (3) if a permission
    # level is passed, but not a username, we simply return the list of usernames authorized at that permission
    # level. Fourth, (4) if a username and permission level are both passed, we return a bool that assesses 
    # True if the passed username is authorized at the passed permission level, else False.

    # if the user doesn't pass a specific permission level or username, then return 
    # the whole data structure
    if not permission and not username:
        return access_roster

    # if we pass a username but not permission, find and return the permissions, as a list, that the user has
    # been authorized - see major comment above for further discussion regarding the tradeoffs of this data
    # structure - a list structure seems most effective because it captures the widest range of possible cases
    # where we are trying to authorize a user and want a general, reusable list of authorized activities that
    # we store in the frontend session.
    elif not permission and username:

        return {    
                    'read':True if username in access_roster['read'] else False, 
                    'write':True if username in access_roster['write'] else False, 
                    'delete':True if username in access_roster['delete'] else False,  
                    'approve':True if username in access_roster['approve'] else False, 
                }

    # if we pass a permission and not a username, then return the entire list of users authorized at the 
    # passed permission level
    elif permission and not username:
        return access_roster[permission]
  
    # if the passed username is a string, return a bool that assesses True if the username is contained at the
    # passed permission level, else False. If the username isn't a string, then just return the list of users
    # authorized at the passed permission level. 
    return (username in access_roster[permission]) if isinstance(username,str) else access_roster[permission]


# this creates a list of forms that require group-based approval, and for which the 
# `group` value passed is set as the approving group.
def list_of_forms_approved_by_this_group(group:str,forms:dict=None) -> list:

    # import the forms object if none is passed
    if not forms:
        from libreforms import forms

    l = [] # this is the list object that we'll use to return the form names
    
    # add form names to the list if the current group is their approver 
    for form_name,form_config in forms.items():
        if '_form_approval' in form_config and form_config['_form_approval']['type'] == 'group':
            if form_config['_form_approval']['target'] == group:
                l.append(form_name)
    return l

# this wraps the list_of_forms_approved_by_this_group function above, by returning 
# an actual list of documents that need approval, so it can be appended (if len > 0) 
# to the list of form approvals in app.views.submissions and app.action_needed.
def documents_needing_this_groups_approval (group:str,forms:dict=None) -> list:

    # import the forms object if none is passed
    if not forms:
        from libreforms import forms

    df = pd.DataFrame()

    form_list = list_of_forms_approved_by_this_group(group=group,forms=forms)

    # select list of form where form_name in `form_list` and where there is no approval


    return df

