# src/research/verify_results.py
"""
Verify and display research results with hybrid search support
"""
import logging
from typing import Dict, List, Optional
from .database.db import ResearchDatabase
from .exceptions import DatabaseError
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchVerifier:
    def __init__(self):
        self.db = ResearchDatabase()
    
    def verify_session(self, session_id: str) -> Optional[Dict]:
        """
    Verify and format session results
    
    Args:
        session_id: Database session ID
            
    Returns:
        Optional[Dict]: Formatted results dictionary or None if session not found
    """
    # Add input validation
        if not isinstance(session_id, str):    
            logger.error("Invalid session_id format")
            return None
        
        session = self.db.get_session(session_id)
        
        if not session:
            logger.error(f"Session {session_id} not found")
            return None
            
        logger.info(f"Found session: {session.get('query', 'Unknown query')}")
    
        articles = self.db.get_articles(session_id)
        logger.info(f"Found {len(articles)} articles")
    
    # Add debug logging for first article
        if articles:
            logger.info("Sample article data:")
            logger.info(f"Keys in article: {list(articles[0].keys())}")
            logger.info(f"Metadata: {articles[0].get('metadata', {})}")
            logger.info(f"Full article data: {articles[0]}")

    # Format results
        formatted_results = {
            "Query": session.get('query', 'Unknown'),
            "Articles": []
        }
    
        for idx, article in enumerate(articles, 1):
        # Get article metadata
            metadata = article.get('metadata', {})
            logger.info(f"Processing article {idx}:")
            logger.info(f"Article metadata: {metadata}")
        
        # Handle dates more robustly
            published_date = metadata.get('published_date', 'N/A')
            retrieved_at = metadata.get('retrieved_at')
        
        # Format retrieved_at date
            if isinstance(retrieved_at, datetime):
                retrieved_at = retrieved_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
            elif isinstance(retrieved_at, str):
                retrieved_at = retrieved_at
            else:
                retrieved_at = 'N/A'
        
            article_data = {
                f"Article {idx}": {
                    "Title": article.get('title', 'N/A'),
                    "URL": article.get('url', 'N/A'),
                    "Relevance Score": article.get('score', 0),
                    "Source": "Tavily Search",
                # Dodanie daty publikacji
                "Published Date": published_date if published_date != 'N/A' else 'Not available',
                "Retrieved At": retrieved_at if retrieved_at != 'N/A' else 'Not available',
                "Response Time": metadata.get('response_time', 'N/A'),
                "Content Length": len(article.get('content', '')),
                "Has Raw Content": bool(article.get('raw_content')),
                "Author": metadata.get('author', 'N/A'),
                "Language": metadata.get('language', 'N/A')
            }
        }
            logger.info(f"Formatted article data: {article_data}")
            formatted_results["Articles"].append(article_data)
    
        return formatted_results

def display_results(session_id: str) -> None:
    """Display research results for a given session"""
    verifier = ResearchVerifier()
    results = verifier.verify_session(session_id)
    
    if results:
        print("\nGathered Sources:")
        print("-" * 60 + "\n")
        
        displayed_urls = set()
        total_content_length = 0
        articles_with_raw_content = 0

        for article_dict in results["Articles"]:
            article_details = list(article_dict.values())[0]

            url = article_details['URL']
            if url in displayed_urls:
                continue
            displayed_urls.add(url)
            
            # Basic information (always display)
            print(f"Title: {article_details['Title']}")
            print(f"URL: {article_details['URL']}")
            print(f"Relevance Score: {article_details['Relevance Score']:.2f}")
            print(f"Source: {article_details['Source']}")
            print(f"Published Date: {article_details['Published Date']}")
            print(f"Retrieved At: {article_details['Retrieved At']}")
            print(f"Response Time: {article_details['Response Time']}")

            # Display optional metadata if available
            for field in ['Author', 'Language', 'Content Length', 'Response Time']:
                if (field in article_details and 
                    article_details[field] not in ['N/A', 'Not available', 0]):
                    print(f"{field}: {article_details[field]}")
                    
            # Display content information
            if article_details.get('Content Length', 0) > 0:
                content_length = article_details['Content Length']
                print(f"Content Size: {content_length:,} characters")
                total_content_length += content_length
            if article_details.get('Has Raw Content'):
                print("Full content available")
                articles_with_raw_content += 1
            
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
        print("\n" + "=" * 50)
        print("RESEARCH SUMMARY")
        print("=" * 50)
        print(f"\nTopic: {data['topic']}")
        
        # Format timestamps
        if isinstance(session.get('timestamp'), datetime):
            timestamp = session['timestamp'].strftime('%a, %d %b %Y %H:%M:%S GMT')
        else:
            timestamp = 'N/A'
            
        if isinstance(session.get('completed_at'), datetime):
            completed_at = session['completed_at'].strftime('%a, %d %b %Y %H:%M:%S GMT')
        else:
            completed_at = 'N/A'
            
        print(f"Session Created: {timestamp}")
        print(f"Last Updated: {completed_at}")

        # Display Stats
        if 'stats' in session:
            print("\nSearch Statistics:")
            print(f"Total Results Found: {session['stats'].get('total_found', 0):,}")
            print(f"Scientific Sources: {session['stats'].get('scientific_sources', 0)}")
            print(f"Other Sources: {session['stats'].get('other_sources', 0)}")

        # Display Key Findings with error handling
        print("\n" + "-" * 20)
        print("KEY FINDINGS")
        print("-" * 20)
        try:
            for i, finding in enumerate(data['key_findings'], 1):
                print(f"\n{i}. {finding}")
        except KeyError:
            logger.warning("No key findings available")
            print("\nNo key findings available")

        # Display Processed Articles
        print("\n" + "=" * 50)
        print("PROCESSED ARTICLES")
        print("=" * 50)

        # Sort articles by date if available
        try:
            articles = data['articles']
            articles.sort(
                key=lambda x: x.get('metadata', {}).get('added_date', ''),
                reverse=True
            )

            for article in articles:
                print("\n" + "-" * 40)
                print(f"Title: {article['title']}")
                print(f"URL: {article['url']}")
                print(f"Relevance Score: {article['score']:.2f}")

                # Enhanced metadata display with error handling
                print("\nMetadata:")
                metadata = article.get('metadata', {})
                print(f"📅 Published: {metadata.get('published_date', 'N/A')}")
                print(f"📅 Added to Database: {metadata.get('added_date', 'N/A')}")
                print(f"🌐 Source: {metadata.get('source', 'web')}")
                print(f"🗣 Language: {metadata.get('language', 'en')}")

                try:
                    print("\nMain Points:")
                    for point in article['summary']['main_points']:
                        print(f"• {point}")
                except KeyError:
                    logger.warning("Missing main_points in article summary")
                    print("Main points not available")

                try:
                    print("\nKey Statistics:")
                    for stat in article['summary'].get('key_statistics', []):
                        print(f"📊 {stat}")
                except KeyError:
                    logger.warning("Missing key_statistics in article summary")
                
                try:
                    print("\nPractical Tips:")
                    for tip in article['summary'].get('practical_tips', []):
                        print(f"💡 {tip}")
                except KeyError:
                    logger.warning("Missing practical_tips in article summary")

                try:
                    print("\nExpert Opinions:")
                    for opinion in article['summary'].get('expert_opinions', []):
                        if opinion.get('expert') and opinion.get('quote'):
                            print(f"👤 {opinion['expert']}: \"{opinion['quote']}\"")
                except KeyError:
                    logger.warning("Missing expert_opinions in article summary")

                try:
                    print("\nDetailed Summary:")
                    print(article['summary']['summary'])
                except KeyError:
                    logger.warning("Missing detailed summary in article")
                    print("Detailed summary not available")

        except KeyError:
            logger.error("Missing required article data")
            print("Error processing article data")

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