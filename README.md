# libreForms
an open form manager API

## features

- A form-building API based on Python dictionaries
- Gunicorn web server (http://x.x.x.x:8000/) that works well with Apache, Nginx, and other reverse-proxies
- MongoDB backend

## Installation

In most cases, the runtime commands below must be run with root privileges.

### Red Hat Enterprise Linux 8

0. install dependencies

```
# see https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-red-hat/
echo "[mongodb-org-5.0] 
name=MongoDB Repository 
baseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/5.0/x86_64/ 
gpgcheck=1 
enabled=1 
gpgkey=https://www.mongodb.org/static/pgp/server-5.0.asc" | tee /etc/yum.repos.d/mongodb-org-5.0.repo
yum update -y
yum install python3.8 mongodb-org -y
systemctl enable --now mongod
```

1. Download the last stable release of this repository into the opt directory:

```
cd /opt
wget https://github.com/signebedi/libreForms/archive/refs/tags/v0.0.1-alpha.tar.gz
tar -xvf v0.0.1-alpha.tar.gz
mv libreforms-v0.0.1-alpha libreForms
```

2. Install Python virtual environment

```
cd /opt/libreForms
python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. libreforms user

```
useradd --no-create-home --system libreforms
chown -R libreforms:libreforms /opt/libreForms
```


4. Systemd service

```
cp /opt/libreForms/gunicorn/libreforms.service /etc/systemd/system
systemctl daemon-reload
systemctl enable --now libreforms
```

### Ubuntu 20.04

0. install dependencies

```
apt install -y mongodb-org # for the most up to date version of mongodb, see https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/
systemctl enable --now mongod
```

1. Download the last stable release of this repository into the opt directory:

```
cd /opt
wget https://github.com/signebedi/libreForms/archive/refs/tags/v0.0.1-alpha.tar.gz
tar -xvf v0.0.1-alpha.tar.gz
mv libreforms-v0.0.1-alpha libreForms
```

2. Install Python virtual environment

```
cd /opt/libreForms
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. libreforms user

```
useradd --no-create-home --system libreforms
chown -R libreforms:libreforms /opt/libreForms
```

4. Systemd service

```
cp /opt/libreForms/gunicorn/libreforms.service /etc/systemd/system
systemctl daemon-reload
systemctl enable --now libreforms
```


## API

The purpose of the libreForms project is to provide a simple but highly extensible method of form building and management in Python, leveraging Flask's doctrine of 'simplicity and extensibility.' As a result, the application provides an API for storing all the information it needs to generate a browser-based form within a Python dictionary. The application then translates these form fields into data structures intended to be stored in a database. Given the project's emphasis on supporting arbitrary data structures, it writes data to a MongoDB database, creating a separate collection for each unique form with the presumption that the documents contained therein will adhere to a data structure that contains some set of common fields upon which data may be collated.

libreForms defines a robust abstraction layer between (1) the types of form fields that are used to collect user data and (2) the data type that the content of these form fields take, once submitted by the user, and (3) the underlying data structure of form responses, which the system stores in a JSON-like database well suited to integration with useful data science tools like pandas, as well as visualization libraries like plotly. Specifically, this API supports the following form fields:

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
        "output_data": {"type": "str", "validators": []},
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

## dependencies

This application has a few dependencies that, in its current form, may be prone to obsolescence; there is an issue in the backlog to unit test for, among other things, obsolete dependencies. In addition to the standard requirements, like Python3, Python3-Pip, Python3-Venv, and MongoDB, here is a list of dependencies that ship with the application under the static/ directory:

```
bootstrap-3.4.1.min.css
bootstrap-3.4.1.min.js
jquery-3.2.1.slim.min.js
jquery-3.5.1.min.js
plotly-v1.58.5.min.js

```

As well as the application's python requirements:
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

## Copyright

```
libreForms is an open form manager API
Copyright (C) 2022 Sig Janoska-Bedi

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```
