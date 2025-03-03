# src/research/data_processor.py

from typing import List, Dict, Optional
from datetime import datetime
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
        min_items=10,
        max_items=15
    )
    summary: str = Field(
        description="Comprehensive summary of the article content",
        max_length=1000
    )
    key_statistics: List[str] = Field(
        description="Important numbers, percentages, and statistics from the article",
        min_items=0,
        max_items=10
    )
    practical_tips: List[str] = Field(
        description="Actionable advice and practical recommendations",
        min_items=0,
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

                    1. REQUIRED - Main Points (MUST provide at least 10, up to 15 points):
                       - Extract detailed insights, not just surface information
                       - Each point should be a complete, informative sentence
                       - Cover different aspects of the topic
                       - Include both general and specific information

                    2. REQUIRED - Summary (max 1000 chars):
                       - Comprehensive yet concise
                       - Cover key themes and findings
                       - Maintain academic tone

                    3. REQUIRED - Key Statistics:
                       - Extract ALL numerical data
                       - Include percentages, numbers, and measurements
                       - Format as "X% of..." or "X people..."
                       - If no statistics found, provide empty array

                    4. REQUIRED - Practical Tips:
                       - Minimum 3 actionable recommendations
                       - Start each with a verb
                       - Be specific and implementable
                       - If none found, derive from content

                    5. Expert Opinions:
                       - Include any quoted experts
                       - Format as {"expert": "Name/Title", "quote": "Exact quote"}
                       - If no direct quotes, look for paraphrased expert opinions

                    6. REQUIRED - Relevance Score (0.0-1.0):
                       - Based on content relevance to query
                       - Consider depth and specificity

                    Return as JSON matching exactly this schema:
                    {
                        "main_points": ["point1", "point2", ...], // MINIMUM 10 points
                        "summary": "text",
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
                "summary": {
                    "main_points": analysis.main_points,
                    "summary": analysis.summary,
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

    def process_and_save_session(self, session_id: str) -> str:
        """Process all articles in session and save results"""
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

            processed_articles = []
            failed_articles = []
            
            # Process each article
            for article in articles:
                try:
                    processed = self.process_article(
                        content=article['content'],
                        title=article['title'],
                        url=article['url'],
                        metadata=article.get('metadata', {})
                    )
                    processed_articles.append(processed)
                    
                    # Update progress
                    self.db.update_session(
                        session_id=session_id,
                        update_data={
                            'processed_count': len(processed_articles),
                            'total_count': len(articles)
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to process article {article['title']}: {e}")
                    failed_articles.append({
                        'title': article['title'],
                        'error': str(e)
                    })

            # Create final summary with all processed article data
            summary = {
                'topic': self.db.get_session(session_id)['query'],
                'articles': processed_articles,
                'created_at': datetime.utcnow()
            }

            # Save final results
            self.db.update_session(
                session_id=session_id,
                update_data={
                    'processed_data': summary,
                    'status': 'completed',
                    'processed_at': datetime.utcnow(),
                    'failed_articles': failed_articles,
                    'success_rate': len(processed_articles) / len(articles)
                }
            )
            logger.info(f"Processed articles saved in the database for session {session_id}")

            logger.info(f"Successfully processed session {session_id}")
            logger.info(f"Processed {len(processed_articles)} articles, {len(failed_articles)} failed")
            
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
        all_points = []
        
        # Sort articles by publication date for temporal context
        sorted_articles = sorted(articles, 
                               key=lambda x: x.get('metadata', {}).get('published_date', ''),
                               reverse=True)
        
        for article in sorted_articles:
            points = article['summary']['main_points']
            metadata = article.get('metadata', {})
            pub_date = metadata.get('published_date', '')
            
            # Add temporal context to significant findings if date exists
            if pub_date:
                try:
                    # Convert to datetime for comparison
                    pub_dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
                    # Add temporal context to first point from each article
                    if points:
                        points[0] = f"As of {pub_dt.strftime('%B %d, %Y')}: {points[0]}"
                except (ValueError, TypeError):
                    pass
                    
            all_points.extend(points)
        
        # Remove duplicates while preserving order
        unique_points = list(dict.fromkeys(all_points))
        return unique_points[:10]  # Return top 10 findings
        
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
                    
                    Key findings from {len(articles)} articles:
                    {chr(10).join([f"- {finding}" for finding in content['key_findings']])}
                    
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