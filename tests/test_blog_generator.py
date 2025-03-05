"""
Test script for the blog post generation workflow with focus on token-based content splitting.
This tests the content chunking functionality that was migrated from blog_generator.py to generate_blog_post_workflow.py
"""
import pytest
import tiktoken
import sys
import os
# Import functions directly from generate_blog_post_workflow
from src.research.generate_blog_post_workflow import split_content_chunks

def test_split_content_chunks():
    """Test the split_content_chunks function with token-based splitting"""
    # Create a test content that's long enough to be split
    # Repeating text to create multiple chunks
    test_content = "This is a test paragraph with multiple sentences. " * 500
    
    # Define max tokens per chunk
    max_tokens = 1000
    
    # Test the function directly
    chunks = split_content_chunks(test_content, max_tokens)
    
    # Verify we got multiple chunks
    assert len(chunks) > 1, "Content should be split into multiple chunks"
    
    # Verify each chunk is within token limit
    encoding = tiktoken.encoding_for_model("gpt-4o-mini")
    for i, chunk in enumerate(chunks):
        tokens = encoding.encode(chunk)
        token_count = len(tokens)
        assert token_count <= max_tokens, f"Chunk {i} has {token_count} tokens, exceeding limit of {max_tokens}"
    
    # Verify that all content is preserved (approximately)
    # We check length instead of exact content due to token encoding/decoding
    original_token_count = len(encoding.encode(test_content))
    total_chunk_token_count = sum(len(encoding.encode(chunk)) for chunk in chunks)
    
    # Allow small differences due to token boundaries
    assert abs(original_token_count - total_chunk_token_count) < 10, \
        f"Token count difference too large: original={original_token_count}, chunks total={total_chunk_token_count}"

def test_edge_cases():
    """Test edge cases for split_content_chunks"""
    # Empty content
    assert split_content_chunks("") == [""], "Empty content should return a list with an empty string"
    
    # Content smaller than max_tokens
    short_content = "Short text that won't be split."
    chunks = split_content_chunks(short_content, 100)
    assert len(chunks) == 1, "Short content should not be split"
    assert chunks[0] == short_content, "Content should be preserved exactly when not split"
    
    # Very small max_tokens (unrealistic but should handle gracefully)
    tiny_chunks = split_content_chunks("This will be split into very tiny chunks.", 5)
    assert len(tiny_chunks) > 1, "Content should be split with very small token limit"
    
if __name__ == "__main__":
    # Updated file name to match current file
    pytest.main(["-v", __file__])
