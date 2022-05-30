# db/__init__.py: defines the class MongoDB used for database operations in the libreForm application.


from pymongo import MongoClient
import datetime

class MongoDB:
    def __init__(self):
        from pymongo import MongoClient
        import datetime
        self.client = MongoClient('localhost', 27017)
        self.db = self.client['libreForms']

    def write_document_to_collection(self, data, collection_name):
        import datetime
        collection = self.db[collection_name]
        data['timestamp'] = str(datetime.datetime.utcnow())
        collection.insert_one(data).inserted_id

    def read_documents_from_collection(self, collection_name):
        collection = self.db[collection_name]
        return collection.find()

