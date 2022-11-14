# import flask-related packages
from flask import Blueprint, request, abort

# import custom packages from the current repository
import mongodb
from app.auth import login_required
from app import log, display, db
from app.models import Signing
import app.signing as signing

# and finally, import other packages
import os, datetime
import pandas as pd


# read database password file, if it exists
if os.path.exists ("mongodb_creds"):
    with open("mongodb_creds", "r+") as f:
        mongodb_creds = f.read().strip()
else:  
    mongodb_creds=None


# initialize mongodb database
mongodb = mongodb.MongoDB(mongodb_creds)


# here we read the current list of acceptible api keys into memory
# users should define this file as it does not ship with the git repo
if os.path.exists ("api_keys"):
    api_keys = pd.read_csv("api_keys")
else:
    api_keys = pd.DataFrame({'api_keys':['t32HDBcKAAIVBBPbjBADCbCh']}) # this will be the default key



bp = Blueprint('api', __name__, url_prefix='/api')


# here we add the api route v1
@bp.route('/v1/<signature>/<form_name>')
# @login_required
def api(form_name, signature):

    # here we capture the string-ified API key passed by the user
    signature = str(signature)

    if not display['enable_rest_api']:
        abort(404)
        return "This feature has not been enabled by your system administrator."

    if not Signing.query.filter_by(signature=signature).first():
        abort(404)
        return "Invalid request key."

    # if the signing key's expiration time has passed, then set it to inactive 
    if Signing.query.filter_by(signature=signature).first().expiration < datetime.datetime.timestamp(datetime.datetime.now()):
        signing.expire_key(signature)

    # if the signing key is set to inactive, then we prevent the user from proceeding
    # this might be redundant to the above condition - but is a good redundancy for now
    if Signing.query.filter_by(signature=signature).first().active== 0:
        abort(404)
        return "Invalid request key."

    # if the signing key is not scoped (that is, intended) for this purpose, then 
    # return an invalid error
    if not Signing.query.filter_by(signature=signature).first().scope == "api_key":
        abort(404)
        return "Invalid request key."


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

        log.info(f'{email} {signature} - REST API query for form \'{form_name}.\'')
        return df.to_dict()

    except Exception as e:
        abort(404)

