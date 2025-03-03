"""
Unified MongoDB connection management for the TavilyResearchAgent.
Applied: codeStructure_001, codeStructure_003
"""
from typing import Optional
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
import logging
from ..exceptions import DatabaseError

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Singleton class for managing MongoDB connections"""
    _instance: Optional['DatabaseConnection'] = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._client:
            self._initialize_connection()

    def _initialize_connection(self):
        """Initialize MongoDB connection"""
        try:
            mongodb_uri = os.getenv('MONGODB_URI')
            if not mongodb_uri:
                raise DatabaseError("MONGODB_URI environment variable not set")
            
            self._client = MongoClient(mongodb_uri)
            db_name = os.getenv('MONGODB_DB_NAME', 'research_db')
            self._db = self._client[db_name]
            logger.info(f"Connected to MongoDB database: {db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise DatabaseError(f"MongoDB connection failed: {str(e)}")

    @property
    def client(self) -> MongoClient:
        """Get MongoDB client instance"""
        return self._client

    @property
    def db(self) -> Database:
        """Get database instance"""
        return self._db

    def get_collection(self, collection_name: str) -> Collection:
        """Get a specific collection"""
        return self._db[collection_name]

    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed")

# Global instance for easy access
db_connection = DatabaseConnection()

def get_db() -> Database:
    """Get the database instance"""
    return db_connection.db

def get_collection(collection_name: str) -> Collection:
    """Get a specific collection"""
    return db_connection.get_collection(collection_name)
