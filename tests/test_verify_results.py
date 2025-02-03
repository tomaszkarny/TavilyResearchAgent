import pytest
from datetime import datetime
from src.research.verify_results import ResearchVerifier
from src.research.database.db import ResearchDatabase

@pytest.fixture
def mock_article():
    return {
        '_id': 'test_id',
        'title': 'Test Article',
        'url': 'https://test.com/article',
        'content': 'Test content',
        'score': 0.95,
        'metadata': {
            'source': 'tavily',
            'published_date': 'Mon, 06 Jan 2025 16:40:47 GMT',
            'retrieved_at': datetime(2025, 1, 6, 17, 31, 41),
            'added_date': '2025-01-06T17:31:41.533662'
        }
    }

@pytest.fixture
def mock_session():
    return {
        '_id': 'test_session',
        'query': 'test query',
        'status': 'completed'
    }

def test_verify_session_date_formatting(mock_article, mock_session):
    """Test that dates are correctly formatted in verify_session"""
    
    class MockDB:
        def get_session(self, session_id):
            return mock_session
            
        def get_articles(self, session_id):
            return [mock_article]
    
    verifier = ResearchVerifier()
    verifier.db = MockDB()
    
    results = verifier.verify_session('test_session')
    assert results is not None
    
    article_data = results['Articles'][0]['Article 1']
    assert 'Published' in article_data
    assert 'Retrieved' in article_data
    
    # Check date formatting
    assert article_data['Published'] == 'Mon, 06 Jan 2025 16:40:47 GMT'
    assert article_data['Retrieved'] == 'Mon, 06 Jan 2025 17:31:41 GMT'

def test_verify_session_missing_dates():
    """Test handling of missing dates in verify_session"""
    
    article_without_dates = {
        '_id': 'test_id',
        'title': 'Test Article',
        'url': 'https://test.com/article',
        'content': 'Test content',
        'score': 0.95,
        'metadata': {
            'source': 'tavily'
        }
    }
    
    class MockDB:
        def get_session(self, session_id):
            return {'_id': 'test_session', 'query': 'test query'}
            
        def get_articles(self, session_id):
            return [article_without_dates]
    
    verifier = ResearchVerifier()
    verifier.db = MockDB()
    
    results = verifier.verify_session('test_session')
    assert results is not None
    
    article_data = results['Articles'][0]['Article 1']
    
    # Check that missing dates don't cause errors
    assert article_data['Published'] is None
    assert article_data['Retrieved'] is None

def test_verify_session_multiple_articles(mock_article):
    """Test handling of multiple articles with different dates"""
    
    article2 = mock_article.copy()
    article2['metadata'] = {
        'source': 'tavily',
        'published_date': 'Tue, 07 Jan 2025 10:00:00 GMT',
        'retrieved_at': datetime(2025, 1, 7, 11, 0, 0)
    }
    
    class MockDB:
        def get_session(self, session_id):
            return {'_id': 'test_session', 'query': 'test query'}
            
        def get_articles(self, session_id):
            return [mock_article, article2]
    
    verifier = ResearchVerifier()
    verifier.db = MockDB()
    
    results = verifier.verify_session('test_session')
    assert results is not None
    assert len(results['Articles']) == 2
    
    # Check first article dates
    article1_data = results['Articles'][0]['Article 1']
    assert article1_data['Published'] == 'Mon, 06 Jan 2025 16:40:47 GMT'
    assert article1_data['Retrieved'] == 'Mon, 06 Jan 2025 17:31:41 GMT'
    
    # Check second article dates
    article2_data = results['Articles'][1]['Article 2']
    assert article2_data['Published'] == 'Tue, 07 Jan 2025 10:00:00 GMT'
    assert article2_data['Retrieved'] == 'Tue, 07 Jan 2025 11:00:00 GMT'
