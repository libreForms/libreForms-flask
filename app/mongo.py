""" 
mongo.py: creates a class for managing MongoDB form backends 

This script defines a class for managing a MongoDB database backend,
which is the default form datastore in the base application. The base
application should, in the long-run, be written to be totally abstract
as to the application used to store data; in reality, however, it is 
strongly tied to using MongoDB. 

# class MongoDB()

This connects, by default, to a local MongoDB server with user 'root' and
on port 27017. Administrators can over ride these defaults using the 
'mongodb_user', 'mongodb_host', and 'mongodb_port' application configs.

# with MongoClient()

Leaving the MongoClient connection open for the lifespan of the MongoDB 
object is not feasible given that MongoDB is not write safe in a multi-
worker environment like WSGI, see:

    1. https://stackoverflow.com/a/73169147
    2. https://stackoverflow.com/a/18401169

and the following issue: https://github.com/signebedi/libreForms/issues/128. 


"""

__name__ = "app.mongo"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi",]
__version__ = "1.0.1"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

from pymongo import MongoClient
import os

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

        # print(self.dbpw)

    def collections(self):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(f'mongodb://{self.user}:{self.dbpw}@{self.host}:{str(self.port)}/?authSource=admin&retryWrites=true&w=majority') as client:
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
                                                    approver_comment=None,):
        import datetime
        from bson.objectid import ObjectId

        # to solve `connection paused` errors when in a forked
        # evironment, we connect and close after each write,
        # see https://github.com/signebedi/libreForms/issues/128        
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(f'mongodb://{self.user}:{self.dbpw}@{self.host}:{str(self.port)}/?authSource=admin&retryWrites=true&w=majority') as client:
            db = client['libreforms']

            collection = db[collection_name]

            timestamp = str(datetime.datetime.utcnow())

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

            # setting the timestamp sooner so it's included in the Journal data, thus removing the
            # need for a data copy.
            data['Timestamp'] = timestamp

            data_copy = data.copy()

            # here we define the behavior of the `Journal` metadata field 
            if not modification:
                # we create an `Owner` field to be more stable than the `Reporter`
                # field - that is, something that does not generally change.
                # See  https://github.com/signebedi/libreForms/issues/143
                data['Owner'] = data['Reporter']
                data_copy['Owner'] = data_copy['Reporter']
                
                data['Journal'] = { timestamp: data_copy }

                # In the past, we added an `initial_submission` tag the first time a form was submitted
                # but this is probably very redundant, so deprecating it here. 
                # data['Journal'][timestamp]['initial_submission'] = True 
            
            # here we define the behavior of the `Journal` metadata field 
            # if not modification:
                # data['Journal'] = { data['Timestamp']: {
                #                                         'Reporter': data['Reporter'],
                #                                         'initial_submission': True}
                #                                         }

                return str(collection.insert_one(data).inserted_id)

            else:

                # some very overkill slicing to get the original 'Journal' value...
                import pandas as pd
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
                collection.update_one({'_id': ObjectId(data['_id'])}, { "$set": data}, upsert=False)

                return str(data['_id'])



    def read_documents_from_collection(self, collection_name):
        with MongoClient(host=self.host, port=self.port) if not self.dbpw else MongoClient(f'mongodb://{self.user}:{self.dbpw}@{self.host}:{str(self.port)}/?authSource=admin&retryWrites=true&w=majority') as client:
            db = client['libreforms']

            collection = db[collection_name]
            return list(collection.find())

