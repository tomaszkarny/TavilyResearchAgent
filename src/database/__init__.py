from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

def get_mongodb_client():
    """Initialize and return MongoDB client"""
    client = MongoClient(os.getenv('MONGODB_URI'))
    return client

def get_collection(collection_name="research_data"):
    """Get MongoDB collection"""
    client = get_mongodb_client()
    db = client[os.getenv('MONGODB_DB_NAME', 'research_db')]
    return db[collection_name] 