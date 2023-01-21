""" 
models.py: defining the models for the application's SQL database

This script defines the data models for two databases: (1) the user 
database, which is used to store local auth data; (2) the signing
database, which is used to store signatures / keys for various uses, 
including RESTful API access, email verification, & password resets. 

# User database

The code that implements this database is stored app/__init__.py 
and app/auth.py. When Gunicorn is used, it will create the database
using behavior defined in etc/gunicorn.conf.py to avoid collision. 
Specifically, the model creates a default user 'libreforms' for initial
access to the web application. When used, Gunicorn will create this user
before forking into multiple process to prevent errors from multiple 
workers trying to create the same user. Further, if custom user fields 
have been defined in the application's configuration file, these will 
be added to the database at the point of instantiation, see 
app/__init__.py and etc/gunicorn.conf.py.

To avoid too many changes to the user data model while still allowing
granular access to forms, visualizations, and other features, we impose
a one-to-one mapping of users to groups; put another way, every user will 
only have one group see https://github.com/signebedi/libreForms/issues/16.
As can be seen from the discussion there, the simple design means that we
should be aware of some default behavior: groups are allowed access to all
forms, fields, dashboards, tables, and other resources by default unless 
explicitly denied using a `deny_group_access` config at that resource's level.

# Signing database

The code that implements this database is stored in app/signing.py, 
app/__init__.py, and app/auth.py. 

The signing database sets the `signature` field to be the primary key. 
This approach ensures that each signature is unique, and thus prevents
'collisions' where a key is reused and allows some kind of leakage or
improper access. Generally, we link an `email` (Nb. this is not a required
field) to each row of data to ensure that some level of authentication 
still exists. We also implement a `scope` field to describe the purpose
in a machine-readable manner, see app/signing.py for more information.
The `active` field is a bool that determines whether a signature has been
'used up'. All signatures are made inactive when their `expiration` has 
passed, while some will expire after a certain number of uses - this depends
on the `scope` that has been defined, see app/signing.py for more information.
Generally, a signature row will not be dropped from the database; instead, 
its `active` field will be set to 0. This helps avoid a subset of potential 
collisions where users who previously obtained a signature can reuse it to
improperly access a future user's scope. This risk is exacerbated because
signatures are documented through users' emails and logs, meaning they 
may retain access to the signature after it has expired.


# Report database

Reports are implemented in app.reporting and views are generated in 
app.views.reports. In the web application, there are two forms of reports:
(1) administrator-defined reports, which are defined in the app config, and 
which have customizable circulation; (2) user-defined reports, which are
defined by users in the web application, and which only circulate reports
to the requesting user. This data model only handles the latter.

Reports stored in this database are given a unique `report_id`, which serves
as the table's primary key. Each report is linked to the requesting `user_id`.
The `frequency` field determined the send frequency (daily, weekly, monthly)
Any logic conditions / filters are stored as strings in the `filters` field,
and assessed by application logic. The `timestamp` stores the time the report
is created, while `start_at` and `end_at` are two optional fields that, if 
specified, will tailor when the reports start and stop sending. The `active`
field will determine whether the report is actively sending or disabled.

"""

__name__ = "app.models"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi",]
__version__ = "1.2.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from flask import current_app
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True) 
    email = db.Column(db.String(100))
    password = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True)
    group = db.Column(db.String(1000))
    organization = db.Column(db.String(1000))
    phone = db.Column(db.String(1000))
    # certificate = db.Column(db.String(100))
    certificate = db.Column(db.LargeBinary())
    theme = db.Column(db.String(100))
    active = db.Column(db.Integer)
    created_date = db.Column(db.String(1000))


class Signing(db.Model):
    __tablename__ = 'signing'
    signature = db.Column(db.String, primary_key=True) 
    email = db.Column(db.String(100))
    scope = db.Column(db.String(100))
    active = db.Column(db.Integer)
    timestamp_human_readable = db.Column(db.String(100))
    expiration_human_readable = db.Column(db.String(100))
    timestamp = db.Column(db.Float)
    expiration = db.Column(db.Float)


class Report(db.Model):
    __tablename__ = 'report'
    report_id = db.Column(db.Integer, primary_key=True) 
    # user_id = db.Column(db.Integer) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) # we link the report to the user_id of the user who created to report
    name = db.Column(db.String(100))
    form_name = db.Column(db.String(100))
    filters = db.Column(db.String(100))
    frequency = db.Column(db.Enum('hourly', 'daily', 'weekly', 'monthly', 'yearly'))
    active = db.Column(db.Boolean)
    timestamp = db.Column(db.Float)
    start_at = db.Column(db.Float) # this is an optional timestamp for when we'd like this report to go into effect
    end_at = db.Column(db.Float) # this is an optional timestamp for when we'd like this report to stop sending / expire (set `active` > False)
