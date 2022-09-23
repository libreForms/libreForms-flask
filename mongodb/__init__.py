# db/__init__.py: defines the class MongoDB used for database operations in the libreForm application.

from pymongo import MongoClient
import datetime, os

class MongoDB:
    def __init__(self, dbpw=None):
        from pymongo import MongoClient
        import datetime

        # read database password file, if it exists
        if os.path.exists ("mongodb_creds"):
            with open("mongodb_creds", "r+") as f:
                mongodb_creds = f.read().strip()
        elif dbpw:  
            pass
        else:
            mongodb_creds=None

        conn = MongoClient(f'mongodb://root:{dbpw}@localhost:27017/')
        self.client = MongoClient('localhost', 27017)
        self.db = self.client['libreforms']

    def write_document_to_collection(self, data, collection_name, reporter=None):
        import datetime
        collection = self.db[collection_name]
        data['Timestamp'] = str(datetime.datetime.utcnow())
        data['Reporter'] = str(reporter) if reporter else None
        collection.insert_one(data).inserted_id

    def read_documents_from_collection(self, collection_name):
        collection = self.db[collection_name]
        return collection.find()

