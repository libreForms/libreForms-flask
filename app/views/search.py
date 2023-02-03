""" 
search.py: search feature implementation



"""

__name__ = "app.views.search"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.5.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# import flask-related dependencies
from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for, send_from_directory
from flask_login import current_user

# import flask app specific dependencies
from app import config
from app.mongo import mongodb
from app.views.auth import login_required


# this mapper function helps map user groups to to their access restrictions, 
# to ensure that search results (and possible other parts of the application) 
# show correct results and avoid leakage / improper access; for more details, 
# see https://github.com/libreForms/libreForms-flask/issues/259. 
def form_access_single_group(group):
    from app.views.forms import propagate_form_configs
    from libreforms import forms

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

            # The following options apply access controls to forms,:

            # "_allow_anonymous_access": False,           # read-form-schema
            # '_deny_groups': [],                         # write-own-form-data
            # '_enable_universal_form_access': False,     # read-other-form-data
            # '_submission': {    
            #     '_enable_universal_form_access': False, # read-other-form-data
            #     '_deny_read': [],                       # read-other-form-data
            #     '_deny_write': [],                      # write-other-form-data (in tandem with _enable_universal_form_access)
            #     },

            # and can be userful here in developing the following measures 
            # specific access, with an implied right to view your own submissions
                # read-form-schema : are members of the group permitted to view the structure of the form
                # write-own-form-data : are members of the group permitted to edit their own form submissions
                # read-other-form-data : are members of the group permitted to view others' form submissions
                # write-other-form-data : are members of the group permitted to edit others' form submissions

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

bp = Blueprint('search', __name__, url_prefix='/search')


@login_required
@bp.route('/', methods=['GET'])
def search():


    ### We start by checking for get vars and setting default behavior when they are not passed
    try:
        query = request.args.get('query').lower()
    except:
        return render_template('app/search.html', 
            site_name=config['site_name'],
            type="home",
            name='search',
            notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
            config=config,
            results=[],
            user=current_user if current_user.is_authenticated else None,
        )

    # here we collect the group access data for search result control
    exclude_forms_for_group, group_mapping = test_access_single_group(group=current_user.group, access_level='read-other-form-data')


    # if we've opted to use elasticsearch as a wrapper search engine for MongoDB
    if config['use_elasticsearch_as_wrapper']:
        from elasticsearch import Elasticsearch 
        from elasticsearch_dsl import Search, Q

        client = Elasticsearch()


        #  we concatenate the group forms exlude list with the config defined form exclude list, if it exists
        total_exclusions = exclude_forms_for_group + config['exclude_forms_from_search'] if config['exclude_forms_from_search'] else exclude_forms_for_group

        #  Add fuzzy matching, we it's been configured
        if config['fuzzy_search']:
            s = Search(using=client, index="submissions") \
                .query(Q({"fuzzy": {"fullString": {"value": query, "fuzziness": config['fuzzy_search']}}})) \
                .exclude("terms", formName=total_exclusions)    

        else:
            s = Search(using=client, index="submissions").query("match", fullString=query) \
                .exclude("terms", formName=total_exclusions)

        # print(s.to_dict())
        results = s.execute()


    else: 
        # if we are not using elasticsearch as a search wrapper for mongodb, 
        # then let's just query mongodb directly; if we've passed any forms
        # to exclude, we pass those to the MongoDB method.

        results = mongodb.search_engine(query, exclude_forms=total_exclusions, fuzzy_search=config['fuzzy_search'])

    # # the following logic can be used if we want to add pagination. Nb. elasticsearch only returns 
    # # 10 records by default, unless modified, see https://stackoverflow.com/a/40009425/13301284
    # page_no = request.args.get('page_no', 1, type=int)
    # results_per_page = request.args.get('results_per_page', 10, type=int)

    # if len(results) > results_per_page:
    #     starting_position = page_no*results_per_page+1
    #     ending_position = starting_position + results_per_page

    #     print(f"sp: {starting_position}\nep:{ending_position}")

    #     results = results[starting_position:ending_position]

    # here we allow administrators to set the max number of results that will be shown in the search results.
    if config['limit_search_results_length'] and isinstance(config['limit_search_results_length'], int) and len(results) > config['limit_search_results_length']:
        results=results[:config['limit_search_results_length']]

    if len(results) < 1:
        flash(f"No results found for search term {query}")

    return render_template('app/search.html', 
        site_name=config['site_name'],
        type="home",
        name='search',
        notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
        config=config,
        results=results,
        user=current_user if current_user.is_authenticated else None,
    )