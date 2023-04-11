""" 
v2_api.py: implementation of v2 REST api views and logic


"""

__name__ = "app.views.v2_api"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.9.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


# import flask-related packages
from flask import current_app, Blueprint, request, abort, make_response, jsonify

# import custom packages from the current repository
from app.views.forms import propagate_form_configs, define_webarg_form_data_types
from app import log, config
from app.models import Signing, db
from app.mongo import mongodb
import app.signing as signing

# and finally, import other packages
import os, datetime, json
from bson import json_util
import pandas as pd
from webargs import flaskparser
from pymongo import MongoClient


bp = Blueprint('v2_api', __name__, url_prefix='/api/v2')

# Define API v2 routes for CRUD operations
@bp.route('/<form_name>', methods=['GET'])
def api_v2_get(form_name):
    # Use request.headers.get('X-API-KEY') to retrieve API key from headers
    signature = request.headers.get('X-API-KEY')

    # here we make it so that API users can only access forms that are in the
    # current form config - eg. old forms, or forms whose name changed, will not
    # appear ... form admins will need to manage change cautiously until further
    # controls, see https://github.com/signebedi/libreForms/issues/130
    if not form_name in libreforms.forms.keys():
        return abort(404)

    signing.verify_signatures(signature, scope="api_key", abort_on_error=True)

    # here we pull the user email
    with db.engine.connect() as conn:
        email = db.session.query(Signing).filter_by(signature=signature).first().email

    # pull the data
    get_data = mongodb.read_documents_from_collection(form_name)

    # write to a df
    df = pd.DataFrame(list(get_data))

    # stringify the ObjectID identifier
    df['_id'] = df['_id'].astype(str)

    # here we drop the metadata fields
    df.drop(columns=[x for x in mongodb.metadata_field_names.values() if x in df.columns and x not in [mongodb.metadata_field_names['reporter'], mongodb.metadata_field_names['owner'], mongodb.metadata_field_names['timestamp']]], inplace=True)
    
    # convert the data back to a dictionary
    data = df.to_dict()

    # set headers and status code
    status_code = 200
    headers = {'Content-Type': 'application/json'}

    # log the query here
    log.info(f'{email} - REST API GET query for form \'{form_name}.\'')

    return make_response(jsonify(data), status_code, headers)


@bp.route('/<form_name>', methods=['POST'])
def api_v2_post(form_name):
    # Use request.headers.get('X-API-KEY') to retrieve API key from headers
    signature = request.headers.get('X-API-KEY')

    # here we make it so that API users can only access forms that are in the
    # current form config - eg. old forms, or forms whose name changed, will not
    # appear ... form admins will need to manage change cautiously until further
    # controls, see https://github.com/signebedi/libreForms/issues/130
    if not form_name in libreforms.forms.keys():
        return abort(404)

    signing.verify_signatures(signature, scope="api_key", abort_on_error=True)

    # here we pull the user email
    with db.engine.connect() as conn:
        email = db.session.query(Signing).filter_by(signature=signature).first().email

    options = propagate_form_configs(form_name)

    data = request.form.to_dict()

    # parsed_args = flaskparser.parser.parse(define_webarg_form_data_types(form_name, args=list(request.form)), request)

    document_id = mongodb.write_document_to_collection(data, form_name, 
                    reporter=signature, 
                    ip_address=request.remote_addr if options['_collect_client_ip'] else None,)


    data = {"message": "success", "document_id": document_id}
    status_code = 201
    headers = {'Content-Type': 'application/json'}
    return make_response(jsonify(data), status_code, headers)


@bp.route('/<form_name>/<document_id>', methods=['GET'])
def api_v2_get_by_id(form_name, document_id):
    # Use request.headers.get('X-API-KEY') to retrieve API key from headers
    signature = request.headers.get('X-API-KEY')

    # here we make it so that API users can only access forms that are in the
    # current form config - eg. old forms, or forms whose name changed, will not
    # appear ... form admins will need to manage change cautiously until further
    # controls, see https://github.com/signebedi/libreForms/issues/130
    if not form_name in libreforms.forms.keys():
        return abort(404)

    signing.verify_signatures(signature, scope="api_key", abort_on_error=True)

    # here we pull the user email
    with db.engine.connect() as conn:
        email = db.session.query(Signing).filter_by(signature=signature).first().email

    data = mongodb.get_document_as_dict(form_name, document_id, drop_fields=[x for x in mongodb.metadata_field_names.values()])
    data['_id'] = str(data['_id'])

    status_code = 200
    headers = {'Content-Type': 'application/json'}
    return make_response(jsonify(data), status_code, headers)

@bp.route('/<form_name>/<document_id>', methods=['PUT'])
def api_v2_put(form_name, document_id):
    # Use request.headers.get('X-API-KEY') to retrieve API key from headers
    signature = request.headers.get('X-API-KEY')

    # here we make it so that API users can only access forms that are in the
    # current form config - eg. old forms, or forms whose name changed, will not
    # appear ... form admins will need to manage change cautiously until further
    # controls, see https://github.com/signebedi/libreForms/issues/130
    if not form_name in libreforms.forms.keys():
        return abort(404)

    signing.verify_signatures(signature, scope="api_key", abort_on_error=True)

    # here we pull the user email
    with db.engine.connect() as conn:
        email = db.session.query(Signing).filter_by(signature=signature).first().email

    options = propagate_form_configs(form_name)

    data = request.form.to_dict()

    document_id = mongodb.api_modify_document(data, form_name, document_id,
                    reporter=signature, 
                    ip_address=request.remote_addr if options['_collect_client_ip'] else None,)

    data = {"message": "success", "document_id": document_id}
    status_code = 200
    headers = {'Content-Type': 'application/json'}
    return make_response(jsonify(data), status_code, headers)


@bp.route('/<form_name>/<document_id>', methods=['DELETE'])
def api_v2_delete(form_name, document_id):
    # Use request.headers.get('X-API-KEY') to retrieve API key from headers
    signature = request.headers.get('X-API-KEY')

    # here we make it so that API users can only access forms that are in the
    # current form config - eg. old forms, or forms whose name changed, will not
    # appear ... form admins will need to manage change cautiously until further
    # controls, see https://github.com/signebedi/libreForms/issues/130
    if not form_name in libreforms.forms.keys():
        return abort(404)

    signing.verify_signatures(signature, scope="api_key", abort_on_error=True)

    # here we pull the user email
    with db.engine.connect() as conn:
        email = db.session.query(Signing).filter_by(signature=signature).first().email

    delete_document = mongodb.soft_delete_document(form_name, document_id) 

    headers = {'Content-Type': 'application/json'}

    if not delete_document:
        return abort(404)

    data = {"message": "success"}
    status_code = 204
    return make_response(jsonify(data), status_code, headers)