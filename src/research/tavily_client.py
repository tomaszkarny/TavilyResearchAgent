"""
Enhanced Tavily client with advanced search capabilities.
"""
import os
import logging
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from dotenv import load_dotenv
from .exceptions import ConfigurationError, SearchError, DocumentProcessingError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv() 


class SortOrder(Enum):
    """Enumeration for sort orders"""
    RELEVANCE = "relevance"
    DATE = "date"
    SCORE = "score"

@dataclass
class SearchFilters:
    """Search filters configuration"""
    min_score: float = 0.5
    max_age_days: Optional[int] = None
    domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    content_type: Optional[List[str]] = None

class ResearchClient:
    """Client for handling research operations using Tavily Hybrid RAG."""
    
    def __init__(self, mock_mode: bool = False):
        """Initialize the client"""
        self.mock_mode = mock_mode
        if not mock_mode:
            self._setup_client()

    def _setup_client(self):
        """Set up the Tavily client"""
        if not self.mock_mode:
            try:
                from tavily import TavilyHybridClient
                from ..database.db_connection import get_collection
                
                self.collection = get_collection()
                self.client = TavilyHybridClient(
                    api_key=os.getenv('TAVILY_API_KEY'),
                    db_provider="mongodb",
                    collection=self.collection,
                    index="vector_index",
                    embeddings_field="embeddings",
                    content_field="content"
                )
            except Exception as e:
                raise ConfigurationError(f"Failed to initialize Tavily client: {str(e)}")

    def search(self, 
              query: str, 
              filters: Optional[SearchFilters] = None,
              sort_by: SortOrder = SortOrder.RELEVANCE,
              max_results: int = 5,
              max_local: Optional[int] = None,
              max_foreign: Optional[int] = None,
              group_similar: bool = False,
              use_hybrid: bool = False) -> List[Dict]:
        """
        Perform advanced search with filtering, sorting, and grouping.
        
        Args:
            query: Search query
            filters: Optional search filters
            sort_by: How to sort results
            max_results: Maximum number of results
            max_local: Maximum number of local results
            max_foreign: Maximum number of foreign results
            group_similar: Whether to group similar results
            use_hybrid: Whether to use hybrid search mode
            
        Returns:
            List of search results
        """
        try:
            # Get mock results in test mode
            if self.mock_mode:
                results = [
                    {
                        'content': 'AI and machine learning developments',
                        'score': 0.95,
                        'metadata': {
                            'title': 'AI News',
                            'url': 'https://example.com/ai-news',
                            'retrieved_at': datetime.utcnow()
                        }
                    },
                    {
                        'content': 'Deep learning and neural networks',
                        'score': 0.85,
                        'metadata': {
                            'title': 'ML Updates',
                            'url': 'https://example.com/ml-updates',
                            'retrieved_at': datetime.utcnow() - timedelta(days=1)
                        }
                    },
                    {
                        'content': 'Weather forecast for tomorrow',
                        'score': 0.75,
                        'metadata': {
                            'title': 'Weather News',
                            'url': 'https://weather.com/forecast',
                            'retrieved_at': datetime.utcnow() - timedelta(days=2)
                        }
                    }
                ]
            else:
                # Get results from Tavily API
                if use_hybrid:
                    results = self.client.hybrid_search(
                        query=query,
                        max_results=max_results * 2,
                        max_local=max_local,
                        max_foreign=max_foreign
                    )
                else:
                    results = self.client.search(
                        query=query,
                        max_results=max_results * 2,
                        max_local=max_local,
                        max_foreign=max_foreign
                    )

            # Apply filters if provided
            if filters:
                results = self._apply_filters(results, filters)
            
            # Sort results
            results = self._sort_results(results, sort_by)
            
            # Group similar results if requested
            if group_similar:
                results = self._group_similar_results(results)
            
            # Return requested number of results
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise SearchError(f"Search operation failed: {str(e)}")

    def _apply_filters(self, results: List[Dict], filters: SearchFilters) -> List[Dict]:
        """Apply filters to search results"""
        filtered = results.copy()
        
        # Filter by score
        if filters.min_score > 0:
            filtered = [r for r in filtered if r.get('score', 0) >= filters.min_score]
        
        # Filter by age
        if filters.max_age_days:
            cutoff = datetime.utcnow() - timedelta(days=filters.max_age_days)
            filtered = [
                r for r in filtered
                if r.get('metadata', {}).get('retrieved_at', datetime.utcnow()) >= cutoff
            ]
        
        # Filter by domains
        if filters.domains:
            filtered = [
                r for r in filtered
                if any(domain in r.get('metadata', {}).get('url', '')
                      for domain in filters.domains)
            ]
        
        # Exclude domains
        if filters.exclude_domains:
            filtered = [
                r for r in filtered
                if not any(domain in r.get('metadata', {}).get('url', '')
                          for domain in filters.exclude_domains)
            ]
        
        return filtered

    def _sort_results(self, results: List[Dict], sort_by: SortOrder) -> List[Dict]:
        """Sort results based on specified criteria"""
        if sort_by == SortOrder.RELEVANCE:
            return sorted(results, key=lambda x: x.get('score', 0), reverse=True)
        
        elif sort_by == SortOrder.DATE:
            return sorted(
                results,
                key=lambda x: x.get('metadata', {}).get('retrieved_at', datetime.min),
                reverse=True
            )
        
        elif sort_by == SortOrder.SCORE:
            return sorted(results, key=self._calculate_combined_score, reverse=True)
        
        return results

    def _calculate_combined_score(self, result: Dict) -> float:
        """Calculate combined score based on multiple factors"""
        base_score = result.get('score', 0)
        age_penalty = self._calculate_age_penalty(result)
        quality_boost = self._calculate_quality_boost(result)
        
        return base_score * (1 - age_penalty) * (1 + quality_boost)

    def _calculate_age_penalty(self, result: Dict) -> float:
        """Calculate penalty for older results"""
        retrieved_at = result.get('metadata', {}).get('retrieved_at')
        if not retrieved_at:
            return 0.0
            
        age_days = (datetime.utcnow() - retrieved_at).days
        return min(age_days / 365.0, 0.5)  # Max 50% penalty for old results

    def _calculate_quality_boost(self, result: Dict) -> float:
        """Calculate quality boost based on metadata"""
        boost = 0.0
        metadata = result.get('metadata', {})
        
        # Boost for having complete metadata
        if all(key in metadata for key in ['title', 'url', 'author']):
            boost += 0.1
            
        # Boost for trusted domains
        if metadata.get('url', '').endswith(('.edu', '.gov', '.org')):
            boost += 0.2
            
        return min(boost, 0.5)  # Max 50% boost

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        if not text1 or not text2:
            return 0.0
            
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0

    def _are_results_similar(self, result1: Dict, result2: Dict) -> bool:
        """Check if two results are similar enough to be grouped"""
        # Compare titles
        title1 = result1.get('metadata', {}).get('title', '').lower()
        title2 = result2.get('metadata', {}).get('title', '').lower()
        
        if title1 and title2:
            title_similarity = self._calculate_similarity(title1, title2)
            if title_similarity > 0.8:
                return True
        
        # Compare content
        content1 = result1.get('content', '').lower()
        content2 = result2.get('content', '').lower()
        content_similarity = self._calculate_similarity(content1, content2)
        
        return content_similarity > 0.6

    def _group_similar_results(self, results: List[Dict]) -> List[Dict]:
        """Group similar results and return the best from each group"""
        if not results:
            return []
            
        grouped = []
        processed = set()
        
        for i, result in enumerate(results):
            if i in processed:
                continue
                
            similar_group = [result]
            processed.add(i)
            
            # Find similar results
            for j, other in enumerate(results[i+1:], i+1):
                if j not in processed and self._are_results_similar(result, other):
                    similar_group.append(other)
                    processed.add(j)
            
            # Add the best result from the group
            best_result = max(similar_group, key=lambda x: x.get('score', 0))
            grouped.append(best_result)
        
        return grouped