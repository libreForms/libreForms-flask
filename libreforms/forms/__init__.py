# libreforms/forms/__init__.py: the source for form field data in the libreForms application.
# libreForms defines a robust abstraction layer between (1) the types of form fields that are 
# used to collect user data and (2) the data type that the content of these form fields take, 
# once submitted by the user, and (3) the underlying data structure of form responses, which 
# the system stores in a JSON-like database well suited to integration with useful data science 
# tools like pandas, as well as visualization libraries like plotly. Specifically, this API
# supports the following form fields:
    # "text"
    # "password"
    # "radio"
    # "checkbox" 
    # "date"
    # "hidden"
    # "number"
    # "file"
# as well as the following output data types:
    # str
    # float
    # int
    # list
# input_field refers only to the structure of the markup field that will be used
# to collect the data; all the information regarding the typing and validation
# of the data exists in output_data.
# for each form, optional, non-form-field data is defined with an underscore (_)
# preceding the key name, like _allow_repeats. All of these are optional fields 
# and default to a value of False. 

import datetime, os, json

forms = {
    "sample-form": {
        "Text_Field": {
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": [lambda p: len(p) >= 6]},
        },
        "Pass_Field": {
            "input_field": {"type": "password", "content": [""]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "Radio_Field": {
            "input_field": {"type": "radio", "content": ["Pick", "An", "Option"]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "Check_Field": {
            "input_field": {"type": "checkbox", "content": ["Pick", "An", "Option"]},
            "output_data": {"type": "list", "required": False, "validators": []},
        },
        "Date_Field": {
            "input_field": {"type": "date", "content": [datetime.datetime.today().strftime("%Y-%m-%d")]},
            # "input_field": {"type": "date", "content": []},
            "output_data": {"type": "date", "required": False, "validators": []},
        },
        "Hidden_Field": {
            "input_field": {"type": "hidden", "content": ["This field is hidden"]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "Float_Field": {
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": False, "validators": []},
        }, 
        "Int_Field": {
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "int", "required": False, "validators": []},
        }, 
#         "File_Field": {
#             "input_field": {"type": "file", "content": [None]}, # still need to review https://flask.palletsprojects.com/en/2.1.x/patterns/fileuploads/
#             "output_data": {"type": TBD, "validators": []},
#         },
        "_dashboard": {             # defaults to False
            "type": "scatter",      # this is a highly powerful feature but requires
            "fields": {             # some knowledge of plotly dashboards; currently
                "x": "Timestamp",   # only line charts with limited features supported
                "y": "Int_Field", 
                "color": "Text_Field"
            }
        },
        "_allow_repeat": False, # defaults to False
        "_allow_uploads": False, # defaults to False
        "_allow_csv_templates": False, # defaults to False
        "_suppress_default_values": False, # defaults to False
    },
    "perstat": {
        "Unit": {
            "input_field": {"type": "radio", "content": ["687", "980", "753", "826"]},
            "output_data": {"type": "str", "required": True, "validators": []},
        },
        "Authorized":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "On_Hand":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "Gains":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "Replacements":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "Returned_to_Duty":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "Killed":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "Wounded":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "Nonbattle_Loss":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "Missing":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "Deserters":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "AWOL":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "Captured":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": True, "validators": []},
        },
        "Narrative":{
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": True, "validators": []},
        },
        "Reporter":{
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": True, "validators": []},
        },
        "_dashboard": { 
            "type": "line",  
            "fields": {
                "x": "Timestamp",   
                "y": "On_Hand", 
                "color": "Unit"
            }
        },
        "_allow_repeat": False, 
        "_allow_uploads": False, 
        "_allow_csv_templates": False, 
        "_suppress_default_values": False,
    },
    "sitrep": { 
        "Unit": {
            "input_field": {"type": "radio", "content": ["687", "980", "753", "826"]},
            "output_data": {"type": "str", "required": True, "validators": []},
        },
        "Present_Location":{
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "Activity":{
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "Effective":{
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": False, "validators": []},
        },
        "Own_Disposition":{
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "Situation":{
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "Operations":{
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "Intelligence":{
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "Logistics":{
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "Communications":{
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "Personnel":{
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": []},
        },
        "_dashboard": False,
        "_allow_repeat": False, 
        "_allow_uploads": False, 
        "_allow_csv_templates": False, 
        "_suppress_default_values": False, 
    },
}