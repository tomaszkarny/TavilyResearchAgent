"""
Tests for Tavily Research Client and Hybrid Search
"""
import pytest
from datetime import datetime
from src.research.tavily_client import ResearchClient, SearchFilters, SortOrder
from src.research.tavily_hybrid import HybridResearchClient

def test_basic_search():
    """Test basic search functionality"""
    client = ResearchClient(mock_mode=True)
    results = client.search("test query", max_results=2)
    
    assert isinstance(results, list)
    assert len(results) <= 2
    assert all('content' in r for r in results)
    assert all('score' in r for r in results)
    assert all('metadata' in r for r in results)

def test_hybrid_search():
    """Test hybrid search functionality"""
    client = HybridResearchClient()
    results = client.hybrid_search(
        "test query",
        max_results=2,
        max_web=1,
        max_local=1,
        min_score=0.6
    )
    
    assert isinstance(results, list)
    assert len(results) <= 2
    assert all('content' in r for r in results)
    assert all('score' in r for r in results)
    assert all(r.get('score', 0) >= 0.6 for r in results)

def test_domain_filtering():
    """Test domain filtering in hybrid search"""
    client = HybridResearchClient()
    
    # Test with excluded domains
    results = client.hybrid_search(
        "test query",
        max_results=5,
        exclude_domains=['example.com'],
        min_score=0.6
    )
    
    assert all('example.com' not in r.get('url', '') for r in results)
    
    # Test with included domains
    results = client.hybrid_search(
        "test query",
        max_results=5,
        include_domains=['github.com'],
        min_score=0.6
    )
    
    if results:  # Some results found
        assert any('github.com' in r.get('url', '') for r in results)

def test_document_saving():
    """Test document saving functionality"""
    client = HybridResearchClient()
    
    # Test document below score threshold
    low_score_doc = {
        'content': 'test content',
        'score': 0.4,
        'title': 'Test Title',
        'url': 'http://test.com'
    }
    processed = client._save_document(low_score_doc)
    assert processed is None
    
    # Test valid document
    good_score_doc = {
        'content': 'test content',
        'score': 0.8,
        'title': 'Test Title',
        'url': 'http://test.com',
        'metadata': {
            'author': 'Test Author',
            'published_date': '2024-01-01'
        }
    }
    processed = client._save_document(good_score_doc)
    assert processed is not None
    assert processed['score'] == 0.8
    assert 'metadata' in processed
    assert 'embedding' in processed

def test_similarity_calculation():
    """Test text similarity calculation"""
    client = ResearchClient(mock_mode=True)
    
    # Test identical texts
    assert client._calculate_similarity("test text", "test text") == 1.0
    
    # Test similar texts
    similarity = client._calculate_similarity(
        "AI and machine learning",
        "AI and deep learning"
    )
    assert 0.5 < similarity < 1.0
    
    # Test different texts
    similarity = client._calculate_similarity(
        "AI and machine learning",
        "Weather forecast tomorrow"
    )
    assert similarity < 0.3

def test_are_results_similar():
    """Test similarity detection between results"""
    client = ResearchClient(mock_mode=True)
    
    result1 = {
        'content': 'AI and machine learning advances',
        'metadata': {'title': 'AI Progress'}
    }
    
    result2 = {
        'content': 'AI and deep learning progress',
        'metadata': {'title': 'AI Updates'}
    }
    
    result3 = {
        'content': 'Weather forecast for tomorrow',
        'metadata': {'title': 'Weather News'}
    }
    
    # Similar results should be detected
    assert client._are_results_similar(result1, result2) is True
    
    # Different results should not be similar
    assert client._are_results_similar(result1, result3) is False

def test_error_handling():
    """Test error handling in hybrid search"""
    client = HybridResearchClient()
    
    # Test invalid domain format
    with pytest.raises(Exception):
        client.hybrid_search(
            "test query",
            include_domains=["not a valid domain"]
        )
    
    # Test invalid score range
    with pytest.raises(Exception):
        client.hybrid_search(
            "test query",
            min_score=2.0  # Invalid score > 1.0
        )