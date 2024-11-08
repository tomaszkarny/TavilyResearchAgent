# src/research/cli.py
"""
Command-line interface for research tool with improved metadata handling
"""
from .manager import ResearchManager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Simplified format for better readability
)
logger = logging.getLogger(__name__)

def main():
    """Main CLI function"""
    try:
        manager = ResearchManager()
        
        print("\n=== Research Tool ===")
        query = input("\nEnter research topic for blog post: ").strip()
        
        try:
            max_results = int(input("How many sources to gather? (5-20): ").strip())
            max_results = min(max(5, max_results), 20)
        except ValueError:
            logger.info("Using default: 10 sources")
            max_results = 10
        
        # Perform research
        session_id = manager.perform_research(query, max_results)
        
        print("\nResearch complete!")
        print("Data is saved and ready for processing by Claude 3.5 Sonnet")
        print(f"Use session ID {session_id} when generating the blog post")
        
        # Show summary of results
        print("\nWould you like to see a summary of the gathered sources? (y/n)")
        if input().strip().lower().startswith('y'):
            from .verify_results import ResearchVerifier
            verifier = ResearchVerifier()
            results = verifier.verify_session(session_id)
            
            if results:
                print("\nGathered Sources:")
                print("-" * 60)
                
                for article in results["Articles"]:
                    for _, details in article.items():
                        print(f"\nTitle: {details['Title']}")
                        print(f"URL: {details['URL']}")
                        print(f"Relevance Score: {details['Relevance Score']:.2f}")
                        print("-" * 60)
        
    except KeyboardInterrupt:
        print("\nResearch cancelled by user")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()