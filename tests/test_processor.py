"""
Test script for data processing and blog generation
"""
import logging
from src.research.data_processor import MiniProcessor
# Removed blog_generator import since we now use generate_blog_post_workflow.py

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_processing_flow():
    """Test the complete processing flow"""
    session_id = "673fb8cf7a721f3920df8e96"  # Our session ID
    
    # Initialize processor
    data_processor = MiniProcessor()
    
    try:
        # 1. Get processed research data
        logger.info("Getting research data...")
        context = data_processor.prepare_llm_context(session_id)
        
        print("\n=== Research Context ===")
        print(context)
        
        # 2. Export in different formats
        print("\n=== JSON Export ===")
        json_export = data_processor.export_for_blog(session_id, 'json')
        print(json_export)
        
        print("\n=== Markdown Export ===")
        md_export = data_processor.export_for_blog(session_id, 'markdown')
        print(md_export)
        
        # Note: Blog post generation moved to generate_blog_post_workflow.py
        print("\n=== Blog Post Workflow ===")
        print("Blog post generation is now handled by generate_blog_post_workflow.py")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    test_processing_flow()