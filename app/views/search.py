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

    page_no = request.args.get('page_no', 1, type=int)
    results_per_page = request.args.get('results_per_page', 10, type=int)


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

    return render_template('app/search.html', 
        site_name=config['site_name'],
        type="home",
        name='search',
        notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
        config=config,
        results=results,
        user=current_user if current_user.is_authenticated else None,
    )