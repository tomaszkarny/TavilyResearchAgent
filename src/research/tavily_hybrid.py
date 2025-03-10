# src/research/tavily_hybrid.py
"""
Modified Tavily client for basic search functionality
without vector search requirements.
"""
from typing import List, Dict, Optional
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
import cohere
from .exceptions import ConfigurationError, SearchError
from .database.db import ResearchDatabase
from tavily import TavilyClient

logger = logging.getLogger(__name__)

load_dotenv()

class SearchConfig:
    """Configuration for Tavily search parameters"""
    def __init__(
        self,
        search_depth: str = "advanced",
        topic: str = "news",
        include_answer: bool = False,
        include_raw_content: bool = True,
        include_images: bool = False,
        max_results: int = 5,
        days: int = 7
    ):
        self.search_depth = search_depth
        self.topic = topic
        self.include_answer = include_answer
        self.include_raw_content = include_raw_content
        self.include_images = include_images
        self.max_results = max_results
        self.days = days

class HybridResearchClient:
    """Enhanced research client with Cohere ranking"""
    
    def __init__(self):
        """Initialize the research client"""
        self.db = ResearchDatabase()
        self._setup_clients()
        logger.info("Research Client initialized")
    
    def _setup_clients(self):
        """Setup Tavily and Cohere clients"""
        try:
            tavily_api_key = os.getenv('TAVILY_API_KEY')
            cohere_api_key = os.getenv('COHERE_API_KEY')
            
            if not all([tavily_api_key, cohere_api_key]):
                raise ConfigurationError("Missing required API keys")
            
            # Initialize Cohere client
            self.cohere_client = cohere.Client(cohere_api_key)
            logger.info("Cohere client initialized")
            
            # Initialize Tavily client
            self.tavily_client = TavilyClient(api_key=tavily_api_key)
            logger.info("Tavily client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize clients: {str(e)}")
            raise ConfigurationError(f"Client initialization failed: {str(e)}")
    
    def _rank_results(self, query: str, documents: List[Dict], top_n: int) -> List[Dict]:
        """Rank search results using Cohere's rerank"""
        try:
            if not documents:
                return []
                
            texts = [doc.get('content', '') for doc in documents]
            
            response = self.cohere_client.rerank(
                query=query,
                documents=texts,
                top_n=min(len(texts), top_n),
                model='rerank-multilingual-v2.0'
            )
            
            ranked_docs = []
            for hit in response.results:
                doc = documents[hit.index].copy()
                doc['score'] = hit.relevance_score
                ranked_docs.append(doc)
            
            logger.info(f"Ranked {len(ranked_docs)} documents")
            return ranked_docs
            
        except Exception as e:
            logger.error(f"Ranking failed: {str(e)}")
            raise SearchError(f"Failed to rank results: {str(e)}")
    
    def _process_search_response(self, response: Dict) -> List[Dict]:
        """Process Tavily search response"""
        processed_results = []
        
        # Log raw response structure
        logger.info("Raw Tavily response structure:")
        logger.info(f"Keys in response: {list(response.keys())}")

        # Extract main search results
        for i, result in enumerate(response.get('results', [])):
            # Log complete result data for debugging
            logger.info(f"\nResult {i+1} complete data:")
            logger.info(f"Available fields: {list(result.keys())}")
            
            # Extract publication date with fallbacks
            published_date = (
                result.get('published_date') or
                result.get('date') or
                result.get('metadata', {}).get('published_date') or
                result.get('metadata', {}).get('date')
            )
            
            if published_date:
                logger.info(f"Found publication date in Tavily response: {published_date}")
            else:
                logger.warning(f"No publication date found for article: {result.get('title')}")
            
            processed = {
                'title': result.get('title', 'N/A'),
                'url': result.get('url', 'N/A'),
                'content': result.get('content', ''),
                'raw_content': result.get('raw_content'),
                'score': result.get('score', 0),
                'source': 'web',
                'metadata': {
                    'source': 'tavily',
                    'published_date': published_date,
                    'retrieved_at': datetime.utcnow()
                }
            }
            processed_results.append(processed)

        # Log sample of processed results
        if processed_results:
            logger.info("\nSample processed result metadata:")
            logger.info(f"First result metadata: {processed_results[0]['metadata']}")

        # Extract any included images if available
        if images := response.get('images'):
            for img_url in images:
                processed_results.append({
                    'title': 'Image',
                    'url': img_url,
                    'type': 'image',
                    'score': 1.0,
                    'source': 'web',
                    'metadata': {
                        'source': 'tavily',
                        'type': 'image',
                        'retrieved_at': datetime.utcnow()
                    }
                })
        
        logger.info(f"\nProcessed {len(processed_results)} results")
        
        return processed_results
    
    def hybrid_search(self,
                     query: str,
                     max_results: int = 10,
                     max_web: Optional[int] = None,
                     include_domains: Optional[List[str]] = None,
                     exclude_domains: Optional[List[str]] = None,
                     min_score: float = 0.6,
                     save_results: bool = True,
                     config: Optional[SearchConfig] = None,
                     session_id: Optional[str] = None) -> List[Dict]:
        """
        Perform hybrid search with proper session management.

        Args:
            query: Search query
            max_results: Maximum total results
            max_web: Maximum web results
            include_domains: Specific domains to include
            exclude_domains: Domains to exclude
            min_score: Minimum relevance score
            save_results: Whether to save web results
            config: Additional search configuration
            session_id: Optional ID of existing session to update

        Returns:
            List of ranked search results

        Raises:
            SearchError: If search operation fails
            ConfigurationError: If required configuration is missing
        """
        start_time = datetime.utcnow()
        try:
            logger.info(f"Starting search for: {query}" + 
                       (f" with session ID: {session_id}" if session_id else ""))
            
            # Use default config if none provided
            config = config or SearchConfig()
            
            # Update session status if exists
            if session_id:
                try:
                    self.db.update_session(
                        session_id=session_id,
                        update_data={
                            'status': 'searching',
                            'last_updated': datetime.utcnow(),
                            'search_config': {
                                'query': query,
                                'max_results': max_results,
                                'min_score': min_score,
                                'include_domains': include_domains,
                                'exclude_domains': exclude_domains,
                                'search_depth': config.search_depth
                            }
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to update initial session status: {str(e)}")

            logger.info("Sending search request to Tavily with parameters:")
            logger.info(f"Query: {query}")
            logger.info(f"Search depth: {config.search_depth}")
            logger.info(f"Topic: {config.topic}")
            logger.info(f"Days: {config.days}")
            
            # Get web results
            response = self.tavily_client.search(
                query=query,
                max_results=max_web or max_results,
                search_depth=config.search_depth,
                topic=config.topic,
                days=config.days,
                include_answer=config.include_answer,
                include_raw_content=config.include_raw_content,
                include_images=config.include_images,
                include_domains=include_domains,
                exclude_domains=exclude_domains
            )
         
            logger.info("Raw Tavily API Response Keys:")
            for key in response.keys():
                logger.info(f"- {key}")
            if response.get('results'):
                logger.info("Sample Result Keys:")
                logger.info(list(response['results'][0].keys()))
            
            # Process results
            all_results = self._process_search_response(response)
            
            # Rank results using Cohere
            ranked_results = []
            if all_results:
                ranked_results = self._rank_results(query, all_results, max_results)
                results = [r for r in ranked_results if r.get('score', 0) >= min_score]
            else:
                results = []
            
            # Save or update results if requested
            if save_results and results:
                try:
                    if session_id:
                        logger.info(f"Updating existing session: {session_id}")
                        update_response = self.db.update_session(
                            session_id=session_id,
                            update_data={
                                'status': 'completed',
                                'results': results,
                                'result_count': len(results),
                                'last_updated': datetime.utcnow(),
                                'search_metadata': {
                                    'total_found': len(all_results),
                                    'ranked_count': len(ranked_results),
                                    'final_count': len(results),
                                    'processing_time': (datetime.utcnow() - start_time).total_seconds()
                                }
                            }
                        )
                        if update_response.get('success'):
                            logger.info(f"Successfully updated session: {session_id}")
                        else:
                            logger.warning(f"Session update completed with status: {update_response.get('message')}")
                    else:
                        logger.info("Creating new research session")
                        session_id = self.db.save_research_session(results, query)
                        logger.info(f"Created new session with ID: {session_id}")
                except Exception as e:
                    logger.error(f"Failed to {'update' if session_id else 'save'} session: {str(e)}")
                    # Continue execution even if session management fails
            
            logger.info(f"Found {len(results)} relevant results")
            return results[:max_results]
            
        except Exception as e:
            error_msg = f"Search operation failed: {str(e)}"
            logger.error(error_msg)
            
            # Update session with error status if it exists
            if session_id:
                try:
                    self.db.update_session(
                        session_id=session_id,
                        update_data={
                            'status': 'failed',
                            'error': error_msg,
                            'last_updated': datetime.utcnow(),
                            'search_metadata': {
                                'error_timestamp': datetime.utcnow(),
                                'processing_time': (datetime.utcnow() - start_time).total_seconds()
                            }
                        }
                    )
                except Exception as db_error:
                    logger.error(f"Failed to update error status: {db_error}")
            
            raise SearchError(error_msg)
    
    def search(self,
              query: str,
              max_results: int = 5,
              config: Optional[SearchConfig] = None) -> Dict:
        """Basic Tavily search with full response"""
        try:
            logger.info(f"Performing search for: {query}")
            config = config or SearchConfig(max_results=max_results)
            
            return self.tavily_client.search(
                query=query,
                max_results=max_results,
                search_depth=config.search_depth,
                topic=config.topic,
                days=config.days,
                include_answer=config.include_answer,
                include_raw_content=config.include_raw_content,
                include_images=config.include_images
            )
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise SearchError(f"Search operation failed: {str(e)}")