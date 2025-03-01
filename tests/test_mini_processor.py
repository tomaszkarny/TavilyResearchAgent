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
    
    # Prepare a mock for metadata that will return None for any key to avoid NoneType errors
    mock_metadata = MagicMock()
    mock_metadata.get.return_value = None
    
    with patch('openai.OpenAI') as mock_openai, patch('src.research.data_processor.ArticleAnalysis') as mock_analysis:
        # Set up mock ArticleAnalysis to return a known object
        mock_analysis_instance = MagicMock()
        mock_analysis_instance.main_points = [
            "Significant improvements in language understanding due to recent research in AI",
            "Newer models achieve 95% accuracy on benchmark tests",
            "Potential applications in fields such as healthcare and education",
            "Key limitations include high computational requirements and potential biases in training data",
            "Researchers have conducted extensive testing on multiple datasets",
            "The study results were published in a peer-reviewed conference",
            "Several teams collaborated on this research initiative",
            "Benchmark comparisons show progress over previous state-of-the-art models",
            "The models use transformers and attention mechanisms",
            "Future work will focus on reducing computational requirements"
        ]
        mock_analysis_instance.summary = "Recent AI research highlights advancements in language understanding, with newer models attaining 95% benchmark accuracy, although challenges like computational needs and bias remain."
        mock_analysis_instance.key_statistics = ["95% accuracy on benchmark tests", "50% reduction in training time compared to previous models"]
        mock_analysis_instance.practical_tips = ["Consider computational requirements before implementing newer models", "Test for biases in training data before deployment"]
        mock_analysis_instance.expert_opinions = [{"expert": "Dr. Smith", "quote": "These results represent a significant breakthrough."}]
        mock_analysis_instance.relevance = 0.9
        
        # Make model_validate_json return our mock instance
        mock_analysis.model_validate_json.return_value = mock_analysis_instance
        
        # Mock response content
        mock_json_response = {
            "main_points": mock_analysis_instance.main_points,
            "summary": mock_analysis_instance.summary,
            "key_statistics": mock_analysis_instance.key_statistics,
            "practical_tips": mock_analysis_instance.practical_tips,
            "expert_opinions": mock_analysis_instance.expert_opinions,
            "relevance": mock_analysis_instance.relevance
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
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        processor.client = mock_client  # Explicitly set the client to avoid None
        
        # Process article with custom metadata
        article = processor.process_article(
            content=TEST_CONTENT,
            title="AI Research Advances",
            url="https://example.com/research",
            metadata={"published_date": "2023-01-01", "source": "example.com"}
        )
        
        # Verify API call
        assert mock_client.chat.completions.create.call_count > 0
        
        # Verify returned data structure
        assert isinstance(article, dict)
        assert 'title' in article
        assert 'url' in article
        assert 'summary' in article
        assert 'score' in article
        assert 'metadata' in article
        
        # Verify content
        assert len(article['summary']['main_points']) >= 10
        assert all(isinstance(point, str) for point in article['summary']['main_points'])
        assert all(len(point) > 10 for point in article['summary']['main_points'])
        
        # Verify specific content
        assert any("language understanding" in point.lower() for point in article['summary']['main_points'])
        assert any("accuracy" in point.lower() for point in article['summary']['main_points'])
        assert any("healthcare" in point.lower() or "education" in point.lower() for point in article['summary']['main_points'])
        
        # Verify summary and score
        assert len(article['summary']['summary']) > 0
        assert 'key_statistics' in article['summary']
        assert 'practical_tips' in article['summary']
        assert 'expert_opinions' in article['summary']
        assert 0 <= article['score'] <= 1
        assert article['score'] == mock_analysis_instance.relevance

def test_generate_blog_summary(mock_db):
    """Test blog summary generation"""
    processor = MiniProcessor()
    
    # Create a patch for the OpenAI client
    with patch('openai.OpenAI') as mock_openai:
        # Mock response for blog generation
        mock_blog_response = {
            "title": "The Future of AI: A Comprehensive Analysis",
            "introduction": "Artificial Intelligence continues to reshape our world...",
            "key_sections": [
                {
                    "heading": "Recent Advancements",
                    "content": "The field of AI has seen remarkable progress..."
                },
                {
                    "heading": "Applications in Healthcare",
                    "content": "AI is transforming healthcare through improved diagnostics..."
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
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        
        # Set the processor's client to our mock
        mock_openai.return_value = mock_client
        processor.client = mock_client
        
        # Mock session data
        mock_session = {
            'processed_data': {
                'topic': 'AI research',
                'articles': [
                    {
                        'summary': {
                            'main_points': ['AI models show 95% accuracy', 'Applications in healthcare are growing'],
                            'key_statistics': ['95% accuracy on benchmarks', '50% reduction in error rates'],
                            'practical_tips': ['Implement AI gradually', 'Focus on data quality']
                        },
                        'metadata': {'published_date': 'Wed, 01 Jan 2023 12:00:00 GMT'}
                    }
                ]
            }
        }
        mock_db.get_session.return_value = mock_session
        
        # Generate blog summary
        blog_content = processor.generate_blog_summary(TEST_SESSION_ID)
        
        # Verify API call was made
        assert mock_client.chat.completions.create.call_count > 0
        
        # Verify structure of blog content
        assert "title" in blog_content
        assert "introduction" in blog_content
        assert "key_sections" in blog_content
        assert "conclusion" in blog_content
        
        # Verify content
        assert len(blog_content["key_sections"]) > 0
        assert all(
            all(key in section for key in ["heading", "content"])
            for section in blog_content["key_sections"]
        )
        
        # Verify database calls
        mock_db.get_session.assert_called_once_with(TEST_SESSION_ID)
        mock_db.update_session.assert_called_once()

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
        
        # Verify the mock was called at least once (due to retry decorator)
        assert mock_instance.chat.completions.create.call_count > 0

def test_invalid_session():
    """Test handling of invalid session ID"""
    processor = MiniProcessor()
    
    with patch('src.research.data_processor.ResearchDatabase') as mock_db:
        # Set up the mock to raise an exception for invalid session ID
        from bson.errors import InvalidId
        mock_db.return_value.get_session.side_effect = InvalidId("Invalid session_id format")
        
        with pytest.raises(ProcessingError) as exc_info:
            processor.generate_blog_summary("invalid_session_id")
        
        # Check that the error message contains information about invalid session ID
        assert "Invalid session_id format" in str(exc_info.value)
        assert "Failed to generate blog summary" in str(exc_info.value)