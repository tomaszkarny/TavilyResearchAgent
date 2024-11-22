# src/research/data_processor.py
"""
Data processor for extracting and preparing research data for LLM consumption
"""
from typing import List, Dict, Optional
import logging
from datetime import datetime
import json
from .database.db import ResearchDatabase
from .exceptions import ProcessingError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchDataProcessor:
    """Processes research data for LLM consumption"""
    
    def __init__(self):
        """Initialize processor"""
        self.db = ResearchDatabase()
    
    def get_session_data(self, session_id: str) -> Dict:
        """
        Get full session data including all articles
        
        Args:
            session_id: Database session ID
            
        Returns:
            Dict containing session and article data
        """
        session = self.db.get_session(session_id)
        if not session:
            raise ProcessingError(f"Session {session_id} not found")
            
        articles = self.db.get_articles(session_id)
        return {
            'session': session,
            'articles': articles
        }
    
    def prepare_llm_context(self, session_id: str, max_tokens: int = 4000) -> str:
        """
        Prepare research data as context for LLM
        
        Args:
            session_id: Database session ID
            max_tokens: Maximum tokens for context window
            
        Returns:
            Formatted context string for LLM
        """
        try:
            # Get data
            data = self.get_session_data(session_id)
            query = data['session'].get('query', '')
            articles = data['articles']
            
            # Create structured context
            context = [
                f"Research Topic: {query}\n",
                f"Number of Sources: {len(articles)}\n",
                "Key Information from Sources:\n\n"
            ]
            
            # Process each article
            for idx, article in enumerate(articles, 1):
                # Extract key metadata
                title = article.get('title', 'Untitled')
                url = article.get('url', 'No URL')
                score = article.get('score', 0)
                
                # Format article section
                article_section = [
                    f"Source {idx}:",
                    f"Title: {title}",
                    f"URL: {url}",
                    f"Relevance Score: {score:.2f}",
                    "Content Summary:",
                    f"{self._extract_key_points(article.get('content', ''))}\n"
                ]
                
                context.extend(article_section)
            
            # Add processing instructions
            context.extend([
                "\nInstructions for Content Generation:",
                "1. Use the above information to create comprehensive content",
                "2. Maintain factual accuracy and cite sources appropriately",
                "3. Follow proper blog post structure",
                "4. Include relevant examples and explanations",
                f"\nOriginal Query: {query}"
            ])
            
            return "\n".join(context)
            
        except Exception as e:
            logger.error(f"Error preparing LLM context: {str(e)}")
            raise ProcessingError(f"Failed to prepare context: {str(e)}")
    
    def _extract_key_points(self, content: str, max_points: int = 5) -> str:
        """
        Extract key points from content
        
        Args:
            content: Article content
            max_points: Maximum number of key points
            
        Returns:
            Formatted key points string
        """
        if not content:
            return "No content available"
            
        # Simple extractive summarization
        sentences = content.split('.')
        key_sentences = []
        
        for sentence in sentences[:max_points]:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Ignore very short sentences
                key_sentences.append(f"• {sentence}")
        
        return "\n".join(key_sentences)
    
    def save_processed_data(self, 
                          session_id: str,
                          processed_content: str,
                          metadata: Optional[Dict] = None) -> str:
        """
        Save processed data back to database
        
        Args:
            session_id: Database session ID
            processed_content: Processed content
            metadata: Additional metadata
            
        Returns:
            ID of saved processed content
        """
        try:
            # Update session with processed content
            processed_data = {
                'session_id': session_id,
                'content': processed_content,
                'metadata': metadata or {},
                'processed_at': datetime.utcnow()
            }
            
            result = self.db.articles.insert_one(processed_data)
            logger.info(f"Saved processed content with ID: {result.inserted_id}")
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving processed data: {str(e)}")
            raise ProcessingError(f"Failed to save processed data: {str(e)}")
    
    def export_for_blog(self, session_id: str, format: str = 'json') -> str:
        """
        Export processed data in blog-friendly format
        
        Args:
            session_id: Database session ID
            format: Export format ('json' or 'markdown')
            
        Returns:
            Formatted content string
        """
        try:
            data = self.get_session_data(session_id)
            
            if format == 'json':
                blog_data = {
                    'topic': data['session'].get('query', ''),
                    'sources': [
                        {
                            'title': article.get('title'),
                            'url': article.get('url'),
                            'key_points': self._extract_key_points(article.get('content', ''))
                        }
                        for article in data['articles']
                    ],
                    'metadata': {
                        'created_at': datetime.utcnow().isoformat(),
                        'source_count': len(data['articles'])
                    }
                }
                return json.dumps(blog_data, indent=2)
                
            elif format == 'markdown':
                md_lines = [
                    f"# Research: {data['session'].get('query', '')}\n",
                    "## Sources\n"
                ]
                
                for article in data['articles']:
                    md_lines.extend([
                        f"### {article.get('title', 'Untitled')}\n",
                        f"Source: {article.get('url', 'No URL')}\n",
                        "Key Points:",
                        f"{self._extract_key_points(article.get('content', ''))}\n"
                    ])
                
                return "\n".join(md_lines)
            
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            raise ProcessingError(f"Failed to export data: {str(e)}")

def test_processor():
    """Test the data processor"""
    processor = ResearchDataProcessor()
    
    try:
        # Get session ID from user
        session_id = input("Enter session ID to process: ")
        
        # Prepare context
        context = processor.prepare_llm_context(session_id)
        print("\nPrepared LLM Context:")
        print("-" * 60)
        print(context)
        
        # Export in different formats
        print("\nJSON Export:")
        print(processor.export_for_blog(session_id, 'json'))
        
        print("\nMarkdown Export:")
        print(processor.export_for_blog(session_id, 'markdown'))
        
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_processor()