# report-app
an open, extensible, lightweight browser-based form manager

## features

- A routeable web server (http://192.168.x.x:8000/) that provides access to various features
- MongoDB backend with documents broken down by unit, then data-type (or report-type), and then timestamp

## database
The structure of the MongoDB database is libreForms > form > _id such that administrators can easily sort data by form and, within each form, select by arbitrary fields like "Preparer" or "timestamp". 


The form_src.py file contains a list of python dictionaries containing each form's name and an arbitary set of fields mapped to their default values for data typing. This list is externalized from app.py in order to make it easily extensible with new forms. The progagate_forms() function in app.py will be used to generate a different static page based on the form field values within the dictionary. Here is an example of what form_src.py might look like.

```python
# forms/__init__.py: the source for form field data in the libreForm application.
# the data contained in this file can be referenced from the base app directory by
# running 'import forms' in a python script. The data here should be stored in the
# 'forms' variable, which is a dictionary whose keys correspond to the name and/or
# number of a given form (meaning no repetition is allowed), while the values is a
# nested dictionary whose keys correspond to a given form field, while the values
# correspond to the default value of that field, which helps also define the data
# type by leveraging python's dynamic typing system. At this time, only strings and
# integers are supported; if the datatype does not neatly fit into one of these types,
# then the field generator in the libreForms app will treat the data like a string.
# Also note, field names may be capitalized, but spaces should be replaced by under
# scores (_) to ensure they are computer-friendly; these are replaced with spaces in
# HTML/Jinja2 template for human-readability.

forms = {
    "sample-1": {                   # this structure creates a dictionary of keys corresponding to
        "Preparer":"Bill Smith",    # each unique form name that an organization's sys admin would
        "Current_Units":0,          # like to make available to their users, while the value is a
        "Requested_Units":0,        # second, nested dictionary containing the field names (keys)
        "Item_ID":"003A9D",         # mapped to their default values (values); by setting default
        "Another_Int":0,            # values, we can easily identify the data type of the field;
        "Yet_Another_Int":0,        # and if you'd like to suppress default values on the web page
        "Another_String":'NA',      # you can simply set display_default_values=False in app.py.
        "allow_repeat":False,       # the "allow_repeat" field is dropped before being returned,
    },                              # and allows the user to to add an arbitrary number of add'l 'rows' of data
    "sample-2": {
        "Preparer_Team":["Infrastructure", "Finance", "Human Capital"],
        "Preparer":"Bill Smith",
        "Access_Requested":["High", "Low"],
        "allow_repeat":True
    },
}
```

## dependencies

This application has a few dependencies that, in its current form, may be prone to obsolescence; there is an issue in the backlog to unit test for, among other things, obsolete dependencies. For now, here is a list of dependencies:

```
bootstrap-3.4.1.min.css
bootstrap-3.4.1.min.js
jquery-3.2.1.slim.min.js
jquery-3.5.1.min.js
plotly-v1.58.5.min.js

```
```

And python requirements:
```
click==8.1.3
Flask==2.1.2
gunicorn==20.1.0
importlib-metadata==4.11.4
itsdangerous==2.1.2
Jinja2==3.1.2
MarkupSafe==2.1.1
marshmallow==3.16.0
numpy==1.21.6
packaging==21.3
pandas==1.3.5
plotly==5.8.0
pymongo==4.1.1
pyparsing==3.0.9
python-dateutil==2.8.2
pytz==2022.1
six==1.16.0
tenacity==8.0.1
typing_extensions==4.2.0
webargs==8.1.0
Werkzeug==2.1.2
zipp==3.8.0
```
