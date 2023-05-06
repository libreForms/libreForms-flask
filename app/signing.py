""" 
signing.py: function set for managing signing keys and corresponding database operations

Signing keys, or signatures (we use these terms interchangeably), are used 
in various situations to authenticate a user when logging in - or even 
registering an account - are not reasonable expectations, but where we would 
still like to be able to strongly authenticate a user before a privileged 
behavior is permitted by the application. This script defines a set of 
operations to generate and manage these signatures using the signing database 
defined in app/models.py, which is a useful script to review for more 
information on the data model. 

# Scope

One point from the data model that will be useful to discuss here is the signature's 
`scope`, which is a field that describes the purpose of a given signature. We employ 
a mixed approach when using a `scope` to constrain a signature's use. For 
example, a signature's scope will not, in itself, be used to set the signature's 
expiration behavior - that is set when write_key_to_database() is invoked and
is defined alongside the signature's scope, see below for more information.
What this means in practice is that the end user retains the freedom to 
set the expiration behavior of different scopes or subsets of scopes. 

However, to prevent improper use of signatures, scopes may not be used for
interchangeable purposes, such that a signature with a scope of 'forgot_password'
cannot be used in an application function requiring a scope of 'email_verification'.
This is a common sense rule that is enforced through some boilerplate that should
be run everytime a signature is invoked. Take, for example, the following code from
app/auth.py, which verifies that a signature exists, that it is active and unexpired,
and that it contains the appropriate scope. Feel free to repurpose the code below for
additional views that may require signature validation. 

```
    if not Signing.query.filter_by(signature=signature).first():
        flash(flash_msg)
        return redirect(url_for(redirect_to))

    # if the signing key's expiration time has passed, then set it to inactive 
    if Signing.query.filter_by(signature=signature).first().expiration < datetime.datetime.timestamp(datetime.datetime.now()):
        signing.expire_key(signature)

    # if the signing key is set to inactive, then we prevent the user from proceeding
    # this might be redundant to the above condition - but is a good redundancy for now
    if Signing.query.filter_by(signature=signature).first().active == 0:
        flash(flash_msg)
        return redirect(url_for(redirect_to))

    # if the signing key is not scoped (that is, intended) for this purpose, then 
    # return an invalid error
    if not Signing.query.filter_by(signature=signature).first().scope == "forgot_password":
        flash(flash_msg)
        return redirect(url_for(redirect_to))
```

Notably, we added verify_signatures(), see below, to an abstract method to apply the logic above 
in a view.

Some scopes that this application implements - primarily located in app/auth.py,
app/api.py, and app/external.py are:

1.  api_key: the base application sets the expiration date at 365 days, and does not expire
    the key after a given use by default, though it does allow administrators to limit the 
    number of API keys a single user / email may register. 

    In the future, there may be some value in setting a dynamic scope for API keys, as in (4)
    below, to permit different sets of CRUD operations.

2.  forgot_password: the base application sets the expiration date at 1 hour, and expires the
    key after a single use.

3.  email_verification: the base application sets the expiration date at 48 hours, and expires 
    the key after a single use.

4.  external_{form_name.lower()}: the base application assesses external / anonymous form 
    submissions dynamically depending on the form name; it sets the expiration date at 48 
    hours and expires the key after a single use.


# generate_key(length=24) 

Generates and returns a signature string defaulting to 24 characters in length.

In the base application, this method is called almost exclusively by write_key_to_database(), 
see below. It made sense to externalize it, however, because there are a reasonable and abstract
set of uses for this function outside the context of the application's signing database and
corresponding data model. It takes a single parameter `length`, which is an integer corresponding
to the length of the signature that the function generates and returns. 


# write_key_to_database(scope=None, expiration=1, active=1, email=None)

Connector function that generates a signature entry conforming to the signing data model.

For more explanation of `scope`, see the corresponding section above. The `expiration` should
be set in hours relative to the current timestamp. Setting signatures to `active` by default
when no futher action is needed to enable them. Setting `email` to None by default may be a
bug or feature, depending on context. Either way, future code revisions may choose to modify 
this behavior to require an email to be set - but then it may break instances where emails are 
not required, or where the 'libreforms' user continues to not have an email set. 


# flush_key_db()

Disables any signatures in the signing database whose expiration timestamp has passed.

In the base application, this method remains largely unimplemented in favor of 
expire_key(), see below. That is because there is no plausible trigger for it -
even though it is theoretically / potentially more efficient than expire_key(),
especially when it catches & expires multiple signatures whose expirations have
passed. 

Implementation probably makes more sense if we can run it asynchronously and
thus trigger on a schedule instead of by an event. For example, maybe we query 
the signing database every hour (since this is the lowest possible increment 
expiration increment), select the row with the lower value for `expiration` 
where active == 1 (so we're selecting the next key set to expire). Then,
we create a single croniter schedule, as in app/reports.py and pass this 
to a timed asynchronous function. Or maybe we just string this without 
running hourly checks - that might be overkill. This allows some degree of
precision in expiring keys.


# expire_key(key=None)

Expire a specific key without any logic or verification.

In the base application, this method is used to expire a specific key. It is 
primarily used when each signature is invoked in the client; take, this example 
from the `scope` section above:

    # if the signing key's expiration time has passed, then set it to inactive 
    if Signing.query.filter_by(signature=signature).first().expiration < datetime.datetime.timestamp(datetime.datetime.now()):
        signing.expire_key(signature)

Make note, all logic determining whether the key should be expired is external to 
this method; it only takes a key as a parameter and expires it.

# def verify_signatures(signature, # the key to validate
                            scope, # what scope the signature should be validated against
                            redirect_to='home', # failed validations redirect here unless abort_on_errors=True
                            flash_msg="Invalid request key. ", # failed validations give msg unless abort_on_errors=True
                            abort_on_error=False, # if True, failed validations will return a 404):

Verify an individual signature and return None if it passes.

In the base application, this function requires two parameters: a `signature` string and a 
`scope` to validate against the database. It has optional parameters to set where to `redirect_to`
on errors, what `flash_msg` to show the user when a key validation fails, and a bool option to 
have the view return a 404 error when key validation fails.

This functiom applies the logic discussed in the `Scope` section above. You would include in a view in
one of two ways: first, as a conditional:

```
if not signing.verify_signatures(signature, scope="forgot_password"):
    return YOUR VIEW HERE
else:
    return abort(404)
```

Alternatively, if you set the `abort_on_error` option to True, then you can simply call it in your view
without needing to deal with nesting conditionals:

```
signing.verify_signatures(signature, scope="forgot_password", abort_on_error=True)
return YOUR VIEW HERE
```

"""


__name__ = "app.signing"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi",]
__version__ = "2.1.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

import os, datetime, secrets, threading, time, functools
import pandas as pd
from flask import current_app, flash, redirect, url_for, abort
from app import config, log
from app.models import Signing, db

# here we generate a signing key with a default length of 24
def generate_key(length:int=24, urandom_method=False):
    if urandom_method:
        key = ''
        while True:
            temp = os.urandom(1)
            if temp.isdigit() or temp.isalpha():
                key = key + temp.decode("utf-8") 
            if len(key) == length:
                return key
    return secrets.token_urlsafe(length)


# maybe the `active` parameter should be set to bool ... again, this is a bug or feature,
# depending on context. 
def write_key_to_database(scope:str=None, expiration:int=1, active:int=1, email:str=None):


    # loop until a unique key is generated
    while True:
        key = generate_key(length=config['signing_key_length'])
        if not Signing.query.filter_by(signature=key).first(): break

    new_key = Signing(
                    signature=key, 
                    scope=scope.lower() if scope else "",
                    email=email.lower() if email else "", 
                    active=active,
                    expiration_human_readable=(datetime.datetime.utcnow() + datetime.timedelta(hours=expiration)).strftime("%Y-%m-%d %H:%M:%S") if expiration else 0,
                    timestamp_human_readable=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    timestamp=datetime.datetime.timestamp(datetime.datetime.now()),
                    expiration=datetime.datetime.timestamp((datetime.datetime.utcnow() + datetime.timedelta(hours=expiration))) if expiration else 0,
    )

    db.session.add(new_key)
    db.session.commit()
    log.info(f'LIBREFORMS - successfully generated key for {email}.')

    return key

# DEPRECATED in favor of key-by-key verification, see verify_signatures()
def flush_key_db():
    signing_df = pd.read_sql_table(Signing.__tablename__, con=db.engine.connect())

    # This will disable all keys whose 'expiration' timestamp is less than the current time
    signing_df.loc[ signing_df['expiration'] < datetime.datetime.timestamp(datetime.datetime.now()), 'active' ] = 0

    # this will write the modified dataset to the database
    signing_df.to_sql(Signing.__tablename__, con=db.engine.connect(), if_exists='replace', index=False)
    return signing_df

# DEPRECATED: I don't think this approach is particularly efficient anymore; instead, 
# we'll approach expiration on a key-by-key basis and potentially prepare an abstract function.

# class flushTimer:
#     def __init__(self, signing_df):
#             t = threading.Thread(target=self.sleep_until_next_expiration(signing_df))
#             t.start()
#             # executor.submit(self.sleep_until_next_expiration(signing_df))

#     def sleep_until_next_expiration(self, signing_df):
#         # while True:

#             # we take a slice to restrict down to active keys
#             active_keys = signing_df.loc[ signing_df.active == 1 ]

#             # we create a datetime object from the next expiration timestamp
#             next_expiration = datetime.datetime.fromtimestamp (
#                 active_keys.expiration.min()
#             # if there are no signing keys, then we check every minute
#             ) if len(active_keys.index > 0) else datetime.datetime.now()+datetime.timedelta(minutes=1)

#             # create an object measuring the amount of time until the next expiration
#             diff = next_expiration - datetime.datetime.now()

#             # sleep for the duration of the time difference measured above
#             time.sleep(diff.total_seconds())

#             flush_key_db()

# here we create a mechanism to disable keys when they are used
def expire_key(key=None):

    # I wonder if there is a more efficient way to accomplish this ... eg. to simply modify 
    # the entry at the query stage immediately below...
    if Signing.query.filter_by(signature=key).first():

        signing_df = pd.read_sql_table(Signing.__tablename__, con=db.engine.connect())

        # This will disable the key
        signing_df.loc[ signing_df['signature'] == key, 'active' ] = 0

        # this will write the modified dataset to the database
        signing_df.to_sql(Signing.__tablename__, con=db.engine.connect(), if_exists='replace', index=False)
        return signing_df
    
    else:
        log.error(f"LIBREFORMS - attempted to expire key {key} but failed to locate it in the signing database.")

# here we define an abstract set of operations that we want 
# to run everytime the end user attempts to invoke a   
def verify_signatures(      signature, # the key to validate
                            scope, # what scope the signature should be validated against
                            redirect_to='home', # failed validations redirect here unless abort_on_errors=True
                            flash_msg="Invalid request key. ", # failed validations give msg unless abort_on_errors=True
                            abort_on_error=False, # if True, failed validations will return a 404
                    ):

    if not Signing.query.filter_by(signature=signature).first():
        if abort_on_error:
            return abort(404)
        flash(flash_msg, "warning")
        return redirect(url_for(redirect_to))

    # if the signing key's expiration time has passed, then set it to inactive 
    if Signing.query.filter_by(signature=signature).first().expiration < datetime.datetime.timestamp(datetime.datetime.now()):
        expire_key(signature)

    # if the signing key is set to inactive, then we prevent the user from proceeding
    # this might be redundant to the above condition - but is a good redundancy for now
    if Signing.query.filter_by(signature=signature).first().active == 0:
        if abort_on_error:
            return abort(404)
        flash(flash_msg, "warning")
        return redirect(url_for(redirect_to))

    # if the signing key is not scoped (that is, intended) for this purpose, then 
    # return an invalid error
    if not Signing.query.filter_by(signature=signature).first().scope == scope:
        if abort_on_error:
            return abort(404)
        flash(flash_msg, "warning")
        return redirect(url_for(redirect_to))

    # Returning None is desirable. It means that we can run `if not verify_signatures():` 
    # as a way to require the check passes... This has allowed us to fix an improper access
    # bug that did not prevent users with keys in the signing db -- irrespective of whether
    # they were still active -- to access other resources.
    return None

