""" 
v1_api.py: implementation of v1 REST api views and logic



"""

__name__ = "app.views.v1_api"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "2.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


# import flask-related packages
from flask import current_app, Blueprint, request, abort, make_response, jsonify

# import custom packages from the current repository
from app import log, config
from app.models import Signing, db
from app.mongo import mongodb
import app.signing as signing
import libreforms

# and finally, import other packages
import os, datetime, json
from bson import json_util
import pandas as pd


bp = Blueprint('v1_api', __name__, url_prefix='/api/v1')


# here we add the api route v1
@bp.route('/<signature>/<form_name>')
def api_v1_get(form_name, signature):

    # here we capture the string-ified API key passed by the user
    signature = str(signature)

    # if not config['enable_v1_rest_api']:
    #     return abort(404)

    # here we make it so that API users can only access forms that are in the
    # current form config - eg. old forms, or forms whose name changed, will not
    # appear ... form admins will need to manage change cautiously until further
    # controls, see https://github.com/signebedi/libreForms/issues/130
    if not form_name in libreforms.forms.keys():
        return abort(404)

    signing.verify_signatures(signature, scope="api_key", abort_on_error=True)

    signing_df = pd.read_sql_table("signing", con=db.engine.connect())
    email = signing_df.loc[ signing_df['signature'] == signature ]['email'].iloc[0]
    
    try: 

        data = mongodb.read_documents_from_collection(form_name)
        df = pd.DataFrame(list(data))
        df.drop(columns=["_id"], inplace=True)
        
        # here we allow the user to select fields they want to use, 
        # overriding the default view-all.
        # warning, this may be buggy

        for col in df.columns:
            if request.args.get(col):
                # prevent type-mismatch by casting both fields as strings
                df = df.loc[df[col].astype("string") == str(request.args.get(col))] 

        log.info(f'{email} - REST API query for form \'{form_name}.\'')
        # log.info(f'{email} {signature} - REST API query for form \'{form_name}.\'') # removed this, which potentially leaks a signing key intended for reuse
        return json.loads(json_util.dumps(df.to_dict())) # borrowed from https://stackoverflow.com/a/18405626

    except Exception as e: 
        log.warning(f"LIBREFORMS - {e}")
        return abort(404)
