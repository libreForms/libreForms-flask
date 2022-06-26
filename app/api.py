# import flask-related packages
from flask import Blueprint, request

# import custom packages from the current repository
import mongodb
from app.db import get_db
from app.auth import login_required
from app.forms import display, parse_form_fields, progagate_forms, parse_options

# and finally, import other packages
import os
import pandas as pd


# read database password file, if it exists
if os.path.exists ("mongodb_pw"):
    with open("mongodb_pw", "r+") as f:
        mongodb_pw = f.read().strip()
else:  
    mongodb_pw=None


# initialize mongodb database
mongodb = mongodb.MongoDB(mongodb_pw)


# here we read the current list of acceptible api keys into memory
# users should define this file as it does not ship with the git repo
if os.path.exists ("api_keys"):
    api_keys = pd.read_csv("api_keys")
else:
    api_keys = pd.DataFrame({'api_keys':['t32HDBcKAAIVBBPbjBADCbCh']}) # this will be the default key



bp = Blueprint('api', __name__, url_prefix='/api')


# here we add the api route v1
@bp.route('/v1/<api_key>/<form_name>')
@login_required
def api(form_name, api_key):

    # here we capture the string-ified API key passed by the user
    api_key = str(api_key)
    
    # we added the strip() method to remove trailing whitespace from the api keys
    if api_key in (api_keys.api_keys.str.strip()).values: 
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

            return df.to_dict()

        except Exception as e:
            return {"form_error":"invalid form"}

    else:
        return {"api_error":"invalid api key"}


