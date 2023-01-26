""" 
mongo.py: creates a class for managing MongoDB form backends 

This script defines a class for managing a MongoDB database backend,
which is the default form datastore in the base application. The base
application should, in the long-run, be written to be totally abstract
as to the application used to store data; in reality, however, it is 
strongly tied to using MongoDB. 

# Form Data Structure

Beyond form-specific data, the application adds the following metadata:
    - Journal:
    - Metadata: what sets this struct apart from others is that its content is 
        generally not meant to be visible when the form is rendered 
    - Timestamp:
    - Reporter:
    - Owner:
    - Signature:
    - IP_Address:
    - Approver:
    - Approval:
    - Approver_Comment:

# class MongoDB()

This connects, by default, to a local MongoDB server with user 'root' and
on port 27017. Administrators can over ride these defaults using the 
'mongodb_user', 'mongodb_host', and 'mongodb_port' application configs.

# `with MongoClient()`

Leaving the MongoClient connection open for the lifespan of the MongoDB 
object is not feasible given that MongoDB is not write safe in a multi-
worker environment like WSGI, see:

    1. https://stackoverflow.com/a/73169147
    2. https://stackoverflow.com/a/18401169

and the following issue: https://github.com/signebedi/libreForms/issues/128. 

As a result, we use context management and re-establish the connection at each 
transaction. 'Is this efficient?' you ask inquisitively. If the MongoDB server
is hosted on the same server, it probably will not be an issue. There may be 
some latency issues with this approach at scale with an externalized database, 
but we'll cross this bridge when we come to it. 


# collections()

This returns a list of current collections (or forms) stored in the MongoDB
database. It's a useful shorthand to test whether an active form has received
any submissions, and whether an inactive form has past submissions still in 
the system - especially, in the latter case, when administrators are migrating
or cleaning up data.


# write_document_to_collection()

This is the bread-and-butter of the web application's MongoDB wrapper library 
by defining the application's behavior when writing a form submission to the 
database.

We start by asking whether this is a new submission (from app.views.forms), or a 
modification to an existing form (coming from app.views.submissions). If it's a new 
submission, we assign the same value to `Reporter` and `Owner`, and then create
the `Journal` using a carbon copy of the form data, except for the timestamp, 
which is used for the `Journal` unique key. If the web application has sent data
about digital signatures and approvals, then we include those as well. If the
submission is a modification, then we overwrite the data that changed and save 
the differences to the `Journal` with a new timestamp; this will also wipe out 
any past approvals / signatures that the form had received.


# read_documents_from_collection()

This method returns a list of documents for a given collection / form name. This is 
used primarily in app.views.submissions (see the wrapper function get_record_of_submissions
in app.views.submissions) when querying submissions for a given form. It's generally useful
when examining data at a form-by-form level. For example, maybe an administrator has 
some form `B-207: request for leave`, and they want to examine longitudinal data about
leave requests, especially when employees tend to make the most requests, to ensure 
management can make informed staffing decisions around these periods. An administrator 
can simply invoke this method, with the form name as an argument, and get a list of each
unique form submission for this form that they can parse using any data science toolkit 
they might choose.


# is_document_in_collection(collection_name, document_id)

This function returns True if the collection_name exists in the MongoDB database and 
there is corresponding document_id in the collection.


# check_connection()

This method will simply attempt to connect to the database and, if successful, return
True, else False. This is useful for system health checks.

# make_connection()
This method is a context-managed shorthand to reduce boilerplate when establishing new
connections to the database.

    @contextlib.contextmanager
    def make_connection(self, *args, **kwargs):
        try:
            client = MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string)
            yield client
        finally:
            client.close()

# get_document()

This method is a little heavy, but will get a document when you pass the collection and
document_id. 



# Errors

We've been noticing some `connection refused` errors in different environments. This might be 
due to the authentication string we're using. We should consider switching out:

# with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(f'mongodb://{self.user}:{self.dbpw}@{self.host}:{str(self.port)}/?authSource=admin&retryWrites=true&w=majority') as client:

with something more like:

# with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(f'mongodb://{self.user}:{self.dbpw}@{self.host}:{str(self.port)}{"/?authSource=admin&retryWrites=true&w=majority" if self.dbpw not in [None, ""] else ""}') as client:

Then again, it might just be a problem with this: https://stackoverflow.com/a/34711892/13301284.

"""

__name__ = "app.mongo"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi",]
__version__ = "1.3.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from pymongo import MongoClient
import os
import contextlib
import pandas as pd
import datetime
from bson.objectid import ObjectId
from app.config import config



class MongoDB:
    def __init__(self, user='libre', host='localhost', port=27017, dbpw=None):
        self.user=user 
        self.host=host 
        self.port=port 

        if not dbpw and os.path.exists ("mongodb_creds"):
            with open("mongodb_creds", "r") as f:
                self.dbpw = f.read().strip()
        else:
            self.dbpw=dbpw

        self.connection_string = f'mongodb://{self.user}{":"+self.dbpw if self.dbpw else ""}{"@"+self.host if self.user else self.host}:{str(self.port)}/?authSource=admin&retryWrites=true&w=majority'
        # print(self.dbpw)

    def collections(self):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
            db = client['libreforms']

            collections = db.list_collection_names()

            return collections

    # def close(self, self.client):
    #     return self.client.close()

    # def connect(self):
    #     self.client = MongoClient(self.host, self.port)
    #     return self.client['libreforms']

    def write_document_to_collection(self, data, collection_name, 
                                                    reporter=None,
                                                    # the `modifications` kwarg expects a truth statement
                                                    # presuming that `data` will just be a slice of changed data
                                                    modification=False,
                                                    digital_signature=None,

                                                    # there are currently a significant number of approver fields
                                                    # that might make sense to hash into a dictionary ... 
                                                    approver=None,
                                                    approval=None,
                                                    approver_comment=None,
                                                    ip_address=None):

        # to solve `connection paused` errors when in a forked
        # evironment, we connect and close after each write,
        # see https://github.com/signebedi/libreForms/issues/128        
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
            db = client['libreforms']

            collection = db[collection_name]

            timestamp_human_readable = str(datetime.datetime.utcnow())

            

            data['Reporter'] = str(reporter) if reporter else None

            # Adding the digital Signature back to Journal now that we have added badges to the user 
            # submission history view - making it more user friendly to view and make sense of, 
            # see https://github.com/signebedi/libreForms/issues/141.
            if digital_signature:
                data['Signature'] = digital_signature

            # Adding an optional `approval` field, which is similar to the `digital_signature`
            # field above - namely, in form management there is a common process where forms are
            # prepared by an individual making a request / proposal, and then an individual with 
            # the authority to review and approve this form does so. We also add an optional 
            # approver comment, see https://github.com/signebedi/libreForms/issues/8.
            if approver:
                data['Approver'] = approver

                # generally, we will (and should) only ever pass an `approver` during initial
                # form submission; in those circumstances where we might pass it again, it's
                # probably going to be a 'change-in-manager' situation that warrants - possibly -
                # an overwrite of the Approval and Approver Comment ... in any account, we ought
                # create those fields blank here to ensure that the logic contained in 
                # submissions.generate_full_document_history() doesn't break ... because all the 
                # fields contained therein need to be contained in an earlier field, see the problem
                # here: https://github.com/signebedi/libreForms/issues/145. It may be that this is 
                # just a temporary fix until we can figure out the logic the generate_full_document_history().
                # data['Approval'] = None
                # data['Approver_Comment'] = None

            # trying a slightly different approach to allow easy overwriting of previously-set Approval 
            # data, see https://github.com/signebedi/libreForms/issues/149. This logic reads the approval
            # and approver_comment kwargs, but drops them if None... I think this will induce desired behavior.
            data['Approval'] = approval
            if not ['Approval']:
                del data['Approval']

            data['Approver_Comment'] = approver_comment
            if not ['Approver_Comment']:
                del data['Approver_Comment']

            # here we collect IP addresses if they have been provided, see 
            # https://github.com/signebedi/libreForms/issues/175.
            data['IP_Address'] = ip_address
            if not ['IP_Address']:
                del data['IP_Address']

            # setting the timestamp sooner so it's included in the Journal data, perhaps removing the
            # need for a data copy.
            data['Timestamp'] = timestamp_human_readable

            # but we create a copy anyways to keep things segmented and avoid potential
            # recursion problems.
            data_copy = data.copy()

            # here we define the behavior of the `Journal` metadata field 
            if not modification:
                # we create an `Owner` field to be more stable than the `Reporter`
                # field - that is, something that does not generally change.
                # See  https://github.com/signebedi/libreForms/issues/143
                data['Owner'] = data['Reporter']
                data_copy['Owner'] = data_copy['Reporter']
                
                data['Journal'] = { timestamp_human_readable: data_copy }

                # In the past, we added an `initial_submission` tag the first time a form was submitted
                # but this is probably very redundant, so deprecating it here. 
                # data['Journal'][timestamp]['initial_submission'] = True 


                # here we add a `Metadata` field, which is implemented per discussion in 
                # https://github.com/signebedi/libreForms/issues/175 to capture form meta
                # data not well suited to the `Journal`.
                data['Metadata'] = {}

                # if the form is submitted with new digital signature or approval data,
                # then we attach related metadata
                if digital_signature:
                    data['Metadata']['signature_timestamp'] = timestamp_human_readable
                    if ip_address:
                        data['Metadata']['signature_ip'] = ip_address

                if approval:
                    data['Metadata']['signature_timestamp'] = timestamp_human_readable
                    if ip_address:
                        data['Metadata']['signature_ip'] = ip_address

            
            # here we define the behavior of the `Journal` metadata field 
            # if not modification:
                # data['Journal'] = { data['Timestamp']: {
                #                                         'Reporter': data['Reporter'],
                #                                         'initial_submission': True}
                #                                         }

                return str(collection.insert_one(data).inserted_id)

            else:

                # some very overkill slicing to get the original 'Journal' value...
                TEMP = self.read_documents_from_collection(collection_name)

                df = pd.DataFrame(list(TEMP))
                data['Journal'] = dict(df.loc[ (df['_id'] == data['_id'])]['Journal'].iloc[0])
                # print("\n\n\n", data['Journal'])
                # print("\n\n\n", type(data['Journal']))

                # we create a slice of the data to pass to the `Journal`
                journal_data = data.copy()
                del journal_data['_id']
                del journal_data['Journal']

                # Adding the digital Signature back now that we have added badges to the user 
                # submission history view, see https://github.com/signebedi/libreForms/issues/141.

                # if 'Signature' in journal_data.keys(): # delete the digital signature from the Journal if it exists 
                #     del journal_data['Signature']

                # print("\n\n\n", journal_data)

                # some inefficient slicing and voila! we have our correct `Journal` values, 
                # which we append to the `Journal` field of the parent dataframe
                data['Journal'][data['Timestamp']] =  dict(journal_data)
                # print(final_data['Journal'])

                # create Metadata field if it doesn't exist
                if 'Metadata' not in data:
                    data['Metadata'] = {}

                # if the form is submitted with new digital signature or approval data,
                # then we attach related metadata
                if digital_signature:
                    data['Metadata']['signature_timestamp'] = timestamp_human_readable
                    if ip_address:
                        data['Metadata']['signature_ip'] = ip_address

                if approval:
                    data['Metadata']['approval_timestamp'] = timestamp_human_readable
                    if ip_address:
                        data['Metadata']['approval_ip'] = ip_address


                collection.update_one({'_id': ObjectId(data['_id'])}, { "$set": data}, upsert=False)

                return str(data['_id'])



    def read_documents_from_collection(self, collection_name):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
            db = client['libreforms']

            collection = db[collection_name]
            return list(collection.find())

    def new_read_documents_from_collection(self, collection_name):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:

            # if the collection doesn't exist, return false
            if collection_name not in self.collections():
                return False

            db = client['libreforms']

            collection = db[collection_name]
            return pd.DataFrame(list(collection.find()))


    def is_document_in_collection(self, collection_name, document_id):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
            db = client['libreforms']

            # if the collection doesn't exist, return false
            if collection_name not in self.collections():
                return False

            # if an invalid ObjectID is passed, return false
            try:
                assert(ObjectId(document_id))
            except Exception as e: 
                return False

            collection = db[collection_name]
            df = pd.DataFrame(list(collection.find()))

            # print(df)

            # we return True if the form exists
            return True if len(df.loc[df['_id'] == ObjectId(document_id)]) > 0 else False

    def get_document(self, collection_name, document_id):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
            db = client['libreforms']

            # if the collection doesn't exist, return false
            if collection_name not in self.collections():
                return False

            # if an invalid ObjectID is passed, return false
            try:
                assert(ObjectId(document_id))
            except Exception as e: 
                return False

            collection = db[collection_name]
            df = pd.DataFrame(list(collection.find()))

            # print(df)

            # we return True if the form exists
            document = df.loc[df['_id'] == ObjectId(document_id)]
            return document.iloc[0].to_dict() if len(document) > 0 else False



    def check_connection(self):
        try:
            with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
                return True
        except Exception as e: 
            return False


# create the mongodb instance that the rest of the application will connect from
mongodb = MongoDB(user=config['mongodb_user'], 
                        host=config['mongodb_host'], 
                        port=config['mongodb_port'], 
                        dbpw=config['mongodb_pw'])