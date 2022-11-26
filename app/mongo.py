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




"""

__name__ = "app.mongo"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi",]
__version__ = "1.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"


class MongoDB:
    def __init__(self, user='root', host='localhost', port=27017, dbpw=None):
        from pymongo import MongoClient
        import datetime, os

        # # read database password file, if it exists
        # if os.path.exists ("mongodb_creds"):
        #     with open("mongodb_creds", "r+") as f:
        #         mongodb_creds = f.read().strip()
        # elif dbpw:  
        #     pass
        # else:
        #     mongodb_creds=None

        # client = MongoClient(f'mongodb://{user}:{dbpw}@{host}:{str(port)}/')
        client = MongoClient(host, port)
        self.db = client['libreforms']

    def collections(self):
        return self.db.list_collection_names()

    def write_document_to_collection(self, data, collection_name, 
                                                    reporter=None,
                                                    # the `modifications` kwarg expects a truth statement
                                                    # presuming that `data` will just be a slice of changed data
                                                    modification=False):
        import datetime
        from bson.objectid import ObjectId

        collection = self.db[collection_name]
        data['Timestamp'] = str(datetime.datetime.utcnow())
        data['Reporter'] = str(reporter) if reporter else None
        
        # here we define the behavior of the `Journal` metadata field 
        if not modification:
            data['Journal'] = { data['Timestamp']: {
                                                    'Reporter': data['Reporter'],
                                                    'initial_submission': True}
                                                    }
            collection.insert_one(data).inserted_id

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
            # print("\n\n\n", journal_data)

            # some inefficient slicing and voila! we have our correct `Journal` values, 
            # which we append to the `Journal` field of the parent dataframe
            data['Journal'][data['Timestamp']] =  dict(journal_data)
            # print(final_data['Journal'])
            collection.update_one({'_id': ObjectId(data['_id'])}, { "$set": data}, upsert=False)



    def read_documents_from_collection(self, collection_name):
        collection = self.db[collection_name]
        return collection.find()

