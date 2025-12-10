import pymongo

class MongoPipeline(object):
    def __init__(self, mongo_uri, mongo_db, mongo_collection):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_collection = mongo_collection

    @classmethod
    def from_crawler(cls, crawler):
        # Pulls database settings from settings.py
        return cls(
            mongo_uri=f"mongodb://{crawler.settings.get('MONGODB_SERVER')}:{crawler.settings.get('MONGODB_PORT')}",
            mongo_db=crawler.settings.get('MONGODB_DB', 'items'),
            mongo_collection=crawler.settings.get('MONGODB_COLLECTION', 'items')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        # Inserts the item into the 'articles' collection
        # We handle duplicates later in the spider's 'closed' method
        try:
            self.db[self.mongo_collection].insert_one(dict(item))
        except Exception:
            pass
        return item