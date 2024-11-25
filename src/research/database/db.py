# src/research/database/db.py
"""
Database operations with basic search support for MongoDB Atlas Basic Plan
"""
from typing import List, Dict, Optional
from datetime import datetime
import logging
from pymongo import MongoClient, ASCENDING, TEXT
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId
from ..exceptions import DatabaseError

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchDatabase:
    """MongoDB database with basic search capabilities"""
    
    def __init__(self):
        """Initialize database connection and collections"""
        self.client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.client[os.getenv('MONGODB_DB_NAME', 'research_db')]
        
        # Collections
        self.sessions = self.db.sessions
        self.articles = self.db.articles
        
        # Ensure indexes
        self._setup_indexes()
        logger.info("Research database initialized")
    
    def _setup_indexes(self):
        """Setup required database indexes"""
        # Session indexes
        self.sessions.create_index([("timestamp", ASCENDING)])
        
        # Article indexes
        self.articles.create_index([("session_id", ASCENDING)])
        self.articles.create_index([("url", ASCENDING)])
        
        # Text search index
        try:
            self.articles.create_index([
                ("content", TEXT),
                ("title", TEXT)
            ])
            logger.info("Text search index created successfully")
        except Exception as e:
            logger.error(f"Text index creation failed: {e}")
            raise
    
    def save_research_session(self, results: List[Dict], query: str) -> str:
        """Save research results"""
        try:
            # Create session record
            session = {
                'query': query,
                'timestamp': datetime.utcnow(),
                'source': 'hybrid',
                'processed': False,
                'article_count': len(results)
            }
            
            session_id = str(self.sessions.insert_one(session).inserted_id)
            logger.info(f"Created research session: {session_id}")
            
            # Save articles
            for result in results:
                article = {
                    'session_id': session_id,
                    'title': result.get('title', 'N/A'),
                    'url': result.get('url', 'N/A'),
                    'content': result.get('content', ''),
                    'score': result.get('score', 0),
                    'source': result.get('source', 'web'),
                    'metadata': result.get('metadata', {}),
                    # Store embeddings as regular field
                    'embedding_data': result.get('embedding', [])
                }
                self.articles.insert_one(article)
            
            logger.info(f"Saved {len(results)} articles for session {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error saving research session: {e}")
            raise
    
    def update_session(self, session_id: str, update_data: Dict) -> None:
        """
        Update research session with new data
        
        Args:
            session_id: Database session ID
            update_data: Dictionary with fields to update
        """
        try:
            # Convert ObjectId if string provided
            if isinstance(session_id, str):
                session_id = ObjectId(session_id)
                
            # Update session document
            result = self.sessions.update_one(
                {'_id': session_id},
                {'$set': update_data}
            )
            
            if result.modified_count == 0:
                logger.warning(f"Session {session_id} not found or no changes made")
            else:
                logger.info(f"Updated session {session_id} with new data")
                
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            raise DatabaseError(f"Failed to update session: {str(e)}")
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get session by ID
        
        Args:
            session_id: Database session ID
            
        Returns:
            Session document or None if not found
        """
        try:
            if isinstance(session_id, str):
                session_id = ObjectId(session_id)
                
            session = self.sessions.find_one({'_id': session_id})
            return session
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise DatabaseError(f"Failed to get session: {str(e)}")
    
    def get_articles(self, session_id: str) -> List[Dict]:
        """Get articles for a session"""
        try:
            return list(self.articles.find({"session_id": session_id}))
        except Exception as e:
            logger.error(f"Error getting articles: {e}")
            return []
    
    def text_search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Perform text search on articles
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching documents
        """
        try:
            results = list(self.articles.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit))
            
            logger.info(f"Found {len(results)} articles in text search")
            return results
            
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return []