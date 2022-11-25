# import flask-related packages
from flask import Blueprint, request, abort

# import custom packages from the current repository
from app.auth import login_required
from app import log, display, db, mongodb
from app.models import Signing
import app.signing as signing

# and finally, import other packages
import os, datetime, json
from bson import json_util
import pandas as pd


bp = Blueprint('api', __name__, url_prefix='/api')

if display['enable_rest_api']:


    # here we add the api route v1
    @bp.route('/v1/<signature>/<form_name>')
    # @login_required
    def api(form_name, signature):

        # here we capture the string-ified API key passed by the user
        signature = str(signature)

        if not display['enable_rest_api']:
            abort(404)
            return "This feature has not been enabled by your system administrator."

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
            abort(404)

