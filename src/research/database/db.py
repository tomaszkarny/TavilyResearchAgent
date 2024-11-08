# src/research/database/db.py
"""
Database operations for research data with improved metadata handling and debug logging
"""
import os
from datetime import datetime
from typing import List, Dict
from urllib.parse import urlparse
from pymongo import MongoClient
from dotenv import load_dotenv
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchDatabase:
    """Handles database operations for research data"""
    
    def __init__(self):
        """Initialize database connection"""
        load_dotenv()
        self.client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.client[os.getenv('MONGODB_DB_NAME', 'research_db')]
        
        # Collections
        self.sessions = self.db['research_sessions']
        self.articles = self.db['research_articles']
        
        logger.info("Research database initialized")
    
    def save_research_session(self, results: List[Dict], query: str) -> str:
        """
        Save research results with enhanced metadata handling
        
        Args:
            results: List of search results from Tavily
            query: Original search query
            
        Returns:
            str: Session ID
        """
        try:
            # Debug: Log received results
            logger.debug("Received results for saving:")
            logger.debug(json.dumps(results, indent=2, default=str))
            
            # Create session record
            session = {
                'query': query,
                'timestamp': datetime.utcnow(),
                'source': 'tavily',
                'processed': False,
                'article_count': len(results)
            }
            
            session_id = self.sessions.insert_one(session).inserted_id
            str_session_id = str(session_id)
            
            logger.info(f"Created research session: {str_session_id}")
            
            # Save each article with enhanced metadata
            for result in results:
                # Debug: Log raw result before processing
                logger.debug(f"Processing result: {json.dumps(result, indent=2, default=str)}")
                
                article = self._format_article(result, str_session_id)
                self.articles.insert_one(article)
            
            logger.info(f"Saved {len(results)} articles for session {str_session_id}")
            return str_session_id
            
        except Exception as e:
            logger.error(f"Error saving research session: {str(e)}")
            raise
    
    def _format_article(self, result: Dict, session_id: str) -> Dict:
        """
        Format article data with enhanced metadata handling
        
        Args:
            result: Single result from Tavily API
            session_id: ID of the research session
        """
        try:
            # Extract basic information
            title = result.get('title', '')
            url = result.get('url', '')
            content = result.get('content', '')
            raw_content = result.get('raw_content', '')
            
            # Log extraction of key fields
            logger.debug(f"Extracting data for article:")
            logger.debug(f"Title: {title}")
            logger.debug(f"URL: {url}")
            logger.debug(f"Content length: {len(content)}")
            
            # Format the article data
            article_data = {
                'session_id': session_id,
                'title': title,  # Store title at top level
                'url': url,      # Store URL at top level
                'content': {
                    'title': title,
                    'full_text': content,
                    'raw_content': raw_content,
                    'summary': content[:500] if content else '',
                    'key_points': []
                },
                'metadata': {
                    'url': url,
                    'domain': self._extract_domain(url),
                    'author': result.get('author', ''),
                    'published_date': result.get('published_date'),
                    'retrieved_date': datetime.utcnow(),
                    'relevance_score': result.get('score', 0),
                    'source': 'tavily'
                },
                'analysis': {
                    'processed': False,
                    'sentiment': None,
                    'topics': [],
                    'llm_notes': None
                }
            }
            
            # Log formatted article data
            logger.debug(f"Formatted article data: {json.dumps(article_data, indent=2, default=str)}")
            
            return article_data
            
        except Exception as e:
            logger.error(f"Error formatting article: {str(e)}")
            logger.error(f"Problematic result: {json.dumps(result, indent=2, default=str)}")
            raise
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            return urlparse(url).netloc
        except:
            return ''
    
    def get_session_data(self, session_id: str) -> Dict:
        """
        Get all data for a research session
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Dict containing session and article data
        """
        try:
            # Get session
            session = self.sessions.find_one({"_id": session_id})
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Get articles
            articles = list(self.articles.find({"session_id": str(session_id)}))
            
            return {
                "session": session,
                "articles": articles,
                "article_count": len(articles)
            }
            
        except Exception as e:
            logger.error(f"Error retrieving session data: {str(e)}")
            raise

def test_database():
    """Test database functionality with sample data"""
    db = ResearchDatabase()
    
    # Test data with complete metadata
    test_results = [
        {
            "title": "Test Article",
            "url": "https://example.com/article",
            "content": "Test content",
            "score": 0.95,
            "metadata": {
                "author": "John Doe",
                "published_date": "2024-01-01"
            }
        }
    ]
    
    try:
        # Save test session
        session_id = db.save_research_session(test_results, "test query")
        logger.info(f"Test session saved with ID: {session_id}")
        
        # Retrieve and verify data
        session_data = db.get_session_data(session_id)
        logger.info(f"Retrieved {session_data['article_count']} articles")
        
        # Print first article data
        if session_data['articles']:
            article = session_data['articles'][0]
            logger.info("First article data:")
            logger.info(f"Title: {article.get('title')}")
            logger.info(f"URL: {article.get('url')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Set debug logging for testing
    logging.getLogger(__name__).setLevel(logging.DEBUG)
    
    success = test_database()
    print(f"Database test {'passed' if success else 'failed'}")