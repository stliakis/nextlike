import pymongo
from app.settings import get_settings


def get_mongo(database: str = None) -> pymongo.MongoClient:
    db = pymongo.MongoClient(
        host=[get_settings().MONGO_HOST]
    )

    if database:
        return db[database]

    return db
