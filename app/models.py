from flask_login import UserMixin
from app import db
from app.display import display



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100))
    password = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True)
    organization = db.Column(db.String(1000))
    phone = db.Column(db.String(1000))
    active = db.Column(db.Integer)
    created_date = db.Column(db.String(1000))


class Signing(db.Model):
    # id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    signature = db.Column(db.String, primary_key=True) # by making the signature the primary key, can we solve for collisions?
    email = db.Column(db.String(100))
    scope = db.Column(db.String(100))
    active = db.Column(db.Integer)
    timestamp_human_readable = db.Column(db.String(100))
    expiration_human_readable = db.Column(db.String(100))
    timestamp = db.Column(db.Float)
    expiration = db.Column(db.Float)
