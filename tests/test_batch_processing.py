"""
Test batch processing and bulk database operations
Applied: codeStructure_001, codeStructure_002, codeStructure_003
"""
import os
import pytest
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch
from src.research.data_processor import MiniProcessor, ArticleAnalysis
from src.research.database.db import ResearchDatabase

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data
TEST_ARTICLES = [
    {
        "title": "Test Article 1",
        "url": "https://example.com/article1",
        "content": "This is the content of test article 1. It contains information about various topics.",
        "metadata": {"published_date": "2023-01-01", "source": "test", "language": "en"}
    },
    {
        "title": "Test Article 2",
        "url": "https://example.com/article2",
        "content": "This is the content of test article 2. It discusses different aspects of the subject.",
        "metadata": {"published_date": "2023-01-02", "source": "test", "language": "en"}
    },
    {
        "title": "Test Article 3",
        "url": "https://example.com/article3",
        "content": "This is the content of test article 3. It explores various dimensions of the topic.",
        "metadata": {"published_date": "2023-01-03", "source": "test", "language": "en"}
    },
    {
        "title": "Test Article 4",
        "url": "https://example.com/article4",
        "content": "This is the content of test article 4. It analyzes the core concepts in detail.",
        "metadata": {"published_date": "2023-01-04", "source": "test", "language": "en"}
    }
]

# Mock OpenAI API response for batch processing
MOCK_BATCH_RESPONSE = [
    {
        "article_index": 0,
        "main_points": ["Point 1.1", "Point 1.2", "Point 1.3", "Point 1.4", "Point 1.5", 
                      "Point 1.6", "Point 1.7", "Point 1.8", "Point 1.9", "Point 1.10",
                      "Point 1.11", "Point 1.12", "Point 1.13", "Point 1.14", "Point 1.15"],
        "summary": "Summary of article 1",
        "background": "Background of article 1",
        "key_findings": ["Finding 1.1", "Finding 1.2"],
        "implications": "Implications of article 1",
        "key_quotes": ["Quote 1.1", "Quote 1.2"],
        "key_statistics": ["Stat 1.1", "Stat 1.2"],
        "practical_tips": ["Tip 1.1", "Tip 1.2", "Tip 1.3", "Tip 1.4", "Tip 1.5"],
        "expert_opinions": [{"expert": "Expert 1.1", "quote": "Expert quote 1.1"}],
        "relevance": 0.8
    },
    {
        "article_index": 1,
        "main_points": ["Point 2.1", "Point 2.2", "Point 2.3", "Point 2.4", "Point 2.5", 
                      "Point 2.6", "Point 2.7", "Point 2.8", "Point 2.9", "Point 2.10",
                      "Point 2.11", "Point 2.12", "Point 2.13", "Point 2.14", "Point 2.15"],
        "summary": "Summary of article 2",
        "background": "Background of article 2",
        "key_findings": ["Finding 2.1", "Finding 2.2"],
        "implications": "Implications of article 2",
        "key_quotes": ["Quote 2.1", "Quote 2.2"],
        "key_statistics": ["Stat 2.1", "Stat 2.2"],
        "practical_tips": ["Tip 2.1", "Tip 2.2", "Tip 2.3", "Tip 2.4", "Tip 2.5"],
        "expert_opinions": [{"expert": "Expert 2.1", "quote": "Expert quote 2.1"}],
        "relevance": 0.9
    },
    {
        "article_index": 2,
        "main_points": ["Point 3.1", "Point 3.2", "Point 3.3", "Point 3.4", "Point 3.5", 
                      "Point 3.6", "Point 3.7", "Point 3.8", "Point 3.9", "Point 3.10",
                      "Point 3.11", "Point 3.12", "Point 3.13", "Point 3.14", "Point 3.15"],
        "summary": "Summary of article 3",
        "background": "Background of article 3",
        "key_findings": ["Finding 3.1", "Finding 3.2"],
        "implications": "Implications of article 3",
        "key_quotes": ["Quote 3.1", "Quote 3.2"],
        "key_statistics": ["Stat 3.1", "Stat 3.2"],
        "practical_tips": ["Tip 3.1", "Tip 3.2", "Tip 3.3", "Tip 3.4", "Tip 3.5"],
        "expert_opinions": [{"expert": "Expert 3.1", "quote": "Expert quote 3.1"}],
        "relevance": 0.7
    }
]


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client for testing"""
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_choices = MagicMock()
    mock_message = MagicMock()
    
    # Set up the mock response structure
    mock_message.content = '{"articles": ' + str(MOCK_BATCH_RESPONSE).replace("'", '"') + '}'
    mock_choices.choices = [MagicMock(message=mock_message)]
    mock_completion.create.return_value = mock_choices
    mock_client.chat = mock_completion
    
    # Fix serialization issues
    def mock_json():
        return MOCK_BATCH_RESPONSE
    
    # Patch json.loads to return our mock data
    with patch('json.loads', return_value=MOCK_BATCH_RESPONSE):
        yield mock_client


@pytest.fixture
def mock_database():
    """Create a mock database for testing"""
    mock_db = MagicMock(spec=ResearchDatabase)
    
    # Set up the mock db.save_processed_articles method
    mock_db.save_processed_articles.return_value = 3
    
    # Set up mock session data
    mock_db.get_session.return_value = {
        "query": "test query",
        "timestamp": datetime.utcnow(),
        "status": "pending"
    }
    
    # Set up mock articles
    mock_db.get_articles.return_value = TEST_ARTICLES
    
    return mock_db


class TestBatchProcessing:
    """Test the batch processing functionality"""
    
    def test_process_article_batch(self, mock_openai_client, mock_database):
        """Test that article batch processing works correctly"""
        # Initialize processor with mocks
        processor = MiniProcessor()
        processor.client = mock_openai_client
        processor.api_available = True
        processor.db = mock_database
        
        # Process a batch of articles
        processed_articles, failed_articles = processor.process_article_batch(
            TEST_ARTICLES[:3],  # Use first 3 articles
            batch_size=3
        )
        
        # Verify results
        assert len(processed_articles) == 3, "Should process 3 articles"
        assert len(failed_articles) == 0, "Should have no failed articles"
        
        # Verify article structure
        for i, article in enumerate(processed_articles):
            assert article["title"] == TEST_ARTICLES[i]["title"], f"Title mismatch for article {i}"
            assert article["url"] == TEST_ARTICLES[i]["url"], f"URL mismatch for article {i}"
            assert "summary" in article, f"Missing summary for article {i}"
            assert "main_points" in article["summary"], f"Missing main_points for article {i}"
            assert "key_findings" in article["summary"], f"Missing key_findings for article {i}"
    
    @patch('src.research.data_processor.MiniProcessor.process_article_batch')
    def test_process_and_save_session(self, mock_batch_process, mock_database):
        """Test session processing with batch processing and bulk DB operations"""
        # Set up the mock batch processor
        mock_processed = []
        for i, article in enumerate(TEST_ARTICLES):
            processed = {
                "title": article["title"],
                "url": article["url"],
                "session_id": "test_session",
                "summary": {
                    "main_points": [f"Point {i}.{j}" for j in range(1, 16)],
                    "summary": f"Summary of article {i}",
                    "background": f"Background of article {i}",
                    "key_findings": [f"Finding {i}.{j}" for j in range(1, 3)],
                    "implications": f"Implications of article {i}",
                    "key_quotes": [f"Quote {i}.{j}" for j in range(1, 3)],
                    "key_statistics": [f"Stat {i}.{j}" for j in range(1, 3)],
                    "practical_tips": [f"Tip {i}.{j}" for j in range(1, 6)],
                    "expert_opinions": [{"expert": f"Expert {i}.{j}", "quote": f"Expert quote {i}.{j}"} for j in range(1, 2)]
                },
                "score": 0.8 + (i * 0.1) % 0.3,
                "metadata": article["metadata"],
                "processed_at": datetime.utcnow()
            }
            mock_processed.append(processed)
        
        mock_batch_process.return_value = (mock_processed, [])
        
        # Initialize processor with mocks
        processor = MiniProcessor()
        processor.db = mock_database
        
        # Process the session
        session_id = "test_session"
        result = processor.process_and_save_session(session_id)
        
        # Verify calls
        mock_database.get_articles.assert_called_once_with(session_id)
        mock_batch_process.assert_called_once()
        mock_database.save_processed_articles.assert_called_once()
        
        # Verify session updates
        assert mock_database.update_session.call_count >= 2, "Should update session at least twice"
        
        # Verify final result
        assert result == session_id, "Should return the session ID"
        
    def test_save_processed_articles_bulk(self, mock_database):
        """Test bulk saving of processed articles"""
        # Prepare test articles
        processed_articles = []
        for i, article in enumerate(TEST_ARTICLES):
            processed = {
                "title": article["title"],
                "url": article["url"],
                "session_id": "test_session",
                "summary": {
                    "main_points": [f"Point {i}.{j}" for j in range(1, 16)],
                    "summary": f"Summary of article {i}"
                },
                "metadata": article["metadata"]
            }
            processed_articles.append(processed)
        
        # Call the bulk save method
        result = mock_database.save_processed_articles(processed_articles)
        
        # Verify the result
        assert result == 3, "Should return the number of bulk saved articles"
        mock_database.save_processed_articles.assert_called_once_with(processed_articles)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
