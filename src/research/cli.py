# src/research/cli.py
"""
Command-line interface for research tool with hybrid search support
"""
from .manager import ResearchManager
from typing import List
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

def get_domains_filter() -> tuple[List[str], List[str]]:
    """Get domain inclusion/exclusion lists from user"""
    include_domains = []
    exclude_domains = []
    
    print("\nDomain filtering options:")
    print("1. Add specific domains to include")
    print("2. Add domains to exclude")
    print("3. No domain filtering")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        domains = input("Enter domains to include (comma-separated): ")
        include_domains = [d.strip() for d in domains.split(",") if d.strip()]
    elif choice == "2":
        domains = input("Enter domains to exclude (comma-separated): ")
        exclude_domains = [d.strip() for d in domains.split(",") if d.strip()]
    
    return include_domains, exclude_domains

def get_search_parameters():
    """Get search parameters from user"""
    parameters = {}
    
    try:
        # Get result limits
        parameters['max_results'] = int(input("How many sources to gather? (5-20): ").strip())
        parameters['max_results'] = min(max(5, parameters['max_results']), 20)
    except ValueError:
        logger.info("Using default: 10 sources")
        parameters['max_results'] = 10
    
    # Get minimum score
    try:
        score = input("\nMinimum relevance score (0.0-1.0, default=0.6): ").strip()
        if score:
            parameters['min_score'] = max(0.0, min(float(score), 1.0))
    except ValueError:
        parameters['min_score'] = 0.6
    
    # Get domain filters
    include_domains, exclude_domains = get_domains_filter()
    if include_domains:
        parameters['include_domains'] = include_domains
    if exclude_domains:
        parameters['exclude_domains'] = exclude_domains
    
    return parameters

def main():
    """Main CLI function"""
    try:
        manager = ResearchManager()
        
        print("\n=== Enhanced Research Tool ===")
        query = input("\nEnter research topic: ").strip()
        
        # Get additional parameters
        print("\nWould you like to configure advanced search options? (y/n)")
        if input().strip().lower().startswith('y'):
            parameters = get_search_parameters()
        else:
            parameters = {'max_results': 10, 'min_score': 0.6}
        
        # Perform research
        session_id = manager.perform_research(query, **parameters)
        
        print("\nResearch complete!")
        print("Data is saved and ready for processing")
        print(f"Session ID: {session_id}")
        
        # Show summary
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
                        print(f"Source: {details['Source']}")
                        print("-" * 60)
        
    except KeyboardInterrupt:
        print("\nResearch cancelled by user")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()