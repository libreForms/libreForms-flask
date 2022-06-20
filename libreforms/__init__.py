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
            "output_data": {"type": "str", "required": False, "validators": []},
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
}

# read forms from file as add_ons
# overwrite/append add_ons to forms in this file
try:
    import libreforms.add_ons as add_ons
    forms_appended = dict(forms)            # this creates a copy of the original dictionary, to
    forms_appended.update(add_ons.forms)    # which we will append the add_ons data
    forms = add_ons.forms # this is the default behavior, which overwrites the default behavior   
except: # if anything above fails, we skip 
    pass

# this function can be run to debug the forms located in this 
# file and any additional form data passed through forms.d/
def lint(forms=forms):
    for form in forms.keys():
        print(form)

        for field in forms[form].keys():
            print(field)

            if field.startswith("_"):
                break

            # verify that the input_field key is defined for each field
            assert forms[form][field]["input_field"]

            # verify that the type employed conforms to one of the acceptable form fields
            assert forms[form][field]["input_field"]["type"] in ["text", "password", "radio", "checkbox" , "date", "hidden", "number", "file"]

            # verify that the form content is is a list data type
            assert isinstance(forms[form][field]["input_field"]["content"], list)

            # verify that the output_data key is defined for each field
            assert forms[form][field]["output_data"]

            # verify that the type employed conforms to one of the acceptable form fields
            assert forms[form][field]["output_data"]["type"] in ["str", "float", "int", "list"]

            # verify that required is set to true or false
            assert forms[form][field]["output_data"]['required'] in [True, False]

            # verify that the form validators key a list data type
            assert isinstance(forms[form][field]["output_data"]["validators"], list)

        # if field == "_dashboard":
        #     assert forms[form]["_dashboard"]
        # assert forms[form]["_allow_repeat"]
        # assert forms[form]["_allow_uploads"]
        # assert forms[form]["_allow_csv_templates"]
        # assert forms[form]["_suppress_default_values"]
