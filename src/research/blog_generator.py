from typing import List, Dict, Optional
import logging
from datetime import datetime
import tiktoken
from .data_processor import MiniProcessor
from .exceptions import ProcessingError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlogPostGenerator:
    """Generates blog posts from research data"""
    
    def __init__(self):
        """Initialize generator"""
        self.processor = MiniProcessor()
    
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
        Split content into manageable chunks for LLM based on actual token count
        
        Args:
            content: Content to split
            max_tokens: Maximum tokens per chunk
            
        Returns:
            List of content chunks
        """
        # Handle empty content edge case
        if not content:
            return [""]
            
        # Use encoding for GPT-4o-mini model
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        tokens = encoding.encode(content)
        chunks = []
        current_chunk = []
        current_count = 0
        
        for token in tokens:
            if current_count + 1 > max_tokens:
                # Save current chunk and start a new one
                chunks.append(encoding.decode(current_chunk))
                current_chunk = [token]
                current_count = 1
            else:
                current_chunk.append(token)
                current_count += 1
        
        # Add last chunk if it exists
        if current_chunk:
            chunks.append(encoding.decode(current_chunk))
        
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
