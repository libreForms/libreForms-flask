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
    - Access_Roster:

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

Issue references:
1. https://github.com/libreForms/libreForms-flask/issues/136
2. https://github.com/libreForms/libreForms-flask/issues/219

"""

__name__ = "app.mongo"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi",]
__version__ = "2.1.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from pymongo import MongoClient, TEXT
import os
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

        # prepare the connection string
        self.connection_string = f'mongodb://{self.user}{":"+self.dbpw if self.dbpw else ""}{"@"+self.host if self.user else self.host}:{str(self.port)}/?authSource=admin&retryWrites=true&w=majority'
        # print(self.dbpw)

        # set our metadata field names, see below
        self.set_metadata_field_names()

    # we set and update the class variable that will be used to set metadata field names, see
    # https://github.com/libreForms/libreForms-flask/issues/195
    def set_metadata_field_names(self,**kwargs):
        
        # we create a class variable called metadata_field_names
        self.metadata_field_names = {}
        
        # we set the default metadata field names

        self.metadata_field_names['journal'] = '_journal' # self.metadata_field_names['journal'] = 'Journal'
        self.metadata_field_names['metadata'] = '_metadata' # self.metadata_field_names['metadata'] = 'Metadata'
        self.metadata_field_names['ip_address'] = '_ip_address' # self.metadata_field_names['ip_address'] = 'IP_Address'
        self.metadata_field_names['approver'] = '_approver' # self.metadata_field_names['approver'] = 'Approver'
        self.metadata_field_names['approval'] = '_approval' # self.metadata_field_names['approval'] = 'Approval'
        self.metadata_field_names['approver_comment'] = '_approver_comment' # self.metadata_field_names['approver_comment'] = 'Approver_Comment'
        self.metadata_field_names['signature'] = '_signature' # self.metadata_field_names['signature'] = 'Signature'
        # self.metadata_field_names['access_roster'] = '_access_roster' # self.metadata_field_names['access_roster'] = 'Access_Roster'
        self.metadata_field_names['owner'] = '_owner' # self.metadata_field_names['owner'] = 'Owner'
        self.metadata_field_names['reporter'] = '_reporter' # self.metadata_field_names['reporter'] = 'Reporter'
        self.metadata_field_names['timestamp'] = '_timestamp' # self.metadata_field_names['timestamp'] = 'Timestamp'

        # we allow them to be overwritten using kwargs
        self.metadata_field_names.update(kwargs) 

        return self.metadata_field_names

    def metadata_fields(self, exclude_id:bool=False, ignore_fields:list=[]) -> list:
        
        # we have a number of fields that are added at various points in the 
        # submission lifecyle, but which we may wish to strip from the data. 
        # this method returns a list of those fields. By default, we do not
        # drop the `_id` field. Added ignore_fields to ignore fields by key
        # if they are passed, for cases where we want some metadata to remain
        fields = [ value for field,value in self.set_metadata_field_names().items() if field not in ignore_fields ]
        
        if exclude_id:
            return fields + ['_id']

        return fields


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

            data[self.metadata_field_names['reporter']] = str(reporter) if reporter else None

            # Adding the digital Signature back to Journal now that we have added badges to the user 
            # submission history view - making it more user friendly to view and make sense of, 
            # see https://github.com/signebedi/libreForms/issues/141.
            if digital_signature:
                data[self.metadata_field_names['signature']] = digital_signature

            # Adding an optional `approval` field, which is similar to the `digital_signature`
            # field above - namely, in form management there is a common process where forms are
            # prepared by an individual making a request / proposal, and then an individual with 
            # the authority to review and approve this form does so. We also add an optional 
            # approver comment, see https://github.com/signebedi/libreForms/issues/8.
            if approver:
                data[self.metadata_field_names['approver']] = approver

                # generally, we will (and should) only ever pass an `approver` during initial
                # form submission; in those circumstances where we might pass it again, it's
                # probably going to be a 'change-in-manager' situation that warrants - possibly -
                # an overwrite of the Approval and Approver Comment ... in any account, we ought
                # create those fields blank here to ensure that the logic contained in 
                # submissions.generate_full_document_history() doesn't break ... because all the 
                # fields contained therein need to be contained in an earlier field, see the problem
                # here: https://github.com/signebedi/libreForms/issues/145. It may be that this is 
                # just a temporary fix until we can figure out the logic the generate_full_document_history().
                # data[self.metadata_field_names['approval']] = None
                # data[self.metadata_field_names['approver_comment']] = None

            # trying a slightly different approach to allow easy overwriting of previously-set Approval 
            # data, see https://github.com/signebedi/libreForms/issues/149. This logic reads the approval
            # and approver_comment kwargs, but drops them if None... I think this will induce desired behavior.
            data[self.metadata_field_names['approval']] = approval
            if not data[self.metadata_field_names['approval']]:
                del data[self.metadata_field_names['approval']]

            data[self.metadata_field_names['approver_comment']] = approver_comment
            if not data[self.metadata_field_names['approver_comment']]:
                del data[self.metadata_field_names['approver_comment']]

            # here we collect IP addresses if they have been provided, see 
            # https://github.com/signebedi/libreForms/issues/175.
            data[self.metadata_field_names['ip_address']] = ip_address
            if not data[self.metadata_field_names['ip_address']]:
                del data[self.metadata_field_names['ip_address']]

            # setting the timestamp sooner so it's included in the Journal data, perhaps removing the
            # need for a data copy.
            data[self.metadata_field_names['timestamp']] = timestamp_human_readable

            # but we create a copy anyways to keep things segmented and avoid potential
            # recursion problems.
            # data_copy = data.copy()

            # here we define the behavior of the `Journal` metadata field 
            if not modification:

                # we create an `Owner` field to be more stable than the `Reporter`
                # field - that is, something that does not generally change.
                # See  https://github.com/signebedi/libreForms/issues/143
                data[self.metadata_field_names['owner']] = data[self.metadata_field_names['reporter']]
                # data_copy[self.metadata_field_names['owner']] = data_copy[self.metadata_field_names['reporter']]
                
                # but we create a copy anyways to keep things segmented and avoid potential
                # recursion problems.
                data[self.metadata_field_names['journal']] = { timestamp_human_readable: data.copy() }

                # In the past, we added an `initial_submission` tag the first time a form was submitted
                # but this is probably very redundant, so deprecating it here. 
                # data[self.metadata_field_names['journal']][timestamp]['initial_submission'] = True 

                # we create an access roster field that will set granular access, see
                # https://github.com/libreForms/libreForms-flask/issues/200. 
                # data[self.metadata_field_names['access_roster']] = {}

                # here we add a `Metadata` field, which is implemented per discussion in 
                # https://github.com/signebedi/libreForms/issues/175 to capture form meta
                # data not well suited to the `Journal`.
                data[self.metadata_field_names['metadata']] = {}

                # here we add a metadata subfield called 'created_timestamp', which will track the time
                # that the form was initially created ... allowing `Timestamp` to solely track the last
                # edit timestamp. For more discussion of this feature and how it supports filters, see
                # https://github.com/libreForms/libreForms-flask/issues/248
                data[self.metadata_field_names['metadata']]['created_timestamp'] = timestamp_human_readable 

                # if the form is submitted with new digital signature or approval data,
                # then we attach related metadata
                if digital_signature:
                    data[self.metadata_field_names['metadata']]['signature_timestamp'] = timestamp_human_readable
                    if ip_address:
                        data[self.metadata_field_names['metadata']]['signature_ip'] = ip_address

                if approval:
                    data[self.metadata_field_names['metadata']]['signature_timestamp'] = timestamp_human_readable
                    if ip_address:
                        data[self.metadata_field_names['metadata']]['signature_ip'] = ip_address

                        # we add the approver to the access roster with `approver` level permissions
                        # data[self.metadata_field_names['access_roster']][approver] = 'approver'
                
                # we add the owner to the access roster with `owner` level permissions
                # data[self.metadata_field_names['access_roster']][reporter] = 'owner'

            
            # here we define the behavior of the `Journal` metadata field 
            # if not modification:
                # data[self.metadata_field_names['journal']] = { data[self.metadata_field_names['timestamp']]: {
                #                                         'Reporter': data['Reporter'],
                #                                         'initial_submission': True}
                #                                         }

                # print(data)
                return str(collection.insert_one(data).inserted_id)

            else:

                # some very overkill slicing to get the original 'Journal' value...
                TEMP = self.read_documents_from_collection(collection_name)
                
                df = pd.DataFrame(list(TEMP))
                data[self.metadata_field_names['journal']] = dict(df.loc[ (df['_id'] == data['_id'])][self.metadata_field_names['journal']].iloc[0])
                # print("\n\n\n", data[self.metadata_field_names['journal']])
                # print("\n\n\n", type(data[self.metadata_field_names['journal']]))

                # we create a slice of the data to pass to the `Journal`
                journal_data = data.copy()
                del journal_data['_id']
                del journal_data[self.metadata_field_names['journal']]

                # Adding the digital Signature back now that we have added badges to the user 
                # submission history view, see https://github.com/signebedi/libreForms/issues/141.

                # if mongodb.metadata_field_names['signature'] in journal_data.keys(): # delete the digital signature from the Journal if it exists 
                #     del journal_data[self.metadata_field_names['signature']]

                # print("\n\n\n", journal_data)

                # some inefficient slicing and voila! we have our correct `Journal` values, 
                # which we append to the `Journal` field of the parent dataframe
                data[self.metadata_field_names['journal']][data[self.metadata_field_names['timestamp']]] =  dict(journal_data)
                # print(final_data[self.metadata_field_names['journal']])

                # create Metadata field if it doesn't exist
                if self.metadata_field_names['metadata'] not in data:
                    data[self.metadata_field_names['metadata']] = {}

                # if the form is submitted with new digital signature or approval data,
                # then we attach related metadata
                if digital_signature:
                    data[self.metadata_field_names['metadata']]['signature_timestamp'] = timestamp_human_readable
                    if ip_address:
                        data[self.metadata_field_names['metadata']]['signature_ip'] = ip_address

                if approval:
                    data[self.metadata_field_names['metadata']]['approval_timestamp'] = timestamp_human_readable
                    if ip_address:
                        data[self.metadata_field_names['metadata']]['approval_ip'] = ip_address


                collection.update_one({'_id': ObjectId(data['_id'])}, { "$set": data}, upsert=False)

                # print(data)
                return str(data['_id'])


    def read_documents_from_collection(self, collection_name):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
            db = client['libreforms']

            collection = db[collection_name]
            return list(collection.find())

    #  this new version returns a pandas dataframe instead of a list
    def new_read_documents_from_collection(self, collection_name):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:

            if collection_name in self.collections():

                db = client['libreforms']

                collection = db[collection_name]
                return pd.DataFrame(list(collection.find()))

            # if the collection doesn't exist, return false
            return False

    #  this new version returns a list of columns, except those passed as args
    def get_collection_columns(self, collection_name, *args):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:

            if collection_name in self.collections():

                db = client['libreforms']

                collection = db[collection_name]
                df = pd.DataFrame(list(collection.find()))
                return [x for x in df.columns if x not in args]

            # if the collection doesn't exist, return false
            return False
    
    def search_engine(  self,
                        search_term,
                        limit=10, 
                        exclude_forms=None,
                        fuzzy_search=False):

        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:

            return_list = []
            return_dict = {}

            db = client['libreforms']

            for collection_name in self.collections():

                # if we've passed exclude_forms, then we assess it here
                # and ignore the form if administrators want us to skip it,
                # see https://github.com/libreForms/libreForms-flask/issues/260
                if exclude_forms and collection_name in exclude_forms:
                # if type(exclude_forms)==list and collection_name in exclude_forms: # if we want to force this to be a list...
                    continue


                if fuzzy_search:
                    from fuzzywuzzy import fuzz

                    TEMP = []
                    for item in db[collection_name].find():
                        # print(item)
                        for field in item:
                            # print(f"-- {field}")
                            score = fuzz.token_set_ratio(search_term, item[field])
                            if score >= fuzzy_search:
                                # print (f"********Found Match")
                                TEMP.append(item)
                                continue
                    
                else:
                    # here we add an index, see 
                    #   https://stackoverflow.com/a/48237570/13301284
                    #   https://stackoverflow.com/a/30314946/13301284 
                    #   *** https://stackoverflow.com/a/48371352/13301284
                    db[collection_name].create_index([('$**', 'text')], default_language='english')

                    # Probably need to escape the values here, see
                    #   https://stackoverflow.com/a/13224790/13301284

                    TEMP = list(db[collection_name].find(
                        {"$text": {"$search": search_term, "$caseSensitive" : False}},
                        [x for x in self.get_collection_columns(collection_name, *self.metadata_fields())]
                        ).limit(limit))

                df = pd.DataFrame(TEMP)

                if len(df) < 1:
                    continue

                # print(df)

                # case as a string
                df['_id'] = df['_id'].astype("string")
                df['formName'] = collection_name
                # df['Hyperlink'] = df.apply (lambda row: f"submissions/{collection_name}/{row['_id']}", axis=1)
                df['fullString'] = df.apply (lambda row: " ".join([str(row[x]) for x in row.keys() if x not in ["Hyperlink", "_id"]]), axis=1)


                

                # TEMP = list(db[collection_name].find())
                [return_list.append(x) for x in df.to_dict('records')]

                # return_dict[collection_name] = df

            return return_list

    def advanced_search_engine(self, conditions, limit=10, exclude_forms=None, fuzzy_search=False):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:

            return_list = []

            db = client['libreforms']

            for collection_name in self.collections():

                # Skip excluded forms
                if exclude_forms and collection_name in exclude_forms:
                    continue

                # Construct the base query using the conditions
                query = {"$and": [{condition["field"]: condition["value"]} for condition in conditions]}

                if fuzzy_search:
                    from fuzzywuzzy import fuzz

                    TEMP = []
                    for item in db[collection_name].find(query):  # Use the constructed query here
                        for field, value in conditions:
                            score = fuzz.token_set_ratio(value, item.get(field, ""))
                            if score >= fuzzy_search:
                                TEMP.append(item)
                                continue

                else:
                    # Add text index for the collection
                    db[collection_name].create_index([('$**', 'text')], default_language='english')

                    # Use the constructed query for direct search
                    TEMP = list(db[collection_name].find(query).limit(limit))

                df = pd.DataFrame(TEMP)

                if len(df) < 1:
                    continue

                # Process the dataframe as before
                df['_id'] = df['_id'].astype("string")
                df['formName'] = collection_name
                df['fullString'] = df.apply(lambda row: " ".join([str(row[x]) for x in row.keys() if x not in ["Hyperlink", "_id"]]), axis=1)

                [return_list.append(x) for x in df.to_dict('records')]

            return return_list



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

    # here we reimplement get_document() without pandas
    def get_document_as_dict(self, collection_name, document_id, drop_fields=[]):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
            db = client['libreforms']

            # if the collection doesn't exist, return false
            if collection_name not in self.collections():
                # print('not in collections')
                return False

            # if an invalid ObjectID is passed, return false
            try:
                assert(ObjectId(document_id))
                _id = ObjectId(document_id)
                # print(_id)
            except Exception as e: 
                return False

            collection = db[collection_name]
            # print(f'found {collection_name}')

            try:
                # return false if the length of the query is less than 1
                x = list(collection.find({"_id": _id}))
                assert(len(list(x)) > 0)
                # print (list(x))

                data = {key: value for key, value in x[0].items() if key not in drop_fields}

                return data

            except:
                return False

    def migrate_form_data(self,from_collection_name,to_collection_name,delete_originals_on_transfer=True):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
            db = client['libreforms']

            from_collection = db[from_collection_name]
            to_collection = db[to_collection_name]

            # Retrieve all documents from collection A
            pipeline = []
            documents = from_collection.aggregate(pipeline)

            to_collection.insert_many(documents)
            if delete_originals_on_transfer:
                from_collection.delete_many({})


    def migrate_collection(self,from_collection_name,to_collection_name,delete_originals_on_transfer=True):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
            db = client['libreforms']

            from_collection = db[from_collection_name]
            to_collection = db[to_collection_name]

            # Retrieve all documents from from_collection
            pipeline = []
            documents = from_collection.aggregate(pipeline)

            to_collection.insert_many(documents)
            
            if delete_originals_on_transfer:
                from_collection.delete_many({})


    def migrate_single_document(self,from_collection_name,to_collection_name,document_id,delete_originals_on_transfer=True):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
            db = client['libreforms']

            from_collection = db[from_collection_name]
            to_collection = db[to_collection_name]

            # Find document in from_collection and make a copy
            document = from_collection.find_one({'_id': ObjectId(document_id)})

            # return None if document not found
            if not document:
                return None
            
            document_copy = document.copy()
            # Insert copied document into new collection
            to_collection.insert_one(document_copy)

            if delete_originals_on_transfer:
                from_collection.delete_one({'_id': ObjectId(document_id)})

            return True

    # this is a wrapper function for migrate_single_document, which moves document 
    # document_id to '_'+from_collection, with delete_originals_on_transfer set to True.
    # We call this `soft deletion` to distinguish it from hard deletion, which would 
    # entirely remove the document from the database.
    def soft_delete_document(self,from_collection_name,document_id):

        # here we set the to_collection name to the 'deletion' collection (_COLLECTION_NAME)
        # unless it already starts with an underscore, in which case we either return None
        # or, perhaps, can just set the to_collection equal to the from_collection ...
        if not from_collection_name.startswith('_'):
            to_collection_name = '_'+from_collection_name
        else:
            # to_collection_name = from_collection_name
            return None
        
        return self.migrate_single_document(from_collection_name, to_collection_name,document_id)

    # this method will restore a soft-deleted document.
    def restore_soft_deleted_document(self,to_collection_name,document_id):

        # here we set the from_collection name to the 'deletion' collection (_COLLECTION_NAME)
        # unless it already starts with an underscore, in which case we return None
        if not to_collection_name.startswith('_'):
            from_collection_name = '_'+to_collection_name
        else:
            return None
        
        return self.migrate_single_document(from_collection_name, to_collection_name,document_id)



    def api_modify_document(self, data, collection_name, document_id,
                                        reporter=None,
                                        ip_address=None):

        # to solve `connection paused` errors when in a forked
        # evironment, we connect and close after each write,
        # see https://github.com/signebedi/libreForms/issues/128        
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(self.connection_string) as client:
            db = client['libreforms']

            collection = db[collection_name]

            timestamp_human_readable = str(datetime.datetime.utcnow())

            data[self.metadata_field_names['reporter']] = str(reporter) if reporter else None

            # here we collect IP addresses if they have been provided, see 
            # https://github.com/signebedi/libreForms/issues/175.
            data[self.metadata_field_names['ip_address']] = ip_address
            if not data[self.metadata_field_names['ip_address']]:
                del data[self.metadata_field_names['ip_address']]

            # setting the timestamp sooner so it's included in the Journal data, perhaps removing the
            # need for a data copy.
            data[self.metadata_field_names['timestamp']] = timestamp_human_readable


            document = self.get_document_as_dict(collection_name, document_id)

            # first we add the data to the document journal field
            document[self.metadata_field_names['journal']][timestamp_human_readable] = data

            for item in data:
                document[item] = data[item]

            collection.update_one({'_id': ObjectId(document_id)}, { "$set": document}, upsert=False)

            # print(data)
            return document_id


    # def get_access_roster(self, collection_name, document_id):

    #     # This will read the access_roster data for a given form, expecting 
    #     # the following format of the row's data formatted as a string:
    #         # _access_roster = {
    #         #     'group_a': {
    #         #         'access':'read',
    #         #         'target':'user'
    #         #     }, 
    #         #     'user_b': {
    #         #         'access':'write',
    #         #         'target':'group'
    #         #     }, 
    #         # }
    #     # see https://github.com/libreForms/libreForms-flask/issues/200.

    #     document = self.get_document_as_dict(collection_name, document_id)

    #     _access_roster = document[self.metadata_field_names['access_roster']]

    #     return _access_roster

# create the mongodb instance that the rest of the application will connect from
mongodb = MongoDB(user=config['mongodb_user'], 
                        host=config['mongodb_host'], 
                        port=config['mongodb_port'], 
                        dbpw=config['mongodb_pw'])