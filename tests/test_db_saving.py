#!/usr/bin/env python
"""
Test script to verify that database saving works correctly with all required fields.
This script simulates the article processing and verifies that session_id is included
at the root level of processed articles.
"""

import os
import json
import logging
from datetime import datetime
from src.research.data_processor import MiniProcessor
from src.research.database.db import ResearchDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_articles(session_id):
    """Create sample articles for testing"""
    return [
        {
            'title': 'Test Article 1',
            'url': 'https://example.com/article1',
            'content': 'This is a test article with some content for processing.',
            'metadata': {
                'session_id': session_id,
                'published_date': '2023-01-01',
                'source': 'test'
            }
        },
        {
            'title': 'Test Article 2',
            'url': 'https://example.com/article2',
            'content': 'Another test article with different content for testing.',
            'metadata': {
                'session_id': session_id,
                'published_date': '2023-01-02',
                'source': 'test'
            }
        }
    ]

def verify_processed_articles(processed_articles, session_id):
    """Verify that all processed articles have the required fields"""
    all_valid = True
    
    for i, article in enumerate(processed_articles):
        # Check for required fields
        missing_fields = []
        
        if 'url' not in article or not article['url']:
            missing_fields.append('url')
        
        if 'session_id' not in article or not article['session_id']:
            missing_fields.append('session_id')
        elif article['session_id'] != session_id:
            logger.error(f"Article {i+1} has incorrect session_id: {article['session_id']} vs {session_id}")
            all_valid = False
        
        if missing_fields:
            logger.error(f"Article {i+1} missing required fields: {', '.join(missing_fields)}")
            all_valid = False
        else:
            logger.info(f"Article {i+1} has all required fields ✓")
            
    return all_valid

def test_db_saving_mock():
    """Test database saving with mock data (no actual DB connection)"""
    session_id = f"test-session-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    processor = MiniProcessor()
    
    # Skip if OpenAI API is not available
    if not processor.api_available:
        logger.warning("OpenAI API not available. Skipping test.")
        return False

    # Create test articles
    articles = create_test_articles(session_id)
    
    # Process articles in parallel
    processed_articles, failed_articles = processor.process_articles_in_parallel(articles, max_workers=2)
    
    # Verify processed articles
    success = verify_processed_articles(processed_articles, session_id)
    
    # Print results
    logger.info(f"Test completed with {'SUCCESS' if success else 'FAILURE'}")
    logger.info(f"Processed {len(processed_articles)} articles, {len(failed_articles)} failed")
    
    if failed_articles:
        logger.info("Failed articles:")
        for article in failed_articles:
            logger.info(f"  - {article['title']}: {article['error']}")
            # Verify failed articles have session_id
            if 'session_id' not in article or not article['session_id']:
                logger.error(f"Failed article {article['title']} missing session_id")
                success = False
    
    return success

def main():
    """Run all tests"""
    logger.info("Starting database saving tests...")
    
    # Test with mock data
    mock_success = test_db_saving_mock()
    
    if mock_success:
        logger.info("All tests PASSED ✓")
    else:
        logger.error("Some tests FAILED ✗")

if __name__ == "__main__":
    main()
