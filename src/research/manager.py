# src/research/manager.py
"""
Research process manager with fixed metadata handling
"""
from typing import List, Dict
from .database.db import ResearchDatabase
from .tavily_client_fix import TavilyClient
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchManager:
    """Manages the research process end-to-end"""
    
    def __init__(self):
        """Initialize manager components"""
        self.client = TavilyClient()
        self.db = ResearchDatabase()
        logger.info("ResearchManager initialized")
    
    def perform_research(self, query: str, max_results: int = 10) -> str:
        """
        Perform research on a topic and save results
        
        Args:
            query: Research topic
            max_results: Maximum number of results to fetch
            
        Returns:
            str: Session ID
        """
        try:
            logger.info(f"\nResearching: {query}")
            logger.info(f"Fetching up to {max_results} results...")
            
            # Get search results
            results = self.client.search(
                query=query,
                max_results=max_results
            )
            
            logger.info(f"\nFound {len(results)} relevant articles")
            
            # Save research session
            session_id = self.db.save_research_session(results, query)
            logger.info(f"Research session saved (ID: {session_id})")
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error during research: {str(e)}")
            raise

def test_manager():
    """Test manager functionality"""
    manager = ResearchManager()
    
    try:
        # Test with a simple query
        session_id = manager.perform_research(
            "test query",
            max_results=2
        )
        
        print(f"\nTest session ID: {session_id}")
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_manager()
    print(f"\nTest {'passed' if success else 'failed'}")