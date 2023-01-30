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
from elasticsearch import Elasticsearch 
from elasticsearch_dsl import Search
from flask_login import current_user
from app.mongo import mongodb

bp = Blueprint('search', __name__, url_prefix='/search')


@login_required
@bp.route('/', methods=['GET'])
def search():

    query = request.args.get('query').lower()


    # if config['use_elasticsearch_as_wrapper']:
    #     tokens = query.split(" ")
    #     pass
        # client = Elasticsearch()
        # s = Search(using=client, index="submissions").query({"query_string": {"query": query+"~3", 'default_field':'_all'}})
        # results = s.execute()
        # results = client.get(index='submissions', id=query)

        # results = current_app.elasticsearch.search(index="submissions", 
        #             body={"query": {"query_string": {"query": query+"~3", 'default_field':'_all'}}}) 
    

    ####### this is from: https://www.youtube.com/watch?v=-KjE1JmFVNY and https://github.com/ahnaf-zamil/flask-elasticsearch-autocomplete
    #     # es = Elasticsearch()
    #     # print(f"Connected to ElasticSearch cluster {es.info()}")
        
    #     # clauses = [{"span_multi":{"match": {"fuzzy": {"_all": {"value": i, "fuzziness": "AUTO"}}}}} for i in tokens]

    #     # print(clauses)

    #     # payload = {
    #     #     "bool": {
    #     #         "must": [{"span_near": {"clauses": clauses, "slop": 0, "in_order": False}}]
    #     #     }
    #     # }

    #     # print(payload)

    #     # resp = es.search(index="submissions", query=payload, size=15)
    #     # results = [{'title': result['_source']['title'],'url':result['_source']['name']} for result in resp['hits']['hits']]

    #     # print(results)

    # else:

    results = mongodb.search_engine(query)

    return render_template('app/search.html', 
        site_name=config['site_name'],
        type="home",
        name='search',
        notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
        config=config,
        results=results,
        user=current_user if current_user.is_authenticated else None,
    )