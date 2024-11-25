# tests/test_mini_processor.py

import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime
from bson import ObjectId
from src.research.data_processor import MiniProcessor
from src.research.database.models import (
    ArticleSummary,
    ResearchArticle,
    ResearchSummary,
    BlogPost,
    BlogSection
)
from src.research.exceptions import ProcessingError

TEST_CONTENT = """
Recent research in artificial intelligence has shown significant improvements in language understanding.
The study conducted by researchers found that newer models achieve 95% accuracy on benchmark tests.
These improvements suggest potential applications in various fields including healthcare and education.
Key limitations include computational requirements and potential biases in training data.
"""

TEST_SESSION_ID = str(ObjectId())

@pytest.fixture
def mock_db():
    """Create mock database"""
    with patch('src.research.data_processor.ResearchDatabase') as mock:
        db = mock.return_value
        db.get_session.return_value = {
            '_id': TEST_SESSION_ID,
            'query': 'AI Research',
            'timestamp': datetime.utcnow(),
            'source': 'hybrid',
            'processed_data': {
                'topic': 'AI Research',
                'articles': [
                    {
                        'title': 'Test Article',
                        'summary': {
                            'summary': 'Test summary',
                            'main_points': ['Point 1', 'Point 2']
                        }
                    }
                ]
            }
        }
        db.get_articles.return_value = [
            {
                'title': 'Test Article',
                'url': 'https://example.com',
                'content': TEST_CONTENT
            }
        ]
        yield db

def test_article_processing():
    """Test article processing using Structured Outputs"""
    processor = MiniProcessor()
    
    with patch('openai.OpenAI') as mock_openai:
        # Mock response in JSON format as returned by the API
        mock_json_response = {
            "main_points": [
                "Significant improvements in language understanding due to recent research in AI",
                "Newer models achieve 95% accuracy on benchmark tests",
                "Potential applications in fields such as healthcare and education",
                "Key limitations include high computational requirements and potential biases in training data"
            ],
            "summary": "Recent AI research highlights advancements in language understanding, with newer models attaining 95% benchmark accuracy, although challenges like computational needs and bias remain.",
            "relevance": 0.9
        }
        
        # Create mock completion
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(mock_json_response)
                )
            )
        ]
        
        # Set up mock for chat.completions.create
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        # Process article
        article = processor.process_article(
            content=TEST_CONTENT,
            title="AI Research Advances",
            url="https://example.com/research"
        )
        
        # Verify structure
        assert isinstance(article, ResearchArticle)
        assert isinstance(article.summary, ArticleSummary)
        
        # Verify content
        assert len(article.summary.main_points) == 4
        assert all(isinstance(point, str) for point in article.summary.main_points)
        assert all(len(point) > 10 for point in article.summary.main_points)
        
        # Verify specific content
        assert any("language understanding" in point.lower() for point in article.summary.main_points)
        assert any("accuracy" in point.lower() for point in article.summary.main_points)
        assert any("healthcare" in point.lower() or "education" in point.lower() for point in article.summary.main_points)
        
        # Verify summary and score
        assert len(article.summary.summary) > 0
        assert 0 <= article.summary.relevance <= 1
        assert article.score == mock_json_response["relevance"]

def test_generate_blog_summary(mock_db):
    """Test blog summary generation"""
    processor = MiniProcessor()
    
    with patch('openai.OpenAI') as mock_openai:
        # Mock blog post response
        mock_blog_response = {
            "title": "Latest Advances in AI Research",
            "introduction": "Recent developments in AI have shown promising results...",
            "key_sections": [
                {
                    "heading": "Improved Language Understanding",
                    "content": "AI models have achieved significant improvements...",
                    "key_points": [
                        "95% accuracy on benchmarks",
                        "Better natural language processing"
                    ]
                }
            ],
            "conclusion": "The future of AI looks promising..."
        }
        
        # Create mock completion
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(mock_blog_response)
                )
            )
        ]
        
        # Set up mock for chat.completions.create
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        # Generate blog summary
        blog_content = processor.generate_blog_summary(TEST_SESSION_ID)
        
        # Verify structure (blog_content is already a dict)
        assert "title" in blog_content
        assert "introduction" in blog_content
        assert "key_sections" in blog_content
        assert "conclusion" in blog_content
        
        # Verify content
        assert len(blog_content["key_sections"]) > 0
        assert all(
            all(key in section for key in ["heading", "content", "key_points"])
            for section in blog_content["key_sections"]
        )
        
        # Verify database calls
        mock_db.get_session.assert_called_once_with(TEST_SESSION_ID)

def test_error_handling():
    """Test error handling in processor"""
    processor = MiniProcessor()
    
    with patch('openai.OpenAI') as mock_openai:
        # Create a mock that raises an exception
        mock_instance = mock_openai.return_value
        mock_instance.chat.completions.create.side_effect = Exception("API Error")
        
        # Replace the processor's client with our mock
        processor.client = mock_instance
        
        # Test exception handling
        with pytest.raises(ProcessingError) as exc_info:
            processor.process_article(
                content=TEST_CONTENT,
                title="Test",
                url="https://example.com"
            )
        
        # Verify error message
        assert "Failed to process article" in str(exc_info.value)
        assert "API Error" in str(exc_info.value)
        
        # Verify the mock was called
        mock_instance.chat.completions.create.assert_called_once()

def test_invalid_session():
    """Test handling of invalid session ID"""
    processor = MiniProcessor()
    
    with patch('src.research.data_processor.ResearchDatabase') as mock_db:
        # Mock database returning None for invalid session
        mock_db.return_value.get_session.return_value = None
        
        with pytest.raises(ProcessingError) as exc_info:
            processor.generate_blog_summary("invalid_session_id")
        
        assert "No processed data found for session" in str(exc_info.value)