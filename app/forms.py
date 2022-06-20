from flask import Flask, Blueprint, g, flash, render_template, url_for, request, redirect, jsonify, session
import os, re, datetime, json, functools
import plotly
import plotly.express as px
import pandas as pd
import libreforms as form_src
import mongodb
from webargs import fields, flaskparser, ValidationError
from pymongo import MongoClient
from app.db import get_db
from app.auth import login_required
from app import display



def parse_form_fields(form=False):

    FORM_ARGS = {}           

    for field in form_src.forms[form].keys():

        if field.startswith("_"):
            pass
        elif form_src.forms[form][field]['output_data']['type'] == "str":
            FORM_ARGS[field] = fields.Str(
                        required=form_src.forms[form][field]['output_data']['required'],
                        validators=form_src.forms[form][field]['output_data']['validators'],)
        elif form_src.forms[form][field]['output_data']['type'] == "float":
            FORM_ARGS[field] = fields.Float(
                        required=form_src.forms[form][field]['output_data']['required'],
                        validators=form_src.forms[form][field]['output_data']['validators'],)
        elif form_src.forms[form][field]['output_data']['type'] == "list":
            FORM_ARGS[field] = fields.List(fields.String(),
                        required=form_src.forms[form][field]['output_data']['required'],
                        validators=form_src.forms[form][field]['output_data']['validators'],)
        elif form_src.forms[form][field]['output_data']['type'] == "int":
            FORM_ARGS[field] = fields.Int(
                        required=form_src.forms[form][field]['output_data']['required'],
                        validators=form_src.forms[form][field]['output_data']['validators'],)
        elif form_src.forms[form][field]['output_data']['type'] == "date":
            FORM_ARGS[field] = fields.Str(
                        required=form_src.forms[form][field]['output_data']['required'],
                        validators=form_src.forms[form][field]['output_data']['validators'],)
        else:
            FORM_ARGS[field] = fields.Str(
                        required=form_src.forms[form][field]['output_data']['required'],
                        validators=form_src.forms[form][field]['output_data']['validators'],)

    return FORM_ARGS

# this function creates a list of the form fields 
# we want to pass to the web application
def progagate_forms(form=False):
        
    list_fields = form_src.forms[form]

    # here we drop the meta data fields    
    [list_fields.pop(field) for field in list(list_fields.keys()) if field.startswith("_")]
    
    return list_fields

# placeholder, will be used to parse options for a given form
def parse_options(form=False):
    
    # we start by reading the user defined forms into memory
    list_fields = form_src.forms[form]

    # we define the default values for application-defined options
    OPTIONS = {
        "_dashboard": False,
        "_allow_repeat": False, 
        "_allow_uploads": False, 
        "_allow_csv_templates": False,
        "_suppress_default_values": False,  
    }

    for field in list_fields.keys():
        if field.startswith("_"):
            # we overwrite existing option values, and add new ones
            # based on the user defined configurations
            OPTIONS[field] = list_fields[field]
    
    return OPTIONS


# read database password file, if it exists
if os.path.exists ("mongodb_pw"):
    with open("mongodb_pw", "r+") as f:
        mongodb_pw = f.read().strip()
else:  
    mongodb_pw=None
# initialize mongodb database
mongodb = mongodb.MongoDB(mongodb_pw)


bp = Blueprint('forms', __name__, url_prefix='/forms')

@bp.route(f'/')
@login_required
def forms_home():
    return render_template('app/index.html', 
            homepage_msg="Select a form from the left-hand menu.",
            name="Form",
            type="forms.forms",
            site_name=display['site_name'],
            menu=[x for x in form_src.forms.keys()],
            display=display,
        ) 
        

# this creates the route to each of the forms
@bp.route(f'/<form_name>', methods=['GET', 'POST'])
@login_required
def forms(form_name):

    try:
        forms = progagate_forms(form_name)

        if request.method == 'POST':
            parsed_args = flaskparser.parser.parse(parse_form_fields(form_name), request, location="form")
            mongodb.write_document_to_collection(parsed_args, form_name, reporter=g.user['username'])
            flash(str(parsed_args))

        return render_template('app/index.html', 
            context=forms,                                          # this passes the form fields as the primary 'context' variable
            name=form_name,                                         # this sets the name of the page for the page header
            menu=[x for x in form_src.forms.keys()],                # this returns the forms in libreform/forms to display in the lefthand menu
            type="forms.forms",       
            site_name=display['site_name'],
            options=parse_options(form=form_name),                      # here we pass the _options defined in libreforms/forms/__init__.py
            display=display,
            )

    except Exception as e:
        return render_template('app/index.html', 
            form_not_found=True,
            msg=e,
            name="404",
            type="forms.forms",
            site_name=display['site_name'],
            menu=[x for x in form_src.forms.keys()],
            display=display,
        )
