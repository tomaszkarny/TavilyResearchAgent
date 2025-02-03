#!/usr/bin/env python
"""
Script to extract processed articles from MongoDB.
Usage: python extract_processed_articles.py <session_id>

This script connects to MongoDB using the same configuration as the main application
and retrieves processed article data for a given research session.
"""

import sys
import logging
from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv
from bson.objectid import ObjectId

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_metadata(metadata: Dict) -> str:
    """Format metadata for display"""
    if not metadata:
        return "No metadata available"
    
    formatted = []
    for key, value in metadata.items():
        if isinstance(value, datetime):
            value = value.strftime('%Y-%m-%d %H:%M:%S')
        formatted.append(f"  {key}: {value}")
    return "\n".join(formatted)

def format_summary(summary: Dict) -> str:
    """Format article summary for display"""
    if not summary:
        return "No summary available"
    
    sections = []
    
    # Main summary text
    if "summary" in summary:
        sections.append(f"Summary:\n  {summary['summary']}\n")
    
    # Main points
    if "main_points" in summary:
        points = summary["main_points"]
        sections.append("Main Points:")
        sections.extend(f"  {i+1}. {point}" for i, point in enumerate(points))
        sections.append("")
    
    # Key statistics
    if "key_statistics" in summary and summary["key_statistics"]:
        sections.append("Key Statistics:")
        sections.extend(f"  • {stat}" for stat in summary["key_statistics"])
        sections.append("")
    
    # Practical tips
    if "practical_tips" in summary and summary["practical_tips"]:
        sections.append("Practical Tips:")
        sections.extend(f"  • {tip}" for tip in summary["practical_tips"])
        sections.append("")
    
    # Expert opinions
    if "expert_opinions" in summary and summary["expert_opinions"]:
        sections.append("Expert Opinions:")
        for opinion in summary["expert_opinions"]:
            sections.append(f"  • {opinion['expert']}: {opinion['quote']}")
        sections.append("")
    
    return "\n".join(sections)

def extract_processed_articles(session_id: str) -> List[Dict]:
    """
    Extract processed articles for a given session from MongoDB.
    
    Args:
        session_id: The ID of the research session
        
    Returns:
        List of processed articles
    
    Raises:
        SystemExit: If session is not found or has no processed data
    """
    try:
        # Import here to avoid circular imports
        from src.research.database.db_connection import get_collection
        
        # Get the sessions collection
        sessions = get_collection('sessions')
        
        # Convert string ID to ObjectId if needed
        try:
            if len(session_id) == 24:  # Length of a standard ObjectId
                session_id = ObjectId(session_id)
        except Exception:
            pass  # Keep original string ID if conversion fails
        
        logger.info(f"Attempting to retrieve session with ID: {session_id}")
        session = sessions.find_one({"_id": session_id})
        
        if not session:
            logger.error(f"No session found with ID: {session_id}")
            sys.exit(1)
        
        processed_data = session.get("processed_data")
        if not processed_data:
            logger.error("No processed_data found in this session")
            sys.exit(1)
        
        articles = processed_data.get("articles", [])
        if not articles:
            logger.warning("No processed articles found in this session")
            return []
        
        logger.info(f"Found {len(articles)} processed articles")
        return articles
        
    except Exception as e:
        logger.error(f"Error retrieving session data: {e}")
        sys.exit(1)

def display_articles(articles: List[Dict]):
    """Display formatted article information"""
    if not articles:
        print("No articles to display")
        return
    
    for idx, article in enumerate(articles, start=1):
        print("\n" + "="*80)
        print(f"Article {idx}:")
        print("-"*80)
        
        # Basic information
        print(f"Title: {article.get('title', 'N/A')}")
        print(f"URL: {article.get('url', 'N/A')}")
        print(f"Relevance Score: {article.get('score', 'N/A')}")
        
        # Metadata
        print("\nMetadata:")
        print(format_metadata(article.get('metadata', {})))
        
        # Summary and analysis
        print("\nAnalysis:")
        print(format_summary(article.get('summary', {})))
        
        # Processing timestamp
        processed_at = article.get('processed_at')
        if processed_at:
            if isinstance(processed_at, str):
                print(f"Processed at: {processed_at}")
            else:
                print(f"Processed at: {processed_at.strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv()
    
    if len(sys.argv) != 2:
        print("Usage: python extract_processed_articles.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    articles = extract_processed_articles(session_id)
    display_articles(articles)

if __name__ == "__main__":
    main()
