""" 
search.py: search feature implementation



"""

__name__ = "app.views.search"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.1.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# import flask-related dependencies
from flask import current_app, Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, jsonify
from flask_login import current_user

# import flask app specific dependencies
from app import config
from app.mongo import mongodb
from app.form_access import test_access_single_group
from app.views.auth import login_required
from app.views.forms import standard_view_kwargs
from app.decorators import required_login_and_password_reset
from libreforms import forms as lf

bp = Blueprint('search', __name__, url_prefix='/search')

@required_login_and_password_reset
@bp.route('/', methods=['GET'])
def search():


    ### We start by checking for get vars and setting default behavior when they are not passed
    try:
        query = request.args.get('query').lower()
    except:
        return render_template('app/search.html.jinja', 
            type="home",
            name='Search',
            subtitle="Results",
            results=[],
            **standard_view_kwargs(),
        )

    # here we collect the group access data for search result control
    exclude_forms_for_group, group_mapping = test_access_single_group(group=current_user.group, access_level='read-other-form-data')

    #  we concatenate the group forms exlude list with the config defined form exclude list, if it exists
    total_exclusions = exclude_forms_for_group + config['exclude_forms_from_search'] if config['exclude_forms_from_search'] else exclude_forms_for_group

    # if we've opted to use elasticsearch as a wrapper search engine for MongoDB
    if config['use_elasticsearch_as_wrapper']:
        from elasticsearch import Elasticsearch 
        from elasticsearch_dsl import Search, Q

        client = Elasticsearch()


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
        # print([x for x in results])


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
        flash(f"No results found for search term {query}", "warning")

    return render_template('app/search.html.jinja', 
        type="home",
        name='Search',
        subtitle="Results",
        results=results,
        **standard_view_kwargs(),
    )

# Added in https://github.com/libreForms/libreForms-flask/issues/437
@required_login_and_password_reset
@bp.route('/advanced', methods=['GET'])
def advanced_search():


    # # Here we define a config listing the names of all the forms
    # with app.app_context():
    #     app.config['FORMS_ALL'] = libreforms.forms.keys()


    if config['exclude_forms_from_search']:

        f = [x for x in lf.keys() if x not in config['exclude_forms_from_search']]

    else:
        f = lf.keys()

    return render_template('app/advanced_search.html.jinja', 
        type="home",
        name='Search',
        subtitle="Advanced",
        form_list=f,
        **standard_view_kwargs(),
    )

    # for form not in exclude form:

        # allow users to select form from dropdown and,
        # using JS, select the fields that users can match. 
        # Default to NA for each field. If it is a checkbox 
        # field, allow user to check boxes. If it is a radio or
        # select field, allow users to select from a dropdown.
        # Allow users to toggle exact vs. fuzzy matching on the 
        # query as a whole.

        # Here, we just pass the fields, input_types, and (if
        # they are pre-set value ranges) the options available to 
        # each user.

        # Make sure to escape the query string values to minitgate risk 
        # of an eg. sql injection.


@required_login_and_password_reset
@bp.route('/get_fields', methods=['POST'])
def get_fields_advanced_search():

    data = request.get_json()
    form_name = data.get('formName')

    # Check if the form name exists in the lf dictionary
    if form_name in lf:
        form_fields = lf[form_name]
        response_data = [{"name": field, "type": form_fields[field]['input_field']["type"], "content": form_fields[field]['input_field']["content"]} for field in form_fields if not field.startswith("_") and form_fields[field]['input_field']["type"] != "hidden"]
        return jsonify(response_data)
    else:
        return jsonify({"error": "Form not found"}), 404


    # if request.method == 'POST':
    #     form = request.form['form']

    # return abort(404)
    # try:
    #     form = request.args.get('form').lower()
    # except:
    #     return abort(404)


    # Exclude the hidden fields.
