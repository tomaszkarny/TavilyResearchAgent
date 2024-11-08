"""
Tests for Tavily Research Client
"""
import pytest
from datetime import datetime
from src.research.tavily_client import ResearchClient, SearchFilters, SortOrder

def test_basic_search():
    """Test basic search functionality"""
    client = ResearchClient(mock_mode=True)
    results = client.search("test query", max_results=2)
    
    assert isinstance(results, list)
    assert len(results) <= 2
    assert all('content' in r for r in results)
    assert all('score' in r for r in results)
    assert all('metadata' in r for r in results)

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
    
    # Test empty texts
    assert client._calculate_similarity("", "") == 0.0
    assert client._calculate_similarity("test", "") == 0.0

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