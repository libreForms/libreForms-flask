![header img](docs/header_img_large.png)

# libreForms
an open form manager API

## contents
1. [about](#about)
    - [use cases](#use-cases)
    - [features](#features)
2. [installation](#installation)
    - [RHEL 8](#rhel-8)
    - [Ubuntu 20.04](#ubuntu-2004)
3. [API](#api)
4. [extensibility](#extensibility)
5. [selectors](#selectors)
6. [database](#database)
7. [dashboards](#dashboards)
8. [display overrides](#display-overrides)
9. [dependencies](#dependencies)
10. [copyright](#copyright)

## about

Liberate your forms with libreForms, an open form manager API that's intended to run in your organization's intranet. Most browser-based form managers lack key features, direct control over the underlying application, self-hosting support, a viable cost/licensing model, or lightweight footprints. The libreForms project, first and foremost, defines a simple but highly extensible abstraction layer that matches form fields to backend data structures. It adds a browser-based application, document-oriented database, and RESTful API on top of this. 

### use cases

- You are a small enterprise that has been using Google Forms for your organization's internal forms because it is low-cost, but you dislike the restricted features and lack of direct control over your data.

- You are a medium-sized enterprise that wants a simple, low-cost tool to manage their internal forms. You don't mind self-hosting the application, and you have staff with rudimentary experience using Python to deploy and maintain the system.

- You are a large enterprise with significant technical staff that routinely host and maintain applications for use on your organization's intranet. You have assessed options for form managers on the market and determined that proprietary services provide little direct control over the application source code, or otherwise fail to provide a viable licensing model.

### features

- a form-building abstraction layer based on Python dictionaries
- a flask web application (http://x.x.x.x:8000/) that employs pandas dataframes and plotly dashboards for data visualization & works well with most standard reverse-proxies
- a document-oriented database to store form data 
- \[future\] local and SAML authentication options
- \[future\] support for lookups in form fields, and routing lists for form review, approvals, and notifications

## installation

In most cases, the following commands must be run with root privileges.

### RHEL 8

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
systemctl enable --now mongodb
```

1. Download the last stable release of this repository into the opt directory:

```
cd /opt
wget https://github.com/signebedi/libreForms/archive/refs/tags/v0.0.1-alpha.tar.gz
tar -xvf v0.0.1-alpha.tar.gz
mv libreforms-v0.0.1-alpha libreForms
```

2. install Python virtual environment

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

4. systemd service

```
cp /opt/libreForms/gunicorn/libreforms.service /etc/systemd/system
systemctl daemon-reload
systemctl enable --now libreforms
```

### Ubuntu 20.04

0. install dependencies

```
apt update -y && apt upgrade -y
apt install -y mongodb python3-pip python3-venv # for the most up to date version of mongodb, see https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/
systemctl enable --now mongodb
```

1. Download the last stable release of this repository into the opt directory:

```
cd /opt
wget https://github.com/signebedi/libreForms/archive/refs/tags/v0.0.1-alpha.tar.gz
tar -xvf v0.0.1-alpha.tar.gz
mv libreforms-v0.0.1-alpha libreForms
```

2. install Python virtual environment

```
cd /opt/libreForms
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. libreforms user

```
useradd --no-create-home --system libreforms
chown -R libreforms:libreforms /opt/libreForms
```

4. systemd service

```
cp /opt/libreForms/gunicorn/libreforms.service /etc/systemd/system
systemctl daemon-reload
systemctl enable --now libreforms
```

if you experience a failure when you check `systemctl status libreforms`, then try chowning the program files and restarting the application.

```
chown -R libreforms:libreforms /opt/libreForms
systemctl restart libreforms
```


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

## extensibility

If you'd like to extend the content of ```libreforms/forms/__init__.py```, you can do so by adding a file called ```libreforms/forms/add_ons.py```. This file should replicate the structure of `__init__.py` by defining a dictionary called ```forms``` conforming to the above API. The default behavior is for this dictionary to overwrite the ```forms``` dictionary defined in `__init__.py`. However, if for some reason it is preferrable to append the dictionary, this is stored in a dictionary called forms_appended (which can be called by importing from libreforms.forms.forms_appended instead of libreforms.forms.forms).

## selectors

libreForms allows users to tailor the data in their dashboards and tables using GET variabes as selectors. For example, when you define a dashboard for a given form, you need to set a dependent variable. However, this can be overridden by passing the ```?y=field_name``` GET variable in the browser. Likewise, you can tailor tabular data by passing the ```?FIELD_NAME=VALUE``` GET variable in the browser. Put another way, if a table has a field called ```Sub-Unit``` and another called Fiscal_Year, and you would like to tailor the table to only show data for the Finance sub-unit in the 2021 fiscal year, then you could pass the following GET variables: ```?Sub-Unit=Finance&Fiscal_Year=2021``` to select only this data.

## database

If you elect to password protect your database, which is recommended, you should drop a file in the application home directory named ```dbpw``` and ensure that the ```libreforms``` user has read access.

## dashboards

Right now, only line graphs are supported. In the future, the project plans to allow arbitrary dashboard configurations.

## display overrides

You can override some of the default site display options by adding a file called `site_overrides.py` to the project home directory. This file should contain a dictionary object with key-value attributes that you want to override. 

```
display = {
    'site_name':"My-Site",
    'homepage_msg': "Welcome to My-Site. Select a view from above to get started.",
    'warning_banner':"Please be mindful of the data you post on this system.",
    'favicon':"my_new_favicon.ico",
}
```

## dependencies

This application has a few dependencies that, in its current form, may be prone to obsolescence; there is an issue in the backlog to test for, among other things, obsolete dependencies. In addition to the standard requirements, like Python3, Python3-Pip, Python3-Venv, and MongoDB, here is a list of dependencies that ship with the application under the static/ directory:

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

## copyright

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
