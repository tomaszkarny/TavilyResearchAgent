# src/research/verify_results.py
"""
Verify and display research results with hybrid search support
"""
import logging
from typing import Dict, List, Optional
from .database.db import ResearchDatabase
from .exceptions import DatabaseError

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

def display_processed_data(session_id: str) -> Optional[Dict]:
    """
    Display processed data for a research session
    
    Args:
        session_id: Database session ID
    Returns:
        Optional[Dict]: Processed data if found
    """
    try:
        db = ResearchDatabase()
        session = db.get_session(session_id)
        
        if not session or not session.get('processed_data'):
            logger.error(f"No processed data found for session {session_id}")
            return None
            
        data = session['processed_data']
        
        # Display Research Summary with Session Info
        print("\n" + "="*50)
        print("RESEARCH SUMMARY")
        print("="*50)
        print(f"\nTopic: {data['topic']}")
        print(f"Session Created: {session.get('timestamp', 'N/A')}")
        print(f"Last Updated: {session.get('completed_at', 'N/A')}")
        
        # Display Stats
        if 'stats' in session:
            print("\nSearch Statistics:")
            print(f"Total Results Found: {session['stats'].get('total_found', 0)}")
            print(f"Scientific Sources: {session['stats'].get('scientific_sources', 0)}")
            print(f"Other Sources: {session['stats'].get('other_sources', 0)}")
        
        # Display Key Findings
        print("\n" + "-"*20)
        print("KEY FINDINGS")
        print("-"*20)
        for i, finding in enumerate(data['key_findings'], 1):
            print(f"\n{i}. {finding}")
            
        # Display Processed Articles
        print("\n" + "="*50)
        print("PROCESSED ARTICLES")
        print("="*50)
        
        # Sort articles by date if available
        articles = data['articles']
        articles.sort(
            key=lambda x: x.get('metadata', {}).get('added_date', ''),
            reverse=True
        )
        
        for article in articles:
            print("\n" + "-"*40)
            print(f"Title: {article['title']}")
            print(f"URL: {article['url']}")
            print(f"Relevance Score: {article['score']:.2f}")
            
            # Enhanced metadata display
            print("\nMetadata:")
            metadata = article.get('metadata', {})
            print(f"📅 Published: {metadata.get('published_date', 'N/A')}")
            print(f"📅 Added to Database: {metadata.get('added_date', 'N/A')}")
            print(f"🌐 Source: {metadata.get('source', 'web')}")
            print(f"🗣 Language: {metadata.get('language', 'en')}")
            
            print("\nMain Points:")
            for point in article['summary']['main_points']:
                print(f"• {point}")
                
            print("\nKey Statistics:")
            for stat in article['summary'].get('key_statistics', []):
                print(f"📊 {stat}")
                
            print("\nPractical Tips:")
            for tip in article['summary'].get('practical_tips', []):
                print(f"💡 {tip}")
                
            print("\nExpert Opinions:")
            for opinion in article['summary'].get('expert_opinions', []):
                if opinion.get('expert') and opinion.get('quote'):
                    print(f"👤 {opinion['expert']}: \"{opinion['quote']}\"")
            
            print("\nDetailed Summary:")
            print(article['summary']['summary'])
            
        return data
        
    except Exception as e:
        logger.error(f"Error displaying processed data: {e}")
        raise DatabaseError(f"Failed to display data: {str(e)}")

def main():
    """Command line interface for result verification"""
    session_id = input("Enter session ID to verify: ")
    display_results(session_id)

if __name__ == "__main__":
    main()