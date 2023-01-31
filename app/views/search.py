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
from elasticsearch_dsl import Search, Q
from flask_login import current_user
from app.mongo import mongodb

bp = Blueprint('search', __name__, url_prefix='/search')


@login_required
@bp.route('/', methods=['GET'])
def search():

    query = request.args.get('query').lower()


    if config['use_elasticsearch_as_wrapper']:

        client = Elasticsearch()

        if config['search_fuzzy']:
            s = Search(using=client, index="submissions").query(Q({"fuzzy": {"fullString": {"value": query, "fuzziness": config['search_fuzzy']}}}))

        else:
            s = Search(using=client, index="submissions").query("match", fullString=query)
            # .filter("term", category="search") \ # see https://www.elastic.co/guide/en/elasticsearch/reference/current/query-filter-context.html#query-filter-context-ex
            # .query("match", fullString=query)   \

            # s.aggs.bucket('per_tag', 'terms', field='tags') \
            #     .metric('max_lines', 'max', field='lines')

        # per https://github.com/elastic/elasticsearch-dsl-py/issues/1510
        # Q('fuzzy', fullString=query)

        results = s.execute()

        # for hit in results:
        #     print(hit.url, hit.fullString)

        # for tag in response.aggregations.per_tag.buckets:
        #     print(tag.key, tag.max_lines.value)
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

    else: 
        # if we are not using elasticsearch as a search wrapper for mongodb, 
        # then let's just query mongodb directly; if we've passed any forms
        # to exclude, we pass those to the MongoDB method.

        results = mongodb.search_engine(query, exclude_forms=config['exclude_forms_from_search'])

    return render_template('app/search.html', 
        site_name=config['site_name'],
        type="home",
        name='search',
        notifications=current_app.config["NOTIFICATIONS"]() if current_user.is_authenticated else None,
        config=config,
        results=results,
        user=current_user if current_user.is_authenticated else None,
    )