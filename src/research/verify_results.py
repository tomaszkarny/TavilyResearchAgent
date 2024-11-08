# src/research/verify_results.py
"""
Script to verify and display research results from MongoDB
"""
from typing import Dict, List
import os
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_date(date_obj) -> str:
    """Format datetime object to string"""
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%Y-%m-%d %H:%M:%S")
    return str(date_obj)

class ResearchVerifier:
    def __init__(self):
        """Initialize MongoDB connection"""
        load_dotenv()
        self.client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.client[os.getenv('MONGODB_DB_NAME', 'research_db')]
        
        # Collections
        self.sessions = self.db['research_sessions']
        self.articles = self.db['research_articles']

    def verify_session(self, session_id: str) -> Dict:
        """
        Verify and display session data
        
        Args:
            session_id: Research session ID to verify
        """
        try:
            # Try to find session with ObjectId
            obj_id = ObjectId(session_id)
            session = self.sessions.find_one({"_id": obj_id})
            
            if not session:
                logger.error(f"Session {session_id} not found!")
                return None
                
            logger.info(f"Found session: {session.get('query')}")
            
            # Get articles for session
            articles = list(self.articles.find({"session_id": session_id}))
            logger.info(f"Found {len(articles)} articles")
            
            # Format session data for display
            session_info = {
                "Session ID": str(session.get("_id")),
                "Query": session.get("query"),
                "Timestamp": format_date(session.get("timestamp")),
                "Source": session.get("source"),
                "Processed": session.get("processed"),
                "Article Count": session.get("article_count"),
                "Found Articles Count": len(articles)
            }
            
            # Format article data
            articles_info = []
            for idx, article in enumerate(articles, 1):
                # Get article fields (now stored at top level)
                title = article.get('title', '')
                url = article.get('url', '')
                metadata = article.get('metadata', {})
                content = article.get('content', {})
                
                # Get content text based on structure
                if isinstance(content, dict):
                    content_text = content.get('full_text', '')
                else:
                    content_text = str(content)
                
                article_info = {
                    f"Article {idx}": {
                        "Title": title or metadata.get('title', 'N/A'),
                        "URL": url or metadata.get('url', 'N/A'),
                        "Domain": metadata.get('domain', 'N/A'),
                        "Author": metadata.get('author', 'N/A'),
                        "Published Date": format_date(metadata.get('published_date')),
                        "Retrieved Date": format_date(metadata.get('retrieved_date')),
                        "Relevance Score": metadata.get('relevance_score', 0),
                        "Content Length": len(content_text),
                        "Content Preview": content_text[:200] + "..." if content_text else "N/A"
                    }
                }
                articles_info.append(article_info)
                
            return {
                "Session Information": session_info,
                "Articles": articles_info
            }
            
        except Exception as e:
            logger.error(f"Error verifying session: {str(e)}")
            return None

def pretty_print_results(results: Dict):
    """Print results in a readable format"""
    if not results:
        return
        
    print("\n=== Research Session Verification ===\n")
    
    # Print session information
    session_info = results["Session Information"]
    print("Session Information:")
    print("-" * 50)
    for key, value in session_info.items():
        print(f"{key}: {value}")
    
    # Print article information
    print("\nArticles Found:")
    print("-" * 50)
    for article in results["Articles"]:
        for article_num, details in article.items():
            print(f"\n{article_num}:")
            for key, value in details.items():
                if key == "Content Preview":
                    print(f"\n  {key}:")
                    print(f"  {'-' * 40}")
                    print(f"  {value}")
                else:
                    print(f"  {key}: {value}")
            print("-" * 50)

def main():
    """Main function to verify research results"""
    verifier = ResearchVerifier()
    
    # Get session ID from user
    session_id = input("\nEnter research session ID to verify: ").strip()
    
    try:
        results = verifier.verify_session(session_id)
        if results:
            pretty_print_results(results)
            
            # Save results to file
            filename = f"research_verification_{session_id}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to {filename}")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()