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
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv

# Import the extract_processed_articles function from the existing script. Adjust the import if necessary.
from extract_processed_articles import extract_processed_articles

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set default level to INFO
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True  # Ensure our logging configuration takes precedence
)

# Set our module's logger to DEBUG while keeping others at INFO or higher
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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


def generate_blog_post(prompt):
    """
    Generate a blog post using the GPT-4o-mini model.

    Returns:
        str: The generated blog post.
    """
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
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
