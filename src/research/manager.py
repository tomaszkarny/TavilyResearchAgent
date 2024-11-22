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
        
    def to_search_config(self) -> SearchConfig:
        """Convert session to SearchConfig"""
        return SearchConfig(
            search_depth=self.search_depth,
            topic=self.topic,
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
                        max_results: int = 10,
                        include_domains: Optional[List[str]] = None,
                        exclude_domains: Optional[List[str]] = None,
                        min_score: float = 0.6,
                        search_depth: str = "advanced",
                        topic: str = "general",
                        language: Optional[str] = None,
                        include_answer: bool = False,
                        include_images: bool = False,
                        include_raw_content: bool = True,
                        save_results: bool = True) -> str:
        """
        Perform research on a topic and save results
        
        Args:
            query: Research topic
            max_results: Maximum number of results
            include_domains: Specific domains to include
            exclude_domains: Domains to exclude
            min_score: Minimum relevance score
            search_depth: Search depth ('basic' or 'advanced')
            topic: Search topic ('general' or 'news')
            language: Preferred language for results
            include_answer: Whether to include AI-generated answer
            include_images: Whether to include related images
            include_raw_content: Whether to include raw content
            save_results: Whether to save results to database
            
        Returns:
            str: Session ID
            
        Raises:
            SearchError: If research operation fails
            ConfigurationError: If configuration is invalid
        """
        try:
            # Create research session
            session = ResearchSession(
                query=query,
                max_results=max_results,
                min_score=min_score,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                search_depth=search_depth,
                topic=topic,
                language=language,
                include_answer=include_answer,
                include_images=include_images,
                include_raw_content=include_raw_content
            )
            
            logger.info(f"\nInitiating research for: {query}")
            logger.info(f"Configuration: {vars(session)}")
            
            # If answer or images are requested, use standard search first
            if include_answer or include_images:
                standard_results = self.client.search(
                    query=query,
                    max_results=max_results,
                    config=session.to_search_config()
                )
                answer = standard_results.get('answer')
                images = standard_results.get('images', [])
                response_time = standard_results.get('response_time')
            else:
                answer = None
                images = []
                response_time = None
            
            # Use hybrid search for main results
            hybrid_results = self.client.hybrid_search(
                query=query,
                max_results=max_results,
                max_web=max_results,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                min_score=min_score,
                save_results=save_results,
                config=session.to_search_config()
            )
            
            # Create research result
            research_result = ResearchResult(
                session_id="",  # Will be set after saving
                query=query,
                results=hybrid_results,
                answer=answer,
                images=images,
                response_time=response_time
            )
            
            # Process and enrich results
            enriched_results = self._enrich_results(research_result, session)
            
            # Save research session
            session_id = self.db.save_research_session(enriched_results, query)
            research_result.session_id = session_id
            logger.info(f"Research session saved (ID: {session_id})")
            
            # Log result statistics
            self._log_result_statistics(research_result)
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error during research: {str(e)}")
            raise SearchError(f"Research operation failed: {str(e)}")
    
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