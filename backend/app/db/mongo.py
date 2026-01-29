"""
MongoDB client helpers.
"""
from pymongo import MongoClient

from app.config import settings

_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        if not settings.mongodb_uri:
            raise ValueError("MONGODB_URI is not configured")
        _client = MongoClient(settings.mongodb_uri)
    return _client


def get_database():
    client = get_mongo_client()
    return client[settings.mongo_db]


def get_users_collection():
    db = get_database()
    return db["users"]


def get_papers_collection():
    db = get_database()
    return db["papers"]


def get_conversations_collection():
    db = get_database()
    return db["conversations"]


def get_messages_collection():
    db = get_database()
    return db["messages"]
