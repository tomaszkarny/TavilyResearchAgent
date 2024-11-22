from typing import List, Dict, Optional
import logging
from datetime import datetime
from .data_processor import ResearchDataProcessor
from .exceptions import ProcessingError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlogPostGenerator:
    """Generates blog posts from research data"""
    
    def __init__(self):
        """Initialize generator"""
        self.processor = ResearchDataProcessor()
    
    def generate_blog_prompt(self, session_id: str) -> str:
        """
        Generate prompt for LLM blog generation
        
        Args:
            session_id: Database session ID
            
        Returns:
            Formatted prompt string
        """
        try:
            # Get processed context
            context = self.processor.prepare_llm_context(session_id)
            
            # Create prompt
            prompt = f"""
Based on the following research data, create a comprehensive blog post:

{context}

Requirements for the blog post:
1. Start with an engaging introduction
2. Include key insights from the provided sources
3. Support claims with data and examples from the research
4. Break down complex topics into understandable sections
5. Maintain a professional yet accessible tone
6. Include a brief conclusion with key takeaways
7. Add proper citations and references

Format the blog post with these sections:
- Title
- Introduction
- Main sections (with clear headings)
- Key takeaways
- References

Please generate the blog post now:
"""
            return prompt
        except ProcessingError as e:
            logger.error(f"Failed to prepare blog prompt: {e}")
            raise
    
    def split_content_chunks(self, content: str, max_tokens: int = 4000) -> List[str]:
        """
        Split content into manageable chunks for LLM
        
        Args:
            content: Content to split
            max_tokens: Maximum tokens per chunk
            
        Returns:
            List of content chunks
        """
        # Simple splitting by paragraphs
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para.split())  # Approximate tokens by words
            
            if current_length + para_length > max_tokens:
                # Save current chunk
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
        
        # Add last chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def format_blog_post(self, sections: List[str]) -> str:
        """
        Format blog sections into final post
        
        Args:
            sections: List of blog sections
            
        Returns:
            Formatted blog post
        """
        try:
            return "\n\n".join(sections)
        except Exception as e:
            logger.error(f"Error formatting blog post: {str(e)}")
            raise ProcessingError(f"Failed to format blog post: {str(e)}")
    
    def save_blog_post(self, session_id: str, content: str) -> str:
        """
        Save generated blog post
        
        Args:
            session_id: Database session ID
            content: Blog post content
            
        Returns:
            ID of saved blog post
        """
        metadata = {
            'type': 'blog_post',
            'generated_at': datetime.utcnow().isoformat(),
            'original_session': session_id
        }
        
        return self.processor.save_processed_data(
            session_id=session_id,
            processed_content=content,
            metadata=metadata
        )

def test_generator():
    """Test the blog generator"""
    generator = BlogPostGenerator()
    
    try:
        # Get session ID from user
        session_id = input("Enter session ID to generate blog post: ")
        
        # Generate prompt
        prompt = generator.generate_blog_prompt(session_id)
        
        print("\nGenerated Prompt:")
        print("-" * 60)
        print(prompt)
        
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_generator()
