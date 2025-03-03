#!/usr/bin/env python
"""
Script to generate a blog post from processed articles using GPT-4o-mini.
Usage: python generate_blog_post_workflow.py <session_id>

This script extracts processed article data from MongoDB for a given research session,
aggregates the key information into a context string, builds a detailed prompt, and sends it
to the GPT-4o-mini model to generate a comprehensive blog post. The generated blog post is
then printed to the console.
"""

import sys
import logging
import os
# Import the OpenAI class dynamically in the generate_blog_post function
# to prevent issues with external patches or modifications
# from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
from typing import List
import tiktoken

# Import the extract_processed_articles function from the existing script.
import sys
import os

# Add the project root to Python path to find modules
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# Now import the extract_processed_articles function
from extract_processed_articles import extract_processed_articles

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set default level to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True  # Ensure our logging configuration takes precedence
)

# Set our module's logger to DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Explicitly log that debug is enabled
logger.debug("DEBUG logging is enabled")

# Reduce noise from other loggers
logging.getLogger('urllib3').setLevel(logging.INFO)
logging.getLogger('openai').setLevel(logging.INFO)
logging.getLogger('mongodb').setLevel(logging.INFO)


def build_context(articles):
    """
    Build a context string from a list of processed articles.

    For each article, include:
      - Title
      - Summary text
      - Main Points
      - Key Statistics
      - Practical Tips
      - Expert Opinions
    """
    context_parts = []
    for idx, article in enumerate(articles, start=1):
        title = article.get("title", "No Title")
        summary_data = article.get("summary", {})
        summary_text = summary_data.get("summary", "")
        main_points = summary_data.get("main_points", [])
        key_stats = summary_data.get("key_statistics", [])
        practical_tips = summary_data.get("practical_tips", [])
        expert_opinions = summary_data.get("expert_opinions", [])

        part = f"Article {idx}: {title}\n"
        part += f"Summary: {summary_text}\n"
        if main_points:
            part += "Main Points:\n" + "\n".join(f"- {point}" for point in main_points) + "\n"
        if key_stats:
            part += "Key Statistics:\n" + "\n".join(f"- {stat}" for stat in key_stats) + "\n"
        if practical_tips:
            part += "Practical Tips:\n" + "\n".join(f"- {tip}" for tip in practical_tips) + "\n"
        if expert_opinions:
            part += "Expert Opinions:\n" + "\n".join(
                f"- {opinion.get('expert', 'Unknown')}: {opinion.get('quote', '')}" for opinion in expert_opinions
            ) + "\n"

        context_parts.append(part)
    return "\n\n".join(context_parts)


def build_prompt(context, research_topic):
    """
    Construct the prompt for GPT-4o-mini to generate a blog post.

    The prompt instructs the model to:
      - Write an engaging introduction
      - Present clear sections that highlight key insights from the research data
      - Support claims with data and examples from the provided articles
      - Conclude with key takeaways and final thoughts

    Args:
        context (str): Aggregated research data from processed articles.
        research_topic (str): The research topic or title to guide the blog post.

    Returns:
        str: The full prompt to be sent to the LLM.
    """
    prompt = f"""\
You are a professional blog writer. Based on the following research data, generate a comprehensive blog post on the topic: \"{research_topic}\".

The research data consists of multiple articles, each containing a title, a summary, main points, key statistics, practical tips, and expert opinions. Your blog post should:
- Start with an engaging introduction that sets the context.
- Include clear sections that discuss the key insights derived from the research.
- Use data and examples from the provided research to support your points.
- Conclude with key takeaways and a final thought.

Here is the research data:
{context}

Please generate the blog post now.\n"""
    return prompt


def split_content_chunks(content: str, max_tokens: int = 4000) -> List[str]:
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


def generate_blog_post(prompt):
    """
    Generate a blog post using the GPT-4o-mini model.
    
    If the prompt is too large, it will be split into chunks and processed
    separately, then combined.

    Returns:
        str: The generated blog post.
    """
    try:
        # Log a clear message before chunking
        print("\n=== TESTING CHUNKING FUNCTIONALITY ===")
        
        # Check if the prompt needs to be chunked
        chunks = split_content_chunks(prompt, max_tokens=4000)  # Adjust max_tokens as needed
        
        # Log token count for debugging using print for visibility
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        token_count = len(encoding.encode(prompt))
        print(f"Original prompt token count: {token_count}")
        print(f"Chunking result: {len(chunks)} chunks created")
        print(f"Chunk sizes: {[len(encoding.encode(chunk)) for chunk in chunks]}")
        print("=== END OF CHUNKING TEST ===\n")
        
        # Also log using logger
        logger.info(f"Original prompt token count: {token_count}")
        logger.info(f"Chunking result: {len(chunks)} chunks created")
        
        # Initialization of the OpenAI client - without parameters that may cause problems
        try:
            # Remove OpenAI import at the module level and import it locally
            # Local import will help avoid any external modifications
            from openai import OpenAI
            # Create client only with API key, without any additional parameters
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            # Check if the client works correctly
            if not hasattr(client, 'chat'):
                raise AttributeError("OpenAI client does not have 'chat' attribute")
            
            logger.info("OpenAI client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
        
        if len(chunks) > 1:
            logger.info(f"Prompt split into {len(chunks)} chunks. Processing separately.")
            blog_parts = []
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}...")
                response = client.chat.completions.create(
                    model="gpt-4o-mini-2024-07-18",
                    messages=[
                        {"role": "system", "content": "You are a professional blog writer."},
                        {"role": "user", "content": chunk}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
                blog_parts.append(response.choices[0].message.content.strip())
            
            # Combine parts into final blog post
            blog_post = "\n\n".join(blog_parts)
            return blog_post
        else:
            # Process single chunk
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "You are a professional blog writer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            blog_post = response.choices[0].message.content.strip()
            return blog_post
    except Exception as e:
        logger.error(f"Error generating blog post: {e}")
        raise


def main():
    try:
        load_dotenv()

        if not os.getenv('OPENAI_API_KEY'):
            logger.error("OPENAI_API_KEY environment variable is not set")
            sys.exit(1)

        if len(sys.argv) != 2:
            print("Usage: python generate_blog_post_workflow.py <session_id>")
            sys.exit(1)

        session_id = sys.argv[1]
        logger.info(f"Extracting processed articles for session {session_id}...")

        articles = extract_processed_articles(session_id)
        if not articles:
            logger.error("No processed articles found. Cannot generate blog post.")
            sys.exit(1)

        # Build context from the extracted articles
        context = build_context(articles)
        logger.info("Context built successfully.")

        # Derive a research topic (for example, using the title of the first article)
        research_topic = articles[0].get("title", "Research Findings")

        # Build the prompt
        prompt = build_prompt(context, research_topic)
        logger.info("Prompt built successfully. Generating blog post...")
        
        # Log the complete prompt for debugging
        logger.debug(
            f"\nComplete Prompt for Research Topic: {research_topic}\n" +
            "="*80 + "\n" +
            prompt +
            "\n" + "="*80
        )

        # Generate the blog post
        blog_post = generate_blog_post(prompt)
        
        print("\nGenerated Blog Post:\n")
        print(blog_post)

        # Save the blog post to a Markdown file in the project root
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), f"blog_post_{timestamp}.md")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(blog_post)
            logger.info(f"Blog post successfully saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving blog post to file: {e}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
