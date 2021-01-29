from pymongo import MongoClient


class DbManager:
    DEFAULT_URL = "mongodb+srv://admin:admin@stocktock.mqvxi.mongodb.net/stocktock?retryWrites=true&w=majority"

    client = MongoClient(DEFAULT_URL)
    db = client.stocktock

    @classmethod
    def get_events(cls):
        return cls.db.events

    @classmethod
    def get_event_categories(cls):
        return cls.db.event_categories
