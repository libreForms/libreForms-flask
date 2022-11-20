""" 
mongodb/__init__.py: a class for managing MongoDB form backends 

This script defines a class for managing a MongoDB database backend,
which is the default form datastore in the base application.

"""

__name__ = "mongodb"
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

        # read database password file, if it exists
        if os.path.exists ("mongodb_creds"):
            with open("mongodb_creds", "r+") as f:
                mongodb_creds = f.read().strip()
        elif dbpw:  
            pass
        else:
            mongodb_creds=None

        conn = MongoClient(f'mongodb://{host}:{dbpw}@{host}:{str(port)}/')
        self.client = MongoClient(host, port)
        self.db = self.client['libreforms']

    def write_document_to_collection(self, data, collection_name, 
                                                    reporter=None,
                                                    # the `modifications` kwarg expects a dict of 
                                                    # fields and the values they've been changed to,
                                                    # else Nonetype to signify an initial submission.
                                                    modifications=None):
        import datetime
        collection = self.db[collection_name]
        data['Timestamp'] = str(datetime.datetime.utcnow())
        data['Reporter'] = str(reporter) if reporter else None
        
        # here we define the behavior of the `Journal` metadata field 
        if not modifications:
            data['Journal'] = {data['Timestamp']:f"{data['Reporter']} created initial submission."}
        else:
            data['Journal'] = {data['Timestamp']:f"{data['Reporter']} made the following modifications: {modifications}."}

        collection.insert_one(data).inserted_id

    def read_documents_from_collection(self, collection_name):
        collection = self.db[collection_name]
        return collection.find()

