from flask_login import UserMixin
from app import db
from app.display import display


# class A(object):
#     def __init__(self, foo, bar=3):
#         self.foo = foo
#         self.bar = bar

# class B(A):
#     def __init__(self, quux=6, **kwargs):
#         super(B, self).__init__(**kwargs)
#         self.quux = quux


class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100))
    password = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True)
    organization = db.Column(db.String(1000))
    phone = db.Column(db.String(1000))
    created_date = db.Column(db.String(1000))

    def __init__(self, **kwargs):

        # super(User, self).__init__(**kwargs)

        for key, value in kwargs.items():
            self[key] = value



class Signing(db.Model):
    # id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    signature = db.Column(db.String, primary_key=True) # by making the signature the primary key, can we solve for collisions?
    email = db.Column(db.String(100))
    scope = db.Column(db.String(100))
    active = db.Column(db.Integer)
    timestamp = db.Column(db.String(100))
    expiration = db.Column(db.String(100))


## trying to add support for arbitary user form fields defined in overrides file
# class User(UserMixin, db.Model):
#     def __init__(self, user_registration_fields=display.user_registration_fields):    
#         self.id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
#         self.email = db.Column(db.String(100))
#         self.password = db.Column(db.String(100))
#         self.username = db.Column(db.String(100), unique=True)
#         self.organization = db.Column(db.String(1000))
#         self.phone = db.Column(db.String(1000))
#         self.created_date = db.Column(db.String(1000))

#         if display.user_registration_fields:
#             for key in display.user_registration_fields.keys():
#                 self[key] = db.Column(db.String(100)) if isinstance(display.user_registration_fields[key], [str, list, tuple]) else None
#                 self[key] = db.Column(db.Int(100)) if isinstance(display.user_registration_fields[key], [int]) else None
