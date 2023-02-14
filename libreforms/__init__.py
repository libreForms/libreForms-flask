""" 
libreforms/__init__.py: this script defines the libreForms internal form representation

libreForms-flask implements the libreForms spec, see https://github.com/libreForms/spec,
a form configuration language and associated communication protocol built on HTTP requests 
optimized for managing institutional forms over a network.

Modern bureaucracies often rely on complex processes that tend to send you mad. These processes 
are typically built around the idea of institutional forms, a type of data that has a tendency 
to require multiple users with varying institutional roles to repeatedly access and modify 
individual records in processes that vary in their formality and clarity, and which tend to 
change over time. The libreForms API is purpose-built to manage data in such environments while 
keeping forms simple and flexible to changes in form layout and business processes.

At its core, the libreForms configuration language divides a form into its fields and configs. 
A field is an element of a form that an end user will generally see and interact with. Fields are 
generally composed of input and output specifications. Input specifications describe the type of 
field the end user will see and interact with. Output specifications describe the data type and/or 
structure that the field data will be treated as after the form is submitted.

A config is an element of a form that an end user does not necessarily see or interact with, but 
which modifies the behavior of the form in the client. Configs are generally denoted in their name 
using some reserved character, like a leading underscore. 

The internal form representation is a powerful tool built in Python dictionaries, but because it 
allows for eg. the integration of macros, it is also potentially dangerous to allow low-trust
users to make modifications to this directly. In these cases, we recommend an external form 
representation in a scrubbable markup language like YAML. For further discussion on this topic,
see https://github.com/libreForms/libreForms-flask/issues/280. The internal form representation 
is defined in libreforms/__init__.py. It allows administrators to bootstrap their own forms in a 
file called ```libreforms/form_config.py```. The internal form representation can generate a number 
of HTML fields, including (but not limited to) "text", "password", "radio", "select", "checkbox", 
"date", "hidden", and "number" fields. In addition, we plan to add support file uploads, see 
https://github.com/libreForms/libreForms-flask/issues/10. Further, there are a number of custom 
field types like "autocomplete" and "immutable_user_field" input types. The internal representation
supports casting inputs into str, float, int, and list data types. 

Fields must have a unique name, which must employ underscores instead of spaces ("My Form Field" would 
not work, but "My_Form_Field" is a correct field name). Configs are preceded by an underscore (eg. 
"_dashboard" or "_allow_repeats") and allow form administrators to define unique form behavior. Default 
values for these configs can be seen in app.views.forms by reviewing the propagate_form_configs function.
"""

__title__       = 'libreForms'
__description__ = 'an open form manager API'
__url__         = 'https://github.com/signebedi/libreForms'
__copyright__   = '(c) 2022 Sig Janoska-Bedi'
__name__        = "libreforms"
__author__      = "Sig Janoska-Bedi"
__credits__     = ["Sig Janoska-Bedi"]
__version__     = "1.2.0"
__license__     = "AGPL-3.0"
__maintainer__  = "Sig Janoska-Bedi"
__email__       = "signe@atreeus.com"

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
        "Select_Field": {
            "input_field": {"type": "select", "content": ["Pick", "An", "Option"]},
            "output_data": {"type": "str", "required": False, "validators": [], 'description': "this is a select / dropdown field"},
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
                "x": "_timestamp",   # scatter, bar, histogram, and line charts with 
                "y": "Int_Field",   # limited features supported
                "color": "Text_Field"
            },
            "access": [  # defaults to False, meaning no access controls are in place
                "default", 
                "admins"
                ]
        },
        "_allow_repeat": False, # defaults to False
        "_description": False, # defaults to False
        "_smtp_notifications": False, # defaults to False
        "_allow_anonymous_access": False, # defaults to False
        "_allow_csv_uploads": True, # defaults to False
        "_allow_csv_templates": True, # defaults to False
        "_suppress_default_values": False, # defaults to False
    },
}

# read forms from file as form
# overwrite/append form to forms in this file
try:
    import libreforms.form_config as form_config
    forms_appended = dict(forms)            # this creates a copy of the original dictionary, to
    forms_appended.update(form_config.forms)    # which we will append the form data
    forms = form_config.forms # this is the default behavior, which overwrites the default behavior   
except Exception as e:  # if anything above fails, we skip 
    print (e)

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
            assert forms[form][field]["input_field"]["type"] in ["text", "password", "select", "radio", "checkbox" , "date", "hidden", "number", "file"]

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
        # assert forms[form]["_allow_csv_uploads"]
        # assert forms[form]["_allow_csv_templates"]
        # assert forms[form]["_suppress_default_values"]
