"""
Database operations with basic search support for MongoDB Atlas Basic Plan
Applied: codeStructure_001, codeStructure_003
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from pymongo import ASCENDING, TEXT
from bson.objectid import ObjectId
from ..exceptions import DatabaseError
from .db_connection import get_db, get_collection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchDatabase:
    """MongoDB database with basic search capabilities"""
    
    def __init__(self):
        """Initialize database connection and collections"""
        self.db = get_db()
        
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
        self.articles.create_index([("metadata.published_date", ASCENDING)])
        self.articles.create_index([("metadata.retrieved_at", ASCENDING)])
        
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

    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date string to standard format"""
        if not date_str:
            return 'N/A'
        try:
            # Handle different date formats
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%a, %d %b %Y %H:%M:%S GMT']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
                except ValueError:
                    continue
            return date_str
        except Exception:
            return date_str
    
    def save_research_session(self, results: List[Dict], query: str) -> str:
        """
        Save research session and results to database
        
        Args:
            results: List of search results
            query: Search query
            
        Returns:
            str: Session ID
        """
        try:
            # Validate inputs
            if not isinstance(query, str):
                raise ValueError("Query must be a string")
            if not isinstance(results, list):
                raise ValueError("Results must be a list")

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
                # Process metadata with standardized dates
                metadata = result.get('metadata', {})
                processed_metadata = {
                    'source': metadata.get('source', 'web'),
                    'published_date': self._format_date(result.get('published_date')),
                    'retrieved_at': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                    'added_date': datetime.utcnow().isoformat(),
                    'score': result.get('score', 0),
                    'author': metadata.get('author', 'N/A'),
                    'language': metadata.get('language', 'N/A'),
                    'response_time': result.get('response_time')
                }

                article = {
                    'session_id': session_id,
                    'title': result.get('title', 'N/A'),
                    'url': result.get('url', 'N/A'),
                    'content': result.get('content', ''),
                    'raw_content': result.get('raw_content', '') if result.get('include_raw_content') else '',
                    'score': result.get('score', 0),
                    'source': 'tavily',
                    'metadata': processed_metadata,
                    'embedding_data': result.get('embedding', [])
                }
                self.articles.insert_one(article)

            logger.info(f"Saved {len(results)} articles for session {session_id}")
            return session_id

        except Exception as e:
            logger.error(f"Error saving research session: {e}")
            raise
    
    def update_session(self, session_id: str, update_data: Dict) -> Dict:
        """
        Update research session with new data and metadata tracking.

        Args:
            session_id: Database session ID
            update_data: Dictionary with fields to update

        Returns:
            Dict containing update status and metadata:
                - success: Boolean indicating if update was successful
                - message: Description of the operation result
                - modified_count: Number of documents modified
                - timestamp: When the update occurred
                - previous_state: Previous session state (if available)

        Raises:
            DatabaseError: If session validation or update fails
            ValueError: If session_id or update_data is invalid
        """
        try:
            # Input validation
            if not session_id:
                raise ValueError("session_id cannot be empty")
            if not update_data or not isinstance(update_data, dict):
                raise ValueError("update_data must be a non-empty dictionary")

            # Validate timestamps if present
            if 'timestamp' in update_data and not isinstance(update_data['timestamp'], datetime):
                raise ValueError("timestamp must be a datetime object")

            # Convert ObjectId if string provided
            if isinstance(session_id, str):
                try:
                    session_id = ObjectId(session_id)
                except Exception as e:
                    raise ValueError(f"Invalid session_id format: {str(e)}")

            # Get current session state
            current_session = self.sessions.find_one({'_id': session_id})
            if not current_session:
                raise DatabaseError(f"Session {session_id} not found")

            # Prepare update metadata
            update_metadata = {
                'last_modified': datetime.utcnow(),
                'modification_history': {
                    'timestamp': datetime.utcnow(),
                    'modified_fields': list(update_data.keys()),
                    'previous_state': {
                        k: current_session.get(k)
                        for k in update_data.keys()
                        if k in current_session
                    }
                }
            }

            # Combine update data with metadata
            full_update = {
                '$set': update_data,
                '$push': {
                    'updates': update_metadata['modification_history']
                }
            }

            # Perform update with validation
            result = self.sessions.update_one(
                {'_id': session_id},
                full_update
            )

            # Prepare response
            response = {
                'success': result.modified_count > 0,
                'message': 'Session updated successfully' if result.modified_count > 0 else 'No changes made',
                'modified_count': result.modified_count,
                'timestamp': update_metadata['last_modified'],
                'previous_state': update_metadata['modification_history']['previous_state']
            }

            # Log operation result
            if result.modified_count > 0:
                logger.info(
                    f"Updated session {session_id} with new data. "
                    f"Modified fields: {', '.join(update_data.keys())}"
                )
            else:
                logger.warning(
                    f"Session {session_id} update resulted in no changes. "
                    f"Attempted fields: {', '.join(update_data.keys())}"
                )

            return response

        except ValueError as e:
            error_msg = f"Invalid input: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except DatabaseError as e:
            error_msg = f"Database operation failed: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error updating session {session_id}: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get session by ID
        
        Args:
            session_id: Database session ID
            
        Returns:
            Session document or None if not found
            
        Raises:
            ValueError: If session_id is invalid
            DatabaseError: If database operation fails
        """
        try:
            if not session_id:
                raise ValueError("session_id cannot be empty")
                
            if isinstance(session_id, str):
                try:
                    session_id = ObjectId(session_id)
                except Exception as e:
                    raise ValueError(f"Invalid session_id format: {str(e)}")
                
            session = self.sessions.find_one({'_id': session_id})
            if not session:
                logger.warning(f"Session {session_id} not found")
            return session
            
        except ValueError as e:
            logger.error(f"Invalid session_id {session_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise DatabaseError(f"Failed to get session: {str(e)}")
    
    def get_articles(self, session_id: str) -> List[Dict]:
        """Get articles for a session"""
        try:
            pipeline = [
                {"$match": {"session_id": session_id}},
                {"$sort": {"metadata.published_date": -1}},
                {"$project": {
                    "title": 1,
                    "url": 1,
                    "content": 1,
                    "score": 1,
                    "metadata": 1,
                    "raw_content": 1
                }}
            ]
            return list(self.articles.aggregate(pipeline))
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
    
    def inspect_session_articles(self, session_id: str) -> List[Dict]:
        """
        Inspect articles for a specific session with focus on metadata and dates
        
        Args:
            session_id: ID of the research session
            
        Returns:
            List of articles with their metadata
        """
        try:
            # Find all articles for the session
            articles = list(self.articles.find({"session_id": session_id}))
            
            # Log inspection results
            logger.info(f"\nInspecting articles for session {session_id}")
            logger.info(f"Found {len(articles)} articles")
            
            for article in articles:
                metadata = article.get('metadata', {})
                logger.info(f"\nArticle: {article.get('title')}")
                logger.info(f"URL: {article.get('url')}")
                logger.info(f"Published date: {metadata.get('published_date')}")
                logger.info(f"Added date: {metadata.get('added_date')}")
                logger.info(f"Retrieved at: {metadata.get('retrieved_at')}")
                logger.info(f"Full metadata: {metadata}")
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to inspect session articles: {e}")
            raise DatabaseError(f"Session inspection failed: {e}")
    
    def cleanup_old_sessions(self, days_old: int = 30) -> Dict:
        """
        Remove sessions and their associated articles older than specified days
        
        Args:
            days_old: Number of days after which to remove sessions
            
        Returns:
            Dict containing cleanup statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find old sessions
            old_sessions = self.sessions.find({
                'timestamp': {'$lt': cutoff_date}
            })
            session_ids = [str(s['_id']) for s in old_sessions]
            
            # Remove associated articles first
            articles_result = self.articles.delete_many({
                'session_id': {'$in': session_ids}
            })
            
            # Remove sessions
            sessions_result = self.sessions.delete_many({
                'timestamp': {'$lt': cutoff_date}
            })
            
            stats = {
                'success': True,
                'sessions_removed': sessions_result.deleted_count,
                'articles_removed': articles_result.deleted_count,
                'cutoff_date': cutoff_date.isoformat(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(
                f"Cleanup complete: removed {stats['sessions_removed']} sessions "
                f"and {stats['articles_removed']} articles older than {days_old} days"
            )
            return stats
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise DatabaseError(f"Cleanup operation failed: {str(e)}")