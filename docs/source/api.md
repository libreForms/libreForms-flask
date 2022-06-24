## API

The purpose of the libreForms project is to provide a simple but highly extensible method of form building in Python, leveraging Flask's doctrine of 'simplicity and extensibility' to give significant control and flexibility to organizations to design forms and data that meet their needs. 

The application provides an API for storing all the information it needs to generate a browser-based form within a Python dictionary. Given the project's emphasis on supporting arbitrary data structures, it translates these form fields into data structures intended to be stored in a JSON-like Document database like MongoDB, which it supports out-of-the-box, and creates a separate collection for each unique form with the presumption that the documents contained therein will adhere to a data structure that contains some set of common fields upon which data may be collated.

libreForms defines a robust abstraction layer (the config file for which is located at ```libreforms/forms/__init__.py```, which can be overwritten and/or extended by adding a file called ```libreforms/forms/add_ons.py```) between (1) the types of form fields that are used to collect user data and (2) the data type that the content of these form fields take, once submitted by the user, and (3) the underlying data structure of form responses, which the system stores in a JSON-like database well suited to integration with useful data science tools like pandas, as well as visualization libraries like plotly. Specifically, this API supports the following types of HTML form fields:

- "text"
- "password"
- "radio"
- "checkbox"
- "date"
- "hidden"
- "number"
- "file"

as well as the following output data types:

- str
- float
- int
- list

The “input_field” key refers only to the structure of the markup field that will be used to collect the data; all the information regarding the typing and validation of the data exists in the “output_data” key. for each form, optional, non-form-field data is defined with an underscore (_) preceding the key name, like _allow_repeats. All of these are optional fields and default to a value of False.

Here is an example form “sample-form” with all the allowed form fields given as examples:

```python
# libreforms/forms/__init__.py: the source for form field data in the libreForms application.
import datetime
 
forms = {
"sample-form": {
    "Text_Field": {
        "input_field": {"type": "text", "content": ["NA"]},
        "output_data": {"type": "str", "validators": [lambda p: len(p) >= 6]},
       },
    "Pass_Field": {
        "input_field": {"type": "password", "content": [""]},
        "output_data": {"type": "str", "validators": []},
       },
    "Radio_Field": {
        "input_field": {"type": "radio", "content": ["Pick", "An", "Option"]},
        "output_data": {"type": "str", "validators": []},
       },
    "Check_Field": {
        "input_field": {"type": "checkbox", "content": ["Pick", "An", "Option"]},
        "output_data": {"type": "list", "validators": []},
       },
    "Date_Field": {
        "input_field": {"type": "date", "content": [datetime.datetime.today().strftime("%Y-%m-%d")]},
           # "input_field": {"type": "date", "content": []},
        "output_data": {"type": "date", "validators": []},
       },
    "Hidden_Field": {
        "input_field": {"type": "hidden", "content": ["This field is hidden"]},
        "output_data": {"type": "str", "validators": []},
       },
    "Float_Field": {
        "input_field": {"type": "number", "content": [0]},
        "output_data": {"type": "float", "validators": []},
       },
    "Int_Field": {
        "input_field": {"type": "number", "content": [0]},
        "output_data": {"type": "int", "validators": []},
       },
#      "File_Field": {
#          "input_field": {"type": "file", "content": [None]}, # still need to review https://flask.palletsprojects.com/en/2.1.x/patterns/fileuploads/
#          "output_data": {"type": TBD, "validators": []},
#         },
    "_dashboard": {             # defaults to False
        "type": "scatter",      # this is a highly powerful feature but requires
        "fields": {             # some knowledge of plotly dashboards; currently
            "x": "Timestamp",   # only line charts with limited features supported
            "y": "Num_Field",
            "color": "Text_Field"
           }
       },
    "_allow_repeat": False, # defaults to False
    "_allow_uploads": False, # defaults to False
    "_allow_csv_templates": False, # defaults to False
   },
}
```

The application presumes that authentication is set in place & adds the following to each database write:

    - _id: unique id for each db write
    - Reporter: the username of the reporting user
    - Timestamp: the timestamp that the form was submitted


