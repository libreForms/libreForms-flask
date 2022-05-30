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
