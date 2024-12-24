# src/research/manager.py
"""
Research process manager with enhanced Tavily Hybrid RAG support.
Manages the end-to-end research process including data gathering,
storage, and retrieval using Tavily's advanced features.
"""
from typing import List, Dict, Optional, Union
from datetime import datetime
import logging
from .database.db import ResearchDatabase
from .tavily_hybrid import HybridResearchClient, SearchConfig
from .exceptions import SearchError, ConfigurationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryBuilder:
    """Helper class for building flexible search queries"""
    
    @staticmethod
    def get_domain_specific_terms(query: str, domain_type: str) -> List[str]:
        """
        Dynamically generate search terms based on query and domain type
        """
        # Base modifiers for different types of searches
        base_modifiers = {
            "scientific": [
                "research", "study", "analysis",
                "systematic review", "evidence-based"
            ],
            "news": [
                "latest", "recent", "update",
                "current", "new"
            ],
            "health": [
                "clinical", "medical", "health",
                "treatment", "practice"
            ]
        }
        
        # Get base terms for domain type
        terms = base_modifiers.get(domain_type, [])
        
        # Add domain-specific variations
        if domain_type == "scientific":
            # Add methodological terms
            terms.extend([
                "methodology",
                "meta-analysis",
                "literature review"
            ])
            
        elif domain_type == "health":
            # Add health-specific terms
            terms.extend([
                "guidelines",
                "recommendations",
                "outcomes"
            ])
            
        return terms
    
    @staticmethod
    def enhance_query(
        query: str, 
        domain_type: Optional[str] = None, 
        modifiers: Optional[List[str]] = None
                ) -> str:
                """
    Enhance query based on domain type and modifiers.

    Args:
        query: Base search query string
        domain_type: Type of domain to get specific terms from ('scientific', 'news', 'health')
        modifiers: Additional query modifiers to append

    Returns:
        str: Enhanced query with added domain terms and modifiers

    Example:
        >>> QueryBuilder.enhance_query("AI research", domain_type="scientific")
        'AI research (research OR study OR analysis OR systematic review OR evidence-based)'
    """
                enhanced_query = query
                used_terms = set()
    
                if domain_type:
        # Get domain-specific terms
                    domain_terms = QueryBuilder.get_domain_specific_terms(query, domain_type)
        
         # Add domain terms as optional matches
                    if domain_terms:
                     term_clause = " OR ".join(domain_terms)
                     enhanced_query += f" ({term_clause})"
    
         # Add any additional modifiers
                if modifiers:
                 for modifier in modifiers:
                    if modifier not in used_terms:
                     enhanced_query += f" {modifier}"
                     used_terms.add(modifier)
    
                return enhanced_query

class ResearchSession:
    """Container for research session configuration"""
    def __init__(self,
                 query: str,
                 max_results: int = 10,
                 min_score: float = 0.6,
                 include_domains: Optional[List[str]] = None,
                 exclude_domains: Optional[List[str]] = None,
                 search_depth: str = "advanced",
                 topic: str = "general",
                 days: int = 7,
                 language: Optional[str] = None,
                 include_answer: bool = False,
                 include_images: bool = False,
                 include_raw_content: bool = True) -> None:
        self.query = query
        self.max_results = max_results
        self.min_score = min_score
        self.include_domains = include_domains
        self.exclude_domains = exclude_domains
        self.search_depth = search_depth
        self.topic = topic
        self.language = language
        self.include_answer = include_answer
        self.include_images = include_images
        self.include_raw_content = include_raw_content
        self.timestamp = datetime.utcnow()
        self.days = days 
        
    def to_search_config(self) -> SearchConfig:
        """Convert session to SearchConfig"""
        return SearchConfig(
            search_depth=self.search_depth,
            topic=self.topic,
            days=self.days,
            include_answer=self.include_answer,
            include_raw_content=self.include_raw_content,
            include_images=self.include_images,
            max_results=self.max_results
        )

class ResearchResult:
    """Container for research results"""
    def __init__(self,
                 session_id: str,
                 query: str,
                 results: List[Dict],
                 answer: Optional[str] = None,
                 images: Optional[List[Dict]] = None,
                 response_time: Optional[float] = None) -> None:
        self.session_id = session_id
        self.query = query
        self.results = results
        self.answer = answer
        self.images = images or []
        self.response_time = response_time
        self.timestamp = datetime.utcnow()

class ResearchManager:
    """Manages the research process end-to-end"""
    
    def __init__(self):
        """Initialize manager components"""
        try:
            self.client = HybridResearchClient()
            self.db = ResearchDatabase()
            logger.info("ResearchManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ResearchManager: {str(e)}")
            raise ConfigurationError(f"Manager initialization failed: {str(e)}")
    
    def perform_research(self, 
                        query: str, 
                        max_results: int = 15,
                        min_score: float = 0.6,
                        include_domains: Optional[List[str]] = None,
                        exclude_domains: Optional[List[str]] = None,
                        date_filter: Optional[Dict] = None,
                        search_depth: str = "advanced",
                        query_modifiers: Optional[List[str]] = None,
                        **kwargs) -> str:
        """
        Perform research with enhanced query building and session management.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            min_score: Minimum relevance score for results
            include_domains: List of domains to include in search
            exclude_domains: List of domains to exclude from search
            date_filter: Dictionary with date range filters
            search_depth: Depth of search ("basic" or "advanced")
            query_modifiers: List of additional terms to modify query
            **kwargs: Additional search parameters

        Returns:
            str: Session ID for the research process

        Raises:
            SearchError: If search operation fails
            ConfigurationError: If required configuration is missing
        """
        try:
            logger.info(f"\nInitiating research for: {query}")
            start_time = datetime.utcnow()
            
            # Create research session
            session = ResearchSession(
                query=query,
                max_results=max_results,
                min_score=min_score,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                search_depth=search_depth,
                topic=kwargs.get('topic', 'news'),
                days=kwargs.get('days', 7),
                include_raw_content=True
            )
            
            # Initialize session in database
            session_data = {
                'query': query,
                'timestamp': start_time,
                'status': 'initialized',
                'config': {
                    'max_results': max_results,
                    'min_score': min_score,
                    'include_domains': include_domains,
                    'exclude_domains': exclude_domains,
                    'date_filter': date_filter,
                    'search_depth': search_depth,
                    'query_modifiers': query_modifiers
                }
            }
            session_id = str(self.db.sessions.insert_one(session_data).inserted_id)
            logger.info(f"Created research session: {session_id}")
            
            try:
                # Update session status
                self.db.update_session(session_id, {'status': 'searching'})
                
                all_results = []
                if include_domains:
                    # Scientific domains search
                    scientific_domains = include_domains[:8]
                    other_domains = include_domains[8:]
                    
                    scientific_queries = [
                        f"{query} (research OR study)",
                        f"{query} methodology",
                        f"{query} review",
                        query
                    ]
                    
                    for sq in scientific_queries:
                        if len(all_results) < max_results // 2:
                            try:
                                domain_clause = " OR ".join([f"site:{domain}" for domain in scientific_domains])
                                results = self.client.hybrid_search(
                                    query=f"{sq} ({domain_clause})",
                                    max_results=max_results // 4,
                                    min_score=min_score * 0.7,
                                    config=session.to_search_config(),
                                    session_id=session_id
                                )
                                if results:
                                    all_results.extend(results)
                                    # Update session progress
                                    self.db.update_session(
                                        session_id,
                                        {
                                            'progress': {
                                                'current_phase': 'scientific_search',
                                                'results_found': len(all_results)
                                            }
                                        }
                                    )
                            except Exception as e:
                                logger.warning(f"Error in scientific search: {e}")
                                continue
                    
                    # Other domains search
                    if other_domains and len(all_results) < max_results:
                        try:
                            domain_clause = " OR ".join([f"site:{domain}" for domain in other_domains])
                            results = self.client.hybrid_search(
                                query=f"{query} ({domain_clause})",
                                max_results=max_results - len(all_results),
                                min_score=min_score,
                                config=session.to_search_config(),
                                session_id=session_id
                            )
                            if results:
                                all_results.extend(results)
                                # Update session progress
                                self.db.update_session(
                                    session_id,
                                    {
                                        'progress': {
                                            'current_phase': 'other_domains_search',
                                            'results_found': len(all_results)
                                        }
                                    }
                                )
                        except Exception as e:
                            logger.warning(f"Error in other domains search: {e}")
                else:
                    # Single search without domain filters
                    all_results = self.client.hybrid_search(
                        query=query,
                        max_results=max_results * 2,
                        min_score=min_score,
                        config=session.to_search_config(),
                        session_id=session_id
                    )
                
                # Update session status for processing
                self.db.update_session(session_id, {'status': 'processing'})
                
                # Process and deduplicate results 
                seen_urls = {}
                for result in all_results:
                    url = result.get('url', '').lower()
                    current_score = result.get('score', 0)
                    if url not in seen_urls or current_score > seen_urls[url].get('score', 0):  # Bezpieczny dostęp
                        seen_urls[url] = result
                
                all_results = list(seen_urls.values())
                   
                prioritized_results = []
                other_results = []
                for result in all_results:
                    url = result.get('url', '').lower()
                    is_preferred = any(domain.lower() in url for domain in (include_domains or []))
                    if is_preferred:
                     prioritized_results.append(result)
                    elif not any(domain.lower() in url for domain in (exclude_domains or [])):
                     other_results.append(result)
                
                prioritized_results.sort(key=lambda x: x.get('score', 0), reverse=True)
                other_results.sort(key=lambda x: x.get('score', 0), reverse=True)
                
                # Combine results
                final_results = []
                scientific_limit = max_results // 2
                final_results.extend(prioritized_results[:scientific_limit])
                remaining_slots = max_results - len(final_results)
                final_results.extend(other_results[:remaining_slots])
                
                # Additional search if needed
                if len(final_results) < max_results:
                    additional_results = self.client.hybrid_search(
                        query=query,
                        max_results=max_results - len(final_results),
                        min_score=min_score * 0.7,
                        config=session.to_search_config(),
                        session_id=session_id
                    )
                    final_results.extend(additional_results)
                
                # Save results to database
                for article in final_results:
                    metadata = article.get('metadata', {})
                    published_date = metadata.get('published_date') or metadata.get('date') or 'N/A'

                     # Add debug logging
                    logger.info(f"Saving article to database:")
                    logger.info(f"Title: {article.get('title')}")
                    logger.info(f"Original metadata: {metadata}")
                    logger.info(f"Published date: {published_date}")
                    
                    article_doc = {
                        'session_id': session_id,
                        'title': article.get('title', 'N/A'),
                        'url': article.get('url', 'N/A'),
                        'content': article.get('content', ''),
                        'score': article.get('score', 0),
                        'source': article.get('source', 'web'),
                        'metadata': {
                            **metadata,
                            'published_date': published_date,
                            'added_date': datetime.utcnow().isoformat()
                        },
                        'embedding_data': article.get('embedding', [])
                    }
                    self.db.articles.insert_one(article_doc)
                
                # Update final session stats
                end_time = datetime.utcnow()
                self.db.update_session(
                    session_id=session_id,
                    update_data={
                        'status': 'completed',
                        'stats': {
                            'total_found': len(all_results),
                            'scientific_sources': len(prioritized_results),
                            'other_sources': len(other_results),
                            'final_saved': len(final_results),
                            'processing_time': (end_time - start_time).total_seconds()
                        },
                        'completed_at': end_time
                    }
                )
                
                # Log final statistics
                logger.info(f"\nSearch Result Statistics:")
                logger.info(f"Total Results Found: {len(all_results)}")
                logger.info(f"Scientific Sources: {len(prioritized_results)}")
                logger.info(f"Other Sources: {len(other_results)}")
                logger.info(f"Final Results Saved: {len(final_results)}")
                logger.info(f"Processing Time: {(end_time - start_time).total_seconds():.2f} seconds")
                
                return session_id
                
            except Exception as e:
                # Update session status on error
                self.db.update_session(
                    session_id,
                    {
                        'status': 'error',
                        'error': str(e),
                        'error_timestamp': datetime.utcnow()
                    }
                )
                raise
                
        except Exception as e:
            error_msg = f"Research operation failed: {str(e)}"
            logger.error(error_msg)
            raise SearchError(error_msg)
    
    def _enrich_results(self,
                       result: ResearchResult,
                       session: ResearchSession) -> List[Dict]:
        """
        Enrich search results with additional metadata
        
        Args:
            result: Research result container
            session: Current research session
        
        Returns:
            List of enriched results
        """
        enriched = []
        for item in result.results:
            # Add session metadata
            item['metadata'] = item.get('metadata', {})
            item['metadata'].update({
                'query': session.query,
                'search_timestamp': session.timestamp,
                'search_config': {
                    'max_results': session.max_results,
                    'min_score': session.min_score,
                    'search_depth': session.search_depth,
                    'topic': session.topic,
                    'language': session.language
                }
            })
            
            # Add any AI-generated answer if available
            if result.answer and item == result.results[0]:  # Add to first result only
                item['metadata']['ai_answer'] = result.answer
            
            enriched.append(item)
        
        # Add image results if available
        for image in result.images:
            enriched.append({
                'title': image.get('description', 'Image'),
                'url': image.get('url', ''),
                'type': 'image',
                'score': 1.0,
                'metadata': {
                    'query': session.query,
                    'search_timestamp': session.timestamp,
                    'type': 'image'
                }
            })
        
        return enriched
    
    def _log_result_statistics(self, result: ResearchResult) -> None:
        """
        Log statistics about search results
        
        Args:
            result: Research result container
        """
        if not result.results:
            logger.info("No results found")
            return
            
        # Calculate statistics
        total = len(result.results)
        text_results = len([r for r in result.results if r.get('type', 'text') == 'text'])
        image_results = len([r for r in result.results if r.get('type') == 'image'])
        avg_score = sum(r.get('score', 0) for r in result.results) / total if total > 0 else 0
        
        # Log statistics
        logger.info("\nSearch Result Statistics:")
        logger.info(f"Total Results: {total}")
        logger.info(f"Text Results: {text_results}")
        logger.info(f"Image Results: {image_results}")
        logger.info(f"Average Score: {avg_score:.2f}")
        if result.response_time:
            logger.info(f"Response Time: {result.response_time:.2f}s")
        if result.answer:
            logger.info("AI Answer: Available")
    
    def get_session_results(self, session_id: str) -> Optional[Dict]:
        """
        Get results for a specific research session
        
        Args:
            session_id: ID of the research session
            
        Returns:
            Dict containing session results or None if not found
        """
        try:
            session = self.db.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found")
                return None
            
            articles = self.db.get_articles(session_id)
            
            # Separate text and image results
            text_results = [a for a in articles if a.get('type', 'text') == 'text']
            image_results = [a for a in articles if a.get('type') == 'image']
            
            # Get AI answer if available
            ai_answer = next(
                (a['metadata'].get('ai_answer') for a in articles 
                 if a.get('metadata', {}).get('ai_answer')),
                None
            )
            
            return {
                'session': session,
                'text_results': text_results,
                'image_results': image_results,
                'ai_answer': ai_answer
            }
            
        except Exception as e:
            logger.error(f"Error retrieving session results: {str(e)}")
            return None

def test_manager():
    """Test manager functionality"""
    manager = ResearchManager()
    
    try:
        # Test comprehensive research
        session_id = manager.perform_research(
            query="Latest developments in quantum computing",
            max_results=5,
            min_score=0.7,
            search_depth="advanced",
            topic="general",
            include_answer=True,
            include_images=True
        )
        
        # Get and verify results
        results = manager.get_session_results(session_id)
        if results:
            print(f"\nTest successful!")
            print(f"Session ID: {session_id}")
            print(f"Text Results: {len(results['text_results'])}")
            print(f"Image Results: {len(results['image_results'])}")
            if results['ai_answer']:
                print("AI Answer: Available")
            return True
            
        return False
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_manager()
    print(f"\nTest {'passed' if success else 'failed'}")