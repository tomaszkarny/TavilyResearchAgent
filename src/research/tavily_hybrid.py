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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class SearchConfig:
    """Configuration for Tavily search parameters"""
    def __init__(
        self,
        search_depth: str = "advanced",
        topic: str = "general",
        include_answer: bool = False,
        include_raw_content: bool = True,
        include_images: bool = False,
        max_results: int = 5
    ):
        self.search_depth = search_depth
        self.topic = topic
        self.include_answer = include_answer
        self.include_raw_content = include_raw_content
        self.include_images = include_images
        self.max_results = max_results

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
        
        # Extract main search results
        for result in response.get('results', []):
            processed = {
                'title': result.get('title', 'N/A'),
                'url': result.get('url', 'N/A'),
                'content': result.get('content', ''),
                'raw_content': result.get('raw_content'),
                'score': result.get('score', 0),
                'source': 'web',
                'metadata': {
                    'source': 'tavily',
                    'published_date': result.get('published_date'),
                    'retrieved_at': datetime.utcnow()
                }
            }
            processed_results.append(processed)
        
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
        
        return processed_results
    
    def hybrid_search(self,
                     query: str,
                     max_results: int = 10,
                     max_web: Optional[int] = None,
                     include_domains: Optional[List[str]] = None,
                     exclude_domains: Optional[List[str]] = None,
                     min_score: float = 0.6,
                     save_results: bool = True,
                     config: Optional[SearchConfig] = None) -> List[Dict]:
        """
        Perform search using Tavily API and local database
        
        Args:
            query: Search query
            max_results: Maximum total results
            max_web: Maximum web results
            include_domains: Specific domains to include
            exclude_domains: Domains to exclude
            min_score: Minimum relevance score
            save_results: Whether to save web results
            config: Additional search configuration
        """
        try:
            logger.info(f"Starting search for: {query}")
            
            # Use default config if none provided
            config = config or SearchConfig()
            
            # Get web results
            response = self.tavily_client.search(
                query=query,
                max_results=max_web or max_results,
                search_depth=config.search_depth,
                topic=config.topic,
                include_answer=config.include_answer,
                include_raw_content=config.include_raw_content,
                include_images=config.include_images,
                include_domains=include_domains,
                exclude_domains=exclude_domains
            )
            
            # Process results
            all_results = self._process_search_response(response)
            
            # Rank results using Cohere
            if all_results:
                ranked_results = self._rank_results(query, all_results, max_results)
                results = [r for r in ranked_results if r.get('score', 0) >= min_score]
            else:
                results = []
            
            # Save results if requested
            if save_results and results:
                logger.info("Saving results to database")
                session_id = self.db.save_research_session(results, query)
                logger.info(f"Results saved with session ID: {session_id}")
            
            logger.info(f"Found {len(results)} relevant results")
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise SearchError(f"Search operation failed: {str(e)}")
    
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
                include_answer=config.include_answer,
                include_raw_content=config.include_raw_content,
                include_images=config.include_images
            )
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise SearchError(f"Search operation failed: {str(e)}")