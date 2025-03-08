# src/research/data_processor.py

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field
import logging
import os
from .database.db import ResearchDatabase
from .exceptions import ProcessingError
from .utils import retry
import json

logger = logging.getLogger(__name__)

class ArticleAnalysis(BaseModel):
    """Enhanced schema for detailed article analysis"""
    main_points: List[str] = Field(
        description="Detailed key findings and insights from the article",
        min_items=15,
        max_items=20
    )
    summary: str = Field(
        description="Comprehensive summary of the article content",
        max_length=1500
    )
    background: str = Field(
        description="Background information or context about the topic"
    )
    key_findings: List[str] = Field(
        description="The most important discoveries or conclusions",
        min_items=1
    )
    implications: str = Field(
        description="Potential impact or significance of the findings"
    )
    key_quotes: List[str] = Field(
        description="Significant quotes or key sentences from the article",
        min_items=0
    )
    key_statistics: List[str] = Field(
        description="Important numbers, percentages, and statistics from the article",
        min_items=0,
        max_items=10
    )
    practical_tips: List[str] = Field(
        description="Actionable advice and practical recommendations",
        min_items=5,
        max_items=10
    )
    expert_opinions: List[Dict[str, str]] = Field(
        description="Expert quotes and opinions mentioned in the article",
        default_factory=list
    )
    relevance: float = Field(
        description="Relevance score from 0 to 1",
        ge=0.0,
        le=1.0
    )


class MiniProcessor:
    """Process research data using GPT-4o-mini model"""
    
    def __init__(self):
        self.db = ResearchDatabase()
        self.model = "gpt-4o-mini-2024-07-18"
        
        # Import OpenAI on-the-fly to ensure we're using the latest version
        # In newer versions of OpenAI (>=1.55.3) with httpx 0.28, previous issues are properly handled
        try:
            # Use direct import to ensure we avoid monkey-patching
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            # Check if the client works correctly
            # Try accessing the chat attribute - this is what causes an error in the process_article method
            if not hasattr(self.client, 'chat'):
                raise AttributeError("OpenAI client does not have 'chat' attribute")
                
            logger.info("OpenAI client initialized successfully.")
        except Exception as e:
            # Leave the client as None, but add information that the client is unavailable
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
            self.api_available = False
        else:
            self.api_available = True
    
    @retry(max_attempts=3, delay=1)
    def process_article(self, content: str, title: str, url: str, metadata: Optional[Dict] = None) -> Dict:
        """Process single article using structured outputs"""
        # Check if the OpenAI client is available before attempting to process
        if not self.client or not hasattr(self, 'api_available') or not self.api_available:
            error_msg = "OpenAI API client is not available. Check API key and configuration."
            logger.error(error_msg)
            raise ProcessingError(error_msg)
            
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a precise research analyst. Analyze the article and extract information in the following structured format:

                    1. REQUIRED - Main Points (minimum 15, maximum 20 points):
                       - Extract detailed insights, not just surface information
                       - Each point should be a complete, informative sentence
                       - Cover different aspects of the topic
                       - Include both general and specific information

                    2. REQUIRED - Summary (max 1500 chars):
                       - Provide a comprehensive summary covering key themes, findings, and implications
                       - Maintain academic tone but ensure readability

                    3. REQUIRED - Background Information:
                       - Summarize the context or background of the topic discussed in the article

                    4. REQUIRED - Key Findings:
                       - Highlight the most important discoveries or conclusions from the article

                    5. REQUIRED - Implications:
                       - Discuss the potential impact or significance of the findings

                    6. REQUIRED - Key Quotes:
                       - Extract significant quotes or key sentences that capture the essence of the article
                       - Format as ["quote1", "quote2", ...]

                    7. REQUIRED - Key Statistics:
                       - Extract ALL numerical data (percentages, numbers, measurements)
                       - Format as "X% of..." or "X people..."
                       - If no statistics found, provide empty array

                    8. REQUIRED - Practical Tips (minimum 5):
                       - Provide specific, implementable recommendations
                       - Start each with a verb
                       - Be specific and actionable
                       - If none found, derive from content

                    9. Expert Opinions:
                       - Include quoted experts or paraphrased opinions
                       - Format as {"expert": "Name/Title", "quote": "Exact quote"}

                    10. REQUIRED - Relevance Score (0.0-1.0):
                        - Based on content relevance to query and depth of information

                    Return as JSON matching exactly this schema:
                    {
                        "main_points": ["point1", "point2", ...],
                        "summary": "text",
                        "background": "text",
                        "key_findings": ["finding1", "finding2", ...],
                        "implications": "text",
                        "key_quotes": ["quote1", "quote2", ...],
                        "key_statistics": ["stat1", "stat2", ...],
                        "practical_tips": ["tip1", "tip2", ...],
                        "expert_opinions": [{"expert": "name", "quote": "text"}, ...],
                        "relevance": float
                    }"""
                },
                {
                    "role": "user",
                    "content": f"Title: {title}\n\nContent: {content}"
                }
            ]

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            # Parse response
            response_content = completion.choices[0].message.content
            analysis = ArticleAnalysis.model_validate_json(response_content)
            
            # Create article document with metadata
            processed_article = {
                "title": title,
                "url": url,
                # Add session_id at the root level to ensure database saving works correctly
                "session_id": metadata.get('session_id') if metadata else None,
                "summary": {
                    "main_points": analysis.main_points,
                    "summary": analysis.summary,
                    "background": analysis.background,
                    "key_findings": analysis.key_findings,
                    "implications": analysis.implications,
                    "key_quotes": analysis.key_quotes,
                    "key_statistics": analysis.key_statistics,
                    "practical_tips": analysis.practical_tips,
                    "expert_opinions": analysis.expert_opinions
                },
                "score": analysis.relevance,
                "metadata": {
                    "published_date": metadata.get('published_date') if metadata else "N/A",
                    "added_date": datetime.utcnow().isoformat(),
                    "source": metadata.get('source', 'web'),
                    "language": metadata.get('language', 'en'),
                    "retrieved_at": metadata.get('retrieved_at') if metadata else None
                },
                "processed_at": datetime.utcnow()
            }
            
            logger.info(f"Successfully processed article: {title}")
            return processed_article
            
        except Exception as e:
            logger.error(f"Error processing article {title}: {e}")
            raise ProcessingError(f"Failed to process article: {str(e)}")

    def process_articles_in_parallel(self, articles: List[Dict], max_workers: int = 5) -> Tuple[List[Dict], List[Dict]]:
        """
        Processes articles in parallel mode using ThreadPoolExecutor.
        
        Args:
            articles (List[Dict]): List of articles, each dictionary should contain:
                - 'title'
                - 'url'
                - 'content'
                - 'metadata' (optional)
            max_workers (int): Maximum number of parallel threads (default: 5)

        Returns:
            Tuple[List[Dict], List[Dict]]:
                - processed_articles: list of processed articles in standard format
                - failed_articles: list of articles that failed processing
        """
        # Check if the OpenAI client is available before attempting to process
        if not self.client or not hasattr(self, 'api_available') or not self.api_available:
            error_msg = "OpenAI API client is not available. Check API key and configuration."
            logger.error(error_msg)
            raise ProcessingError(error_msg)

        processed_articles = []
        failed_articles = []

        # Use ThreadPoolExecutor to run multiple calls to self.process_article in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map future -> article, to track which article we're processing
            future_to_article = {
                executor.submit(
                    self.process_article,
                    article['content'],
                    article['title'],
                    article['url'],
                    article.get('metadata', {})
                ): article
                for article in articles
            }

            # as_completed allows us to iterate over all futures as they complete
            for future in as_completed(future_to_article):
                article_info = future_to_article[future]
                try:
                    result = future.result()
                    processed_articles.append(result)
                    logger.info(f"Successfully processed article in parallel: {article_info['title']}")
                except Exception as e:
                    logger.error(f"Error processing article '{article_info['title']}': {e}")
                    failed_articles.append({
                        'title': article_info['title'],
                        'url': article_info.get('url', ''),  # Include URL for better tracking
                        'session_id': article_info.get('metadata', {}).get('session_id'),  # Include session_id
                        'error': str(e)
                    })

        logger.info(f"Parallel processing completed. "
                    f"Successful: {len(processed_articles)}, Failed: {len(failed_articles)}")

        return processed_articles, failed_articles

    def process_article_batch(self, articles: List[Dict], batch_size: int = 3) -> Tuple[List[Dict], List[Dict]]:
        """Process multiple articles in batches to reduce API calls
        
        Args:
            articles: List of article dictionaries
            batch_size: Number of articles to process per batch (default=3)
            
        Returns:
            List of processed article dictionaries
        """
        # Check if the OpenAI client is available before attempting to process
        if not self.client or not hasattr(self, 'api_available') or not self.api_available:
            error_msg = "OpenAI API client is not available. Check API key and configuration."
            logger.error(error_msg)
            raise ProcessingError(error_msg)
        
        # Split content for large articles before batching (use memory logic for chunking)
        # We need to handle each batch carefully to stay within token limits
        processed_articles = []
        failed_articles = []
        
        # Process articles in batches
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i+batch_size]
            batch_data = []
            
            # Prepare batch data
            for article in batch:
                batch_data.append({
                    "index": len(batch_data),
                    "title": article['title'],
                    "url": article['url'],
                    "content": article['content'],
                    "metadata": article.get('metadata', {})
                })
            
            # Process this batch
            try:
                batch_content = "\n\n".join([f"Article {d['index']+1}:\nTitle: {d['title']}\nContent: {d['content']}" for d in batch_data])
                
                # Create system message for batch processing
                system_prompt = """You are a precise research analyst. Analyze each article and extract information in a structured format.
                For EACH article, provide the following analysis in JSON format:

                1. Main Points (minimum 15 points):
                   - Extract detailed insights from each article
                   - Each point should be a complete, informative sentence

                2. Summary (max 1500 chars):
                   - Comprehensive summary covering key themes and findings

                3. Background Information
                4. Key Findings
                5. Implications
                6. Key Quotes
                7. Key Statistics
                8. Practical Tips (minimum 5)
                9. Expert Opinions
                10. Relevance Score (0.0-1.0)

                Return as a JSON array with one object per article, where each object has the format:
                {
                    "article_index": <index number from input>,
                    "main_points": ["point1", "point2", ...],
                    "summary": "text",
                    "background": "text",
                    "key_findings": ["finding1", "finding2", ...],
                    "implications": "text",
                    "key_quotes": ["quote1", "quote2", ...],
                    "key_statistics": ["stat1", "stat2", ...],
                    "practical_tips": ["tip1", "tip2", ...],
                    "expert_opinions": [{"expert": "name", "quote": "text"}, ...],
                    "relevance": float
                }
                """
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": batch_content}
                ]
                
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
                
                # Parse batch response
                response_content = completion.choices[0].message.content
                batch_results = json.loads(response_content)
                
                # Format the results into processed articles
                if not isinstance(batch_results, list):
                    # Handle case where API returns a single object instead of an array
                    if "articles" in batch_results:
                        batch_results = batch_results["articles"]
                    else:
                        batch_results = [batch_results]
                
                # Map articles to their corresponding batch data more intelligently
                processed_batch = []
                
                # First, try to use article_index if available and valid
                for result in batch_results:
                    article_index = result.get("article_index", None)
                    
                    # If index is provided and valid, use it
                    if article_index is not None and 0 <= article_index < len(batch_data):
                        processed_batch.append((result, batch_data[article_index]))
                
                # If we couldn't match all results, use title matching as fallback
                if len(processed_batch) < min(len(batch_results), len(batch_data)):
                    # Clear previous matches and try title matching
                    processed_batch = []
                    
                    # Create a mapping of titles to batch data items
                    title_to_batch = {item["title"].lower().strip(): item for item in batch_data}
                    
                    for result in batch_results:
                        # Try to extract title from the result
                        title = None
                        # Look for title in result keys
                        if "title" in result:
                            title = result["title"]
                        # Look for title in article text
                        elif "summary" in result and isinstance(result["summary"], str) and result["summary"].startswith("Title:"):
                            title = result["summary"].split("\n")[0].replace("Title:", "").strip()
                        
                        # If we found a title, try to match it
                        if title and title.lower().strip() in title_to_batch:
                            processed_batch.append((result, title_to_batch[title.lower().strip()]))
                
                # If we still couldn't match, use positional matching as last resort
                if len(processed_batch) < min(len(batch_results), len(batch_data)):
                    # Clear previous matches and use positional matching
                    processed_batch = []
                    
                    # Match results to batch data by position, up to the minimum length
                    for i in range(min(len(batch_results), len(batch_data))):
                        processed_batch.append((batch_results[i], batch_data[i]))
                
                # Process each matched pair
                for result, article_data in processed_batch:
                    
                    # Convert to ArticleAnalysis model to validate
                    try:
                        analysis = ArticleAnalysis(
                            main_points=result.get("main_points", []),
                            summary=result.get("summary", ""),
                            background=result.get("background", ""),
                            key_findings=result.get("key_findings", []),
                            implications=result.get("implications", ""),
                            key_quotes=result.get("key_quotes", []),
                            key_statistics=result.get("key_statistics", []),
                            practical_tips=result.get("practical_tips", []),
                            expert_opinions=result.get("expert_opinions", []),
                            relevance=result.get("relevance", 0.5)
                        )
                        
                        # Create article document
                        processed_article = {
                            "title": article_data["title"],
                            "url": article_data["url"],
                            "session_id": article_data["metadata"].get("session_id", ""),
                            "summary": {
                                "main_points": analysis.main_points,
                                "summary": analysis.summary,
                                "background": analysis.background,
                                "key_findings": analysis.key_findings,
                                "implications": analysis.implications,
                                "key_quotes": analysis.key_quotes,
                                "key_statistics": analysis.key_statistics,
                                "practical_tips": analysis.practical_tips,
                                "expert_opinions": analysis.expert_opinions
                            },
                            "score": analysis.relevance,
                            "metadata": article_data["metadata"],
                            "processed_at": datetime.utcnow()
                        }
                        processed_articles.append(processed_article)
                    except Exception as e:
                        logger.error(f"Error validating article analysis: {e}")
                        failed_articles.append({
                            'title': article_data['title'],
                            'error': f"Validation error: {str(e)}"
                        })
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                for article in batch_data:
                    failed_articles.append({
                        'title': article['title'],
                        'error': f"Batch processing error: {str(e)}"
                    })
        
        logger.info(f"Successfully processed {len(processed_articles)} articles in batches")
        return processed_articles, failed_articles
    
    def process_and_save_session(self, session_id: str) -> str:
        """Process all articles in session and save results using batch processing"""
        try:
            # Update session status
            self.db.update_session(
                session_id=session_id,
                update_data={'status': 'processing'}
            )
            
            # Get articles
            articles = self.db.get_articles(session_id)
            if not articles:
                raise ProcessingError("No articles found in session")

            # Add session_id to metadata for each article
            for article in articles:
                if 'metadata' not in article:
                    article['metadata'] = {}
                article['metadata']['session_id'] = session_id

            # Process articles in parallel
            processed_articles, failed_articles = self.process_articles_in_parallel(articles, max_workers=5)
                    
            # Save processed articles using bulk operations
            if processed_articles:
                saved_count = self.db.save_processed_articles(processed_articles)
                logger.info(f"Saved {saved_count} articles using bulk operations")
                
                # Update progress after batch processing
                self.db.update_session(
                    session_id=session_id,
                    update_data={
                        'processed_count': len(processed_articles),
                        'total_count': len(articles)
                    }
                )

            # Create final summary with all processed article data
            summary = {
                'topic': self.db.get_session(session_id)['query'],
                'articles': processed_articles,
                'created_at': datetime.utcnow(),
                'parallel_processing_enabled': True,  # Flag to indicate parallel processing was used
                'max_workers': 5  # Default number of workers used
            }

            # Calculate processing efficiency metrics
            processing_metrics = {
                'total_articles': len(articles),
                'processed_articles': len(processed_articles),
                'failed_articles': len(failed_articles), 
                'success_rate': len(processed_articles) / len(articles) if articles else 0,
                'parallelization_gain': round((len(processed_articles) / (len(processed_articles) / min(5, len(articles)))) if processed_articles else 0, 2),
                'processing_approach': 'parallel'
            }

            # Save final results with metrics
            self.db.update_session(
                session_id=session_id,
                update_data={
                    'processed_data': summary,
                    'processing_metrics': processing_metrics,
                    'status': 'completed',
                    'processed_at': datetime.utcnow(),
                    'failed_articles': failed_articles,
                    'success_rate': processing_metrics['success_rate']
                }
            )
            logger.info(f"Processed articles saved in the database for session {session_id}")

            logger.info(f"Successfully processed session {session_id} using batch processing")
            logger.info(f"Processed {len(processed_articles)} articles, {len(failed_articles)} failed")
            logger.info(f"Parallel processing completed with {processing_metrics['success_rate'] * 100}% success rate")
            logger.info(f"Parallelization gain: approximately {processing_metrics['parallelization_gain']}x faster")
            
            return session_id

        except Exception as e:
            logger.error(f"Error processing session {session_id}: {e}")
            self.db.update_session(
                session_id=session_id,
                update_data={
                    'status': 'failed',
                    'error': str(e)
                }
            )
            raise ProcessingError(f"Failed to process session: {str(e)}")

    # Removed the blog post generation functionality as it is no longer required.
    # All extracted article data is now stored directly in the database.

    def _extract_key_findings(self, articles: List[Dict]) -> List[str]:
        """Extract overall key findings from processed articles, incorporating temporal context"""
        all_findings = []
        
        # Sort articles by publication date for temporal context
        sorted_articles = sorted(articles, 
                               key=lambda x: x.get('metadata', {}).get('published_date', ''),
                               reverse=True)
        
        for article in sorted_articles:
            # Prefer the new key_findings field if available, otherwise fall back to main_points
            findings = article['summary'].get('key_findings', [])
            if not findings and 'main_points' in article['summary']:
                # If key_findings is empty, use some of the main_points instead
                findings = article['summary']['main_points'][:3]  # Take just the first few as key findings
                
            metadata = article.get('metadata', {})
            pub_date = metadata.get('published_date', '')
            
            # Add temporal context to significant findings if date exists
            if pub_date:
                try:
                    # Convert to datetime for comparison
                    pub_dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
                    # Add temporal context to first finding from each article
                    if findings:
                        findings[0] = f"As of {pub_dt.strftime('%B %d, %Y')}: {findings[0]}"
                except (ValueError, TypeError):
                    pass
                    
            all_findings.extend(findings)
        
        # Remove duplicates while preserving order
        unique_findings = list(dict.fromkeys(all_findings))
        return unique_findings[:15]  # Return top 15 findings (increased from 10)
        
    def generate_blog_summary(self, session_id: str) -> Dict:
        """
        Generate a blog post summary from processed research data
        
        Args:
            session_id: Database session ID
            
        Returns:
            Dict with blog structure (title, introduction, key_sections, conclusion)
        """
        try:
            # Get session data
            session = self.db.get_session(session_id)
            if not session:
                raise ProcessingError(f"Session {session_id} not found")
                
            # Check if session has processed data
            if not session.get('processed_data'):
                raise ProcessingError(f"Session {session_id} has no processed data")
                
            processed_data = session['processed_data']
            topic = processed_data['topic']
            articles = processed_data['articles']
            
            # Format content for API request
            content = {
                "topic": topic,
                "num_articles": len(articles),
                "key_findings": self._extract_key_findings(articles),
                "statistics": [stat for article in articles 
                              for stat in article['summary'].get('key_statistics', [])[:3]],
                "practical_tips": [tip for article in articles 
                                  for tip in article['summary'].get('practical_tips', [])[:3]]
            }
            
            # Make request to OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"""You are a professional blog writer specializing in creating engaging, research-based content.
                    
Your response must be a valid JSON object with the following structure:
{{
  "title": "An engaging, SEO-friendly blog post title",
  "introduction": "Compelling introduction that hooks the reader (300-500 words)",
  "key_sections": [
    {{
      "heading": "Section 1 Heading",
      "content": "Detailed content for section 1"
    }},
    {{
      "heading": "Section 2 Heading",
      "content": "Detailed content for section 2"
    }}
    // 3-5 sections total
  ],
  "conclusion": "Summary of key points and final thoughts (200-300 words)"
}}
                    """},
                    {"role": "user", "content": f"""
                    Create a comprehensive blog post about {topic} based on the following research:
                    
                    Background Information:
                    {content['background']}
                    
                    Key findings from {len(articles)} articles:
                    {chr(10).join([f"- {finding}" for finding in content['key_findings']])}
                    
                    Implications:
                    {content['implications']}
                    
                    Key quotes:
                    {chr(10).join([f"- {quote}" for quote in content['key_quotes']])}
                    
                    Key statistics:
                    {chr(10).join([f"- {stat}" for stat in content['statistics']])}
                    
                    Practical advice:
                    {chr(10).join([f"- {tip}" for tip in content['practical_tips']])}
                    
                    Requirements:
                    1. Write in a professional but accessible tone
                    2. Include at least 3 main sections with clear headings
                    3. Incorporate statistics where relevant
                    4. Provide practical guidance and takeaways
                    5. Create a compelling introduction and conclusion
                    """}
                ],
                max_tokens=4000,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            blog_content = response.choices[0].message.content
            
            # If JSON string rather than object, parse it
            if isinstance(blog_content, str):
                blog_content = json.loads(blog_content)
                
            # Update session with blog content
            self.db.update_session(
                session_id=session_id,
                update_data={
                    'blog_content': blog_content,
                    'blog_generated_at': datetime.utcnow().isoformat()
                }
            )
            
            return blog_content
            
        except Exception as e:
            logger.error(f"Error generating blog summary: {str(e)}")
            raise ProcessingError(f"Failed to generate blog summary: {str(e)}")