#!/usr/bin/env python
"""
Test script for verifying the parallel article processing functionality in the TavilyResearchAgent.
This script tests the process_articles_in_parallel method to ensure it correctly processes multiple
articles concurrently.
"""

import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Import our modules
from src.research.data_processor import MiniProcessor
from src.research.database.db import ResearchDatabase

def create_test_articles(count=3):
    """Create sample articles for testing."""
    
    # Sample article content with varying lengths
    sample_contents = [
        """
        Artificial Intelligence in Healthcare: A Comprehensive Review
        
        Artificial intelligence (AI) is revolutionizing healthcare delivery across the globe. From diagnostic assistance to personalized treatment plans, AI applications are becoming increasingly integrated into clinical workflows. This article examines the current state of AI in healthcare, highlighting key applications, challenges, and future directions.
        
        Machine learning algorithms have demonstrated remarkable accuracy in analyzing medical images, often matching or exceeding human performance in detecting conditions like diabetic retinopathy, skin cancer, and lung nodules. Natural language processing systems are helping to extract valuable insights from unstructured clinical notes, while predictive analytics models are enabling early identification of patients at risk for deterioration.
        
        Despite these promising developments, significant challenges remain, including concerns about data privacy, algorithmic bias, and the need for robust validation studies. Healthcare organizations must navigate regulatory frameworks while ensuring that AI systems integrate seamlessly into existing clinical workflows without disrupting patient care.
        
        Looking ahead, the convergence of AI with other emerging technologies like genomics and wearable devices promises to accelerate the shift toward precision medicine, enabling truly personalized healthcare interventions tailored to an individual's unique biological makeup and health status.
        """,
        
        """
        Climate Adaptation Strategies for Urban Areas
        
        As climate change intensifies, cities worldwide are developing innovative strategies to adapt to rising temperatures, increased flooding, and other environmental challenges. This article presents a comprehensive overview of urban climate adaptation approaches, drawing on case studies from diverse geographical contexts.
        
        Heat island mitigation strategies include expanding urban tree canopies, implementing cool roofs and pavements, and designing buildings with improved natural ventilation. To address flooding risks, cities are creating water-sensitive urban designs with permeable surfaces, bioswales, and constructed wetlands that can absorb and filter stormwater while providing recreational spaces for residents.
        
        Beyond physical infrastructure, successful adaptation requires robust governance systems, community engagement, and attention to equity concerns. Vulnerable populations, including low-income communities and the elderly, often face disproportionate climate impacts and may have fewer resources to adapt.
        
        The article concludes by emphasizing the importance of integrating adaptation planning with broader sustainability goals, including greenhouse gas reduction efforts and improvements to public health and quality of life.
        """,
        
        """
        The Role of Blockchain in Supply Chain Transparency
        
        Blockchain technology offers unprecedented opportunities to enhance transparency and traceability across global supply chains. This article examines how distributed ledger systems are being deployed across industries to verify product origins, ensure ethical sourcing, and build consumer trust.
        
        By creating immutable records of transactions at each stage of the supply chain, blockchain enables stakeholders to track products from raw materials to finished goods. This capability is particularly valuable in industries plagued by counterfeiting, fraud, or ethical concerns, such as pharmaceuticals, luxury goods, and food products.
        
        Implementation examples include IBM's Food Trust network, which allows consumers to scan QR codes on products to access verified information about their journey from farm to store. Similarly, in the diamond industry, platforms like Everledger help verify the ethical sourcing of gemstones and combat the trade in conflict diamonds.
        
        While adoption challenges include technical complexity, scaling issues, and the need for industry-wide standards, proponents argue that blockchain's potential to reduce fraud, minimize recalls, and strengthen brand reputation makes it a worthwhile investment for forward-thinking organizations committed to supply chain integrity.
        """
    ]
    
    # If we need more articles than we have samples, duplicate them
    while len(sample_contents) < count:
        sample_contents.extend(sample_contents[:count-len(sample_contents)])
    
    # Create the article dictionaries
    articles = []
    for i in range(count):
        articles.append({
            'title': f"Test Article {i+1}",
            'url': f"https://example.com/article{i+1}",
            'content': sample_contents[i],
            'metadata': {
                'session_id': f"test_session_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'source': 'test_script'
            }
        })
    
    return articles

def test_parallel_processing():
    """Test the parallel processing functionality."""
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")
        return
    
    # Create processor instance
    processor = MiniProcessor()
    
    # Create test articles (adjust count as needed)
    article_count = 5
    articles = create_test_articles(article_count)
    
    logger.info(f"Testing parallel processing with {article_count} articles...")
    
    # Time the parallel processing
    start_time = time.time()
    processed_articles, failed_articles = processor.process_articles_in_parallel(
        articles, 
        max_workers=3  # Adjust as needed
    )
    end_time = time.time()
    
    # Calculate results
    total_time = end_time - start_time
    success_count = len(processed_articles)
    failure_count = len(failed_articles)
    
    # Display results
    logger.info("=" * 50)
    logger.info("PARALLEL PROCESSING TEST RESULTS")
    logger.info("=" * 50)
    logger.info(f"Articles processed: {success_count}/{article_count}")
    logger.info(f"Articles failed: {failure_count}/{article_count}")
    logger.info(f"Total processing time: {total_time:.2f} seconds")
    logger.info(f"Average time per article: {total_time/article_count:.2f} seconds")
    
    # Log details about processed articles
    if processed_articles:
        logger.info("\nProcessed Articles:")
        for i, article in enumerate(processed_articles):
            logger.info(f"  {i+1}. {article['title']} - Score: {article['score']}")
            
    # Log details about failed articles
    if failed_articles:
        logger.info("\nFailed Articles:")
        for i, article in enumerate(failed_articles):
            logger.info(f"  {i+1}. {article['title']} - Error: {article.get('error', 'Unknown error')}")
    
    # For comparison, also test sequential processing if we have the regular process_article method
    try:
        logger.info("\nTesting sequential processing for comparison...")
        seq_start_time = time.time()
        
        # Process each article individually
        seq_processed = []
        seq_failed = []
        for article in articles:
            try:
                result = processor.process_article(
                    article['content'], 
                    article['title'], 
                    article['url'], 
                    article.get('metadata', {})
                )
                seq_processed.append(result)
            except Exception as e:
                seq_failed.append({
                    'title': article['title'],
                    'error': str(e)
                })
        
        seq_end_time = time.time()
        seq_total_time = seq_end_time - seq_start_time
        
        logger.info("=" * 50)
        logger.info("SEQUENTIAL PROCESSING RESULTS")
        logger.info("=" * 50)
        logger.info(f"Articles processed: {len(seq_processed)}/{article_count}")
        logger.info(f"Total processing time: {seq_total_time:.2f} seconds")
        logger.info(f"Average time per article: {seq_total_time/article_count:.2f} seconds")
        
        # Calculate speedup
        if seq_total_time > 0:
            speedup = seq_total_time / total_time
            logger.info(f"\nParallel speedup: {speedup:.2f}x faster than sequential processing")
        
    except Exception as e:
        logger.error(f"Error during sequential testing: {e}")
    
    return processed_articles, failed_articles

if __name__ == "__main__":
    test_parallel_processing()
