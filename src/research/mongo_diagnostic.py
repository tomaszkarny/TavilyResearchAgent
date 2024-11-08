# src/research/mongo_diagnostic.py
"""
Diagnostic script for MongoDB connection and data structure
"""
import os
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDBDiagnostic:
    def __init__(self):
        """Initialize MongoDB connection"""
        load_dotenv()
        
        # Get MongoDB URI
        self.mongodb_uri = os.getenv('MONGODB_URI')
        self.db_name = os.getenv('MONGODB_DB_NAME', 'research_db')
        
        logger.info(f"Using database: {self.db_name}")
        logger.info(f"MongoDB URI: {self.mongodb_uri[:20]}...") # Show only beginning for security
        
        # Initialize connection
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.db_name]

    def check_connection(self):
        """Verify MongoDB connection"""
        try:
            # Ping the database
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            return False

    def list_collections(self):
        """List all collections in the database"""
        try:
            collections = self.db.list_collection_names()
            logger.info("Found collections:")
            for collection in collections:
                count = self.db[collection].count_documents({})
                logger.info(f"- {collection}: {count} documents")
            return collections
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            return []

    def check_session(self, session_id: str):
        """Check specific session details"""
        try:
            # Try with string ID
            logger.info(f"Checking session ID: {session_id}")
            
            # Check in string format
            session = self.db.research_sessions.find_one({"_id": session_id})
            if session:
                logger.info("Found session with string ID")
                return session
            
            # Try with ObjectId
            try:
                obj_id = ObjectId(session_id)
                session = self.db.research_sessions.find_one({"_id": obj_id})
                if session:
                    logger.info("Found session with ObjectId")
                    return session
            except:
                logger.info("Invalid ObjectId format")
            
            logger.warning("Session not found with either string or ObjectId")
            return None
            
        except Exception as e:
            logger.error(f"Error checking session: {str(e)}")
            return None

    def list_recent_sessions(self, limit: int = 5):
        """List most recent research sessions"""
        try:
            logger.info(f"Fetching {limit} most recent sessions...")
            
            # Try to find recent sessions
            sessions = list(self.db.research_sessions.find().sort([("timestamp", -1)]).limit(limit))
            
            if sessions:
                logger.info(f"Found {len(sessions)} recent sessions:")
                for session in sessions:
                    logger.info("-" * 40)
                    logger.info(f"ID: {session.get('_id')}")
                    logger.info(f"Query: {session.get('query')}")
                    logger.info(f"Timestamp: {session.get('timestamp')}")
                    logger.info(f"Article Count: {session.get('article_count')}")
            else:
                logger.warning("No sessions found in database")
                
            return sessions
            
        except Exception as e:
            logger.error(f"Error listing recent sessions: {str(e)}")
            return []

def main():
    """Run diagnostic checks"""
    diagnostic = MongoDBDiagnostic()
    
    print("\n=== MongoDB Diagnostic Results ===\n")
    
    # Check connection
    if not diagnostic.check_connection():
        print("Failed to connect to MongoDB. Please check your connection string and network connection.")
        return
        
    # List collections
    print("\nChecking collections...")
    collections = diagnostic.list_collections()
    
    # List recent sessions
    print("\nChecking recent sessions...")
    recent_sessions = diagnostic.list_recent_sessions()
    
    if recent_sessions:
        print("\nWould you like to check a specific session? (y/n)")
        if input().lower() == 'y':
            session_id = input("Enter session ID: ").strip()
            session = diagnostic.check_session(session_id)
            
            if session:
                print("\nSession details:")
                for key, value in session.items():
                    print(f"{key}: {value}")
            else:
                print("Session not found.")

if __name__ == "__main__":
    main()