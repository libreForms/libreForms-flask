# signed URLs allow people to request / be invited to complete a form. 
# Scenario 1 (self initiated): anon. user goes to form page, provides email, and receives a signed link to complete. 
# Scenario 2 (invitation): current user invites another (by email) to complete a form, and the system sends a signed link over email

# we also want to consider the use case for API keys, which will be sufficiently similar to signed URLs to justify handling them
# in the same database. Signed URLs are single use, while API keys are multi use (meaning we can expect there will be fewer of them
# in circulation at any given time).

# finally, there are all sort of other use cases for signing keys, like new user email verification and 'forgot password' functionality
# where it would make sense to have a much shorter expiry

# Structure of the signed URL / API key
# 1. signature - nXhcCzeeY179SemdGtbRyWUC
# 2. timestamp - time of creation
# 3. expiration - 1 year default for API keys, 24 hours for signing keys . Do we want this to be relative (one year) or absolute (august 3rd, 2023, at 4:32.41 Zulu)
# 4. email address - yourName@example.com
# 5. scope - what resources does this give access to? form name? API? Read / Write?
# 6. active - bool, has this been marked expired? we want to keep it in the database for some time to avoid premature re-use and collision.

import os, datetime
import pandas as pd
from app import display, log, db, mailer
from app.models import Signing

# here we generate a signing key with a default length of 24
def generate_key(length=24):
    key = ''
    while True:
        temp = os.urandom(1)
        if temp.isdigit() or temp.isalpha():
            key = key + temp.decode("utf-8") 
        if len(key) == length:
            return key

# where `expiration` should be set to a relative time in hours
# where `scope` should be set to some subset of options like 'form - [form_name]', 
# 'api_key - [r/w]', 'email_verification', or 'forgot_password'
def write_key_to_database(scope=None, expiration=1, active=1, email=None):
    key = generate_key()
    # write to db if no collision

    while True:
        key = generate_key()
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
    log.info(f'LIBREFORMS - successfully generated key {key} for {email}.')

    return key

# this is a function that will periodically scan
# the keys in the database and flush any that have
# expired.
def flush_key_db():
    signing_df = pd.read_sql_table("signing", con=db.engine.connect())

    # This will disable all keys whose 'expiration' timestamp is less than the current time
    signing_df.loc[ signing_df['expiration'] < datetime.datetime.timestamp(datetime.datetime.now()), 'active' ] = 0

    # this will write the modified dataset to the database
    signing_df.to_sql('signing', con=db.engine.connect(), if_exists='replace', index=False)
    return signing_df
  
# here we create a mechanism to disable keys when they are used
def expire_key(key=None):

    # I wonder if there is a more efficient way to accomplish this ... eg. to simply modify 
    # the entry at the query stage immediately below...
    if Signing.query.filter_by(signature=key).first():

        signing_df = pd.read_sql_table("signing", con=db.engine.connect())

        # This will disable the key
        signing_df.loc[ signing_df['signature'] == key, 'active' ] = 0

        # this will write the modified dataset to the database
        signing_df.to_sql('signing', con=db.engine.connect(), if_exists='replace', index=False)
        return signing_df
    
    else:
        log.error(f"LIBREFORMS - attempted to expire key {key} but failed to locate it in the signing database.")



def distribute_key(key=None):
    pass