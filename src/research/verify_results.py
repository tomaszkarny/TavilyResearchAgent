# src/research/verify_results.py
"""
Verify and display research results with hybrid search support
"""
import logging
from typing import Dict, List
from .database.db import ResearchDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchVerifier:
    """Verifies and displays research results"""
    
    def __init__(self):
        """Initialize verifier"""
        self.db = ResearchDatabase()
    
    def verify_session(self, session_id: str) -> Dict:
        """
        Verify and format session results
        
        Args:
            session_id: Database session ID
            
        Returns:
            Dict with formatted results
        """
        session = self.db.get_session(session_id)
        
        if not session:
            logger.error(f"Session {session_id} not found")
            return None
            
        logger.info(f"Found session: {session.get('query', 'Unknown query')}")
        
        articles = self.db.get_articles(session_id)
        logger.info(f"Found {len(articles)} articles")
        
        # Format results
        formatted_results = {
            "Query": session.get('query', 'Unknown'),
            "Articles": []
        }
        
        for idx, article in enumerate(articles, 1):
            # Get article metadata
            metadata = article.get('metadata', {})
            
            article_data = {
                f"Article {idx}": {
                    "Title": article.get('title', 'N/A'),
                    "URL": article.get('url', 'N/A'),
                    "Relevance Score": article.get('score', 0),
                    "Source": article.get('source', 'web'),
                    "Author": metadata.get('author', 'Unknown'),
                    "Published Date": metadata.get('published_date', 'Unknown'),
                    "Retrieved At": metadata.get('retrieved_at', 'Unknown'),
                    "Language": metadata.get('language', 'Unknown')
                }
            }
            formatted_results["Articles"].append(article_data)
        
        return formatted_results

def display_results(session_id: str) -> None:
    """Display research results for a given session"""
    verifier = ResearchVerifier()
    results = verifier.verify_session(session_id)
    
    if results:
        print("\nGathered Sources:")
        print("-" * 60 + "\n")
        
        for article in results["Articles"]:
            for _, details in article.items():
                print(f"Title: {details['Title']}")
                print(f"URL: {details['URL']}")
                print(f"Relevance Score: {details['Relevance Score']:.2f}")
                print(f"Source: {details['Source']}")
                print(f"Author: {details['Author']}")
                print(f"Published: {details['Published Date']}")
                print(f"Retrieved: {details['Retrieved At']}")
                print(f"Language: {details['Language']}")
                print("-" * 60 + "\n")

def main():
    """Command line interface for result verification"""
    session_id = input("Enter session ID to verify: ")
    display_results(session_id)

if __name__ == "__main__":
    main()