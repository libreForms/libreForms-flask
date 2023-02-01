""" 
search.py: search feature implementation



"""

__name__ = "app.views.search"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.4.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for, send_from_directory
from app import config
from app.views.auth import login_required
from flask_login import current_user
from app.mongo import mongodb


def form_access_by_group(group):
    from app.views.forms import propagate_form_configs
    from libreforms import forms

    # we create a mapping dict that pairs each form with its associated configs, which we'll search within.
    mapping = {}
    for form in forms:
        mapping[form] = propagate_form_configs(form)


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

    # if we've opted to use elasticsearch as a wrapper search engine for MongoDB
    if config['use_elasticsearch_as_wrapper']:
        from elasticsearch import Elasticsearch 
        from elasticsearch_dsl import Search, Q

        client = Elasticsearch()

        #  this approach is ugly and inefficient. It needs to be cleaned up.
        if config['fuzzy_search'] and config['exclude_forms_from_search']:
            s = Search(using=client, index="submissions") \
                .query(Q({"fuzzy": {"fullString": {"value": query, "fuzziness": config['fuzzy_search']}}})) \
                .exclude("terms", formName=config['exclude_forms_from_search'])
                # Q({"fuzzy": {"fullString": {"value": query, "fuzziness": config['fuzzy_search']}}})
        

        elif config['fuzzy_search'] and not config['exclude_forms_from_search']:
            s = Search(using=client, index="submissions") \
                .query(Q({"fuzzy": {"fullString": {"value": query, "fuzziness": config['fuzzy_search']}}})) \

        elif not config['fuzzy_search'] and config['exclude_forms_from_search']:
            s = Search(using=client, index="submissions").query("match", fullString=query) \
                .exclude("terms", formName=config['exclude_forms_from_search'])

        else:
            s = Search(using=client, index="submissions").query("match", fullString=query)

        # print(s.to_dict())
        results = s.execute()


    else: 
        # if we are not using elasticsearch as a search wrapper for mongodb, 
        # then let's just query mongodb directly; if we've passed any forms
        # to exclude, we pass those to the MongoDB method.

        results = mongodb.search_engine(query, exclude_forms=config['exclude_forms_from_search'], fuzzy_search=config['fuzzy_search'])

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

    return render_template('app/search.html', 
        site_name=config['site_name'],
        type="home",
        name='search',
        notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
        config=config,
        results=results,
        user=current_user if current_user.is_authenticated else None,
    )