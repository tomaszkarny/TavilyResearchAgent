"""
Tests for advanced search functionality
"""
import pytest
from datetime import datetime, timedelta
from src.research.tavily_client import (
    ResearchClient, 
    SearchFilters, 
    SortOrder
)

def test_search_with_filters():
    """Test search with various filters"""
    client = ResearchClient(mock_mode=True)
    
    # Test score filtering
    filters = SearchFilters(min_score=0.8)
    results = client.search(
        "test query",
        filters=filters
    )
    assert all(r['score'] >= 0.8 for r in results)
    
    # Test domain filtering
    filters = SearchFilters(domains=['example.com'])
    results = client.search(
        "test query",
        filters=filters
    )
    assert all('example.com' in r['metadata']['url'] for r in results)

def test_result_sorting():
    """Test different sorting methods"""
    client = ResearchClient(mock_mode=True)
    
    # Test sorting by date
    results = client.search(
        "test query",
        sort_by=SortOrder.DATE
    )
    if len(results) > 1:
        dates = [r['metadata']['retrieved_at'] for r in results]
        assert all(dates[i] >= dates[i+1] for i in range(len(dates)-1))
    
    # Test sorting by score
    results = client.search(
        "test query",
        sort_by=SortOrder.SCORE
    )
    if len(results) > 1:
        scores = [r['score'] for r in results]
        assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))

def test_result_grouping():
    """Test grouping of similar results"""
    client = ResearchClient(mock_mode=True)
    
    results = client.search(
        "AI and ML",
        group_similar=True
    )
    
    # Should remove similar results but keep unique ones
    all_content = [r['content'] for r in results]
    assert len(all_content) == len(set(all_content))  # No duplicates

def test_combined_functionality():
    """Test multiple features together"""
    client = ResearchClient(mock_mode=True)
    
    filters = SearchFilters(
        min_score=0.8,
        max_age_days=7,
        domains=['example.com']
    )
    
    results = client.search(
        query="AI developments",
        filters=filters,
        sort_by=SortOrder.DATE,
        group_similar=True,
        max_results=5
    )
    
    assert len(results) <= 5
    assert all(r['score'] >= 0.8 for r in results)
    assert all('example.com' in r['metadata']['url'] for r in results)
    assert all(
        r['metadata']['retrieved_at'] >= datetime.utcnow() - timedelta(days=7)
        for r in results
    )