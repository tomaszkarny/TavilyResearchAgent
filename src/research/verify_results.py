# src/research/verify_results.py
"""
Verify and display research results with hybrid search support
"""
import logging
import textwrap
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
            published_date = (
                metadata.get('published_date') or 
                article.get('published_date') or 
                metadata.get('date') or 
                article.get('date')
            )
            retrieved_at = metadata.get('retrieved_at')
        
        # Format retrieved_at date
            if isinstance(retrieved_at, datetime):
                retrieved_at = retrieved_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
            elif isinstance(retrieved_at, str):
                retrieved_at = retrieved_at
            else:
                retrieved_at = None
        
            article_data = {
                f"Article {idx}": {
                    "Title": article.get('title', 'N/A'),
                    "URL": article.get('url', 'N/A'),
                    "Relevance Score": article.get('score', 0),
                    "Source": "Tavily Search",
                    "Published": published_date,
                    "Retrieved": retrieved_at,
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

            # Debug logging
            logger.info(f"Article details before display: {article_details}")
            
            # Basic information (always display)
            print(f"\nTitle: {article_details['Title']}")
            print(f"URL: {article_details['URL']}")
            print(f"Relevance Score: {article_details['Relevance Score']:.2f}")
            print(f"Source: {article_details['Source']}")
            
            # Display dates if available
            if article_details.get('Published'):
                print(f"Published: {article_details['Published']}")
            if article_details.get('Retrieved'):
                print(f"Retrieved: {article_details['Retrieved']}")
            
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
        
     

def generate_key_findings(articles: List[Dict], max_findings: int = 5) -> List[str]:
    """
    Generate key findings from article summaries if they're not already available
    
    Args:
        articles: List of processed article dictionaries
        max_findings: Maximum number of key findings to generate
    Returns:
        List[str]: Generated key findings
    """
    # Initialize findings list
    findings = []
    
    # Extract main points from articles and deduplicate
    unique_points = set()
    
    for article in articles:
        if 'summary' in article and 'main_points' in article['summary']:
            for point in article['summary']['main_points']:
                # Create a simplified version for deduplication (lowercase, remove punctuation)
                simple_point = ''.join(c.lower() for c in point if c.isalnum() or c.isspace())
                if simple_point not in unique_points and len(simple_point) > 20:  # Avoid very short points
                    unique_points.add(simple_point)
                    findings.append(point)
    
    # Sort findings by length and take the top ones (prefer more detailed findings)
    findings.sort(key=len, reverse=True)
    return findings[:max_findings]


def display_long_text(text: str, width: int = 80, chunk_size: int = 2000) -> None:
    """
    Display long text content in chunks to prevent terminal truncation
    
    Args:
        text: The long text content to display
        width: Line width for text wrapping
        chunk_size: Maximum characters to display at once
    """
    # First wrap the text to the specified width
    wrapped_text = textwrap.fill(text, width=width)
    
    # If text is shorter than chunk_size, just print it all
    if len(wrapped_text) <= chunk_size:
        print(wrapped_text)
        return
    
    # Otherwise, display it in chunks with pagination
    chunks = [wrapped_text[i:i+chunk_size] for i in range(0, len(wrapped_text), chunk_size)]
    
    # Display the first chunk immediately
    print(chunks[0])
    
    # Display remaining chunks with pagination
    for i, chunk in enumerate(chunks[1:], 1):
        input(f"\n--- Press Enter to continue reading ({i}/{len(chunks)-1}) ---")
        print(chunk)


def display_processed_data(session_id: str) -> Optional[Dict]:
    """
    Display processed data for a research session with pagination to prevent terminal truncation

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
            key_findings = data.get('key_findings', [])
            
            # Generate key findings if none exist
            if not key_findings and 'articles' in data and len(data['articles']) > 0:
                key_findings = generate_key_findings(data['articles'])
                
            if key_findings:
                for i, finding in enumerate(key_findings, 1):
                    print(f"\n{i}. {finding}")
            else:
                logger.warning("No key findings available")
                print("\nNo key findings available")
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

            for article_idx, article in enumerate(articles):
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

                # Pagination for article content to prevent truncation
                try:
                    main_points = article['summary']['main_points']
                    if main_points:
                        print("\nMain Points:")
                        for i, point in enumerate(main_points):
                            print(f"• {point}")
                except KeyError:
                    logger.warning("Missing main_points in article summary")
                    print("Main points not available")

                try:
                    stats = article['summary'].get('key_statistics', [])
                    if stats:
                        print("\nKey Statistics:")
                        for stat in stats:
                            print(f"📊 {stat}")
                except KeyError:
                    logger.warning("Missing key_statistics in article summary")
                
                try:
                    tips = article['summary'].get('practical_tips', [])
                    if tips:
                        print("\nPractical Tips:")
                        for tip in tips:
                            print(f"💡 {tip}")
                except KeyError:
                    logger.warning("Missing practical_tips in article summary")

                try:
                    opinions = article['summary'].get('expert_opinions', [])
                    if opinions:
                        print("\nExpert Opinions:")
                        for opinion in opinions:
                            if opinion.get('expert') and opinion.get('quote'):
                                print(f"👤 {opinion['expert']}: \"{opinion['quote']}\"")
                except KeyError:
                    logger.warning("Missing expert_opinions in article summary")

                try:
                    if summary := article['summary'].get('summary'):
                        print("\nDetailed Summary:")
                        display_long_text(summary)
                except KeyError:
                    logger.warning("Missing detailed summary in article")
                    print("Detailed summary not available")
                
                # Add pagination prompt after every 2 articles except the last
                if article_idx < len(articles) - 1 and (article_idx + 1) % 2 == 0:
                    input("\nPress Enter to continue viewing articles...")

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