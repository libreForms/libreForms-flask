# libreforms/__init__.py: this script defines the libreForms abstraction layer.
# libreForms provides a simple but highly extensible method of form building in Python, 
# leveraging Flask's doctrine of 'simplicity and extensibility' to give significant 
# control and flexibility to organizations to design forms and data that meet their 
# needs. To accomplish this, the application is built on an abstraction layer that stores 
# all the information needed to generate a browser-based form and parse form data into a 
# cohesive data structure.

# The libreForms abstraction layer is defined in ```libreforms/forms/__init__.py``` 
# and expects organizations to overwrite the default form by adding a file called 
# ```libreforms/add_ons.py```. At this time, the abstraction layer can handle the 
# "text", "password", "radio", "checkbox", "date", "hidden", and "number" input types, 
# and can write to Python's str, float, int, and list data types. 

# The abstraction layer breaks down individual forms into fields and configurations. A 
# field must have a unique name, which must employ underscores instead of spaces ("My 
# Form Field" would not work, but "My_Form_Field" is a correct field name). Configuration 
# names are preceded by an underscore (eg. "_dashboard" or "_allow_repeats") and allow 
# form administrators to define unique form behavior. All built in configurations default 
# to a value of False.

__title__       = 'libreForms'
__description__ = 'an open form manager API'
__version__     = '0.6.0'
__url__         = 'https://github.com/signebedi/libreForms'
__author__      = 'Sig Janoska-Bedi'
__author_email__= 'signe@siftingwinnowing.com'
__maintainer__  = 'Sig Janoska-Bedi'
__license__     = 'AGPL-3.0'
__copyright__   = '(c) 2022 Sig Janoska-Bedi'

import datetime, os, json

forms = {
    "sample-form": {
        "Text_Field": {
            "input_field": {"type": "text", "content": ["NA"]},
            "output_data": {"type": "str", "required": False, "validators": [lambda p: len(p) >= 6], 'description': "this is a text field"},
        },
        "Pass_Field": {
            "input_field": {"type": "password", "content": [""]},
            "output_data": {"type": "str", "required": False, "validators": [], 'description': "this is a password field"},
        },
        "Radio_Field": {
            "input_field": {"type": "radio", "content": ["Pick", "An", "Option"]},
            "output_data": {"type": "str", "required": False, "validators": [], 'description': "this is a radio field"},
        },
        "Check_Field": {
            "input_field": {"type": "checkbox", "content": ["Pick", "An", "Option"]},
            "output_data": {"type": "list", "required": False, "validators": [], 'description': "this is a checkbox field"},
        },
        "Date_Field": {
            "input_field": {"type": "date", "content": [datetime.datetime.today().strftime("%Y-%m-%d")]},
            # "input_field": {"type": "date", "content": []},
            "output_data": {"type": "str", "required": False, "validators": [], 'description': "this is a date field"},
        },
        "Hidden_Field": {
            "input_field": {"type": "hidden", "content": ["This field is hidden"]},
            "output_data": {"type": "str", "required": False, "validators": [], 'description': "this is a hidden field"},
        },
        "Float_Field": {
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "float", "required": False, "validators": [], 'description': "this is a float field"},
        }, 
        "Int_Field": {
            "input_field": {"type": "number", "content": [0]},
            "output_data": {"type": "int", "required": False, "validators": [], 'description': "this is an int field"},
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
        "_allow_uploads": True, # defaults to False
        "_allow_csv_templates": True, # defaults to False
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
