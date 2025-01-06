# src/research/cli.py
"""
Command-line interface for research tool with hybrid search support
"""
from .manager import ResearchManager
from .data_processor import MiniProcessor
from .verify_results import ResearchVerifier, display_processed_data
from .exceptions import ProcessingError
from typing import List, Optional, Dict, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Rozszerzone predefiniowane źródła
PREDEFINED_SOURCES = {
    "1": {
        "name": "Medical Research",
        "domains": [
            "pubmed.ncbi.nlm.nih.gov",
            "ncbi.nlm.nih.gov",
            "medlineplus.gov",
            "clinicaltrials.gov",
            "bmj.com",
            "thelancet.com",
            "nejm.org",
            "jamanetwork.com"
        ]
    },
    "2": {
        "name": "Scientific Journals",
        "domains": [
            "nature.com",
            "science.org",
            "sciencedirect.com",
            "springer.com",
            "wiley.com",
            "frontiersin.org",
            "cell.com",
            "plos.org"
        ]
    },
    "3": {
        "name": "Academic Repositories",
        "domains": [
            "scholar.google.com",
            "researchgate.net",
            "academia.edu",
            "arxiv.org",
            "biorxiv.org",
            "medrxiv.org",
            "ssrn.com",
            "semanticscholar.org"
        ]
    },
    "4": {
        "name": "Health & Medical Organizations",
        "domains": [
            "who.int",
            "cdc.gov",
            "nih.gov",
            "mayoclinic.org",
            "clevelandclinic.org",
            "hopkinsmedicine.org",
            "webmd.com",
            "healthline.com"
        ]
    },
    "5": {
        "name": "News & Media",
        "domains": [
            "reuters.com",
            "bloomberg.com",
            "nytimes.com",
            "bbc.com",
            "theguardian.com",
            "scientificamerican.com",
            "newscientist.com",
            "sciencedaily.com"
        ]
    },
    "6": {
        "name": "University Research",
        "domains": [
            "harvard.edu",
            "stanford.edu",
            "mit.edu",
            "ox.ac.uk",
            "cam.ac.uk",
            "berkeley.edu",
            "ucla.edu",
            "columbia.edu"
        ]
    },
    "7": {
        "name": "Custom Domains",
        "description": "Add your own domains"
    },
    "8": {
        "name": "Exclude Domains",
        "description": "Specify domains to exclude"
    },
    "9": {
        "name": "No Filtering",
        "description": "Search all sources"
    }
}

def display_processing_stats(session_data: Optional[Dict]) -> None:
    """
    Display processing statistics
    
    Args:
        session_data: Optional dictionary containing session data
    """
    if not session_data:
        print("\nNo processing statistics available")
        return
    
    print("\nProcessing Statistics:")
    print(f"Total Articles: {session_data.get('total_count', 0)}")
    print(f"Successfully Processed: {session_data.get('processed_count', 0)}")
    if 'success_rate' in session_data:
        print(f"Success Rate: {session_data['success_rate']:.2%}")
    
    if failed_articles := session_data.get('failed_articles', []):
        print("\nFailed Articles:")
        for article in failed_articles:
            print(f"- {article['title']}: {article['error']}")

def get_domains_filter() -> Tuple[List[str], List[str]]:
    """
    Get domain inclusion/exclusion lists from user
    
    Returns:
        Tuple containing lists of included and excluded domains
    """
    include_domains = []
    exclude_domains = []
    
    print("\nSelect source categories (separate by comma, e.g., 1,2,4):")
    for key, source in PREDEFINED_SOURCES.items():
        print(f"{key}. {source['name']}")
        if source.get('description'):
            print(f"   {source['description']}")
    
    choices = input("\nEnter your choices (1-9): ").strip().split(',')
    
    # Process predefined sources
    for choice in choices:
        choice = choice.strip()
        if choice in PREDEFINED_SOURCES and choice not in ["7", "8", "9"]:
            source = PREDEFINED_SOURCES[choice]
            print(f"\nAdding {source['name']} domains:")
            for domain in source['domains']:
                print(f"- {domain}")
            include_domains.extend(source['domains'])
    
    # Ask for additional custom domains
    print("\nWould you like to add custom domains? (y/n)")
    if input().strip().lower().startswith('y'):
        domains = input("Enter additional domains (comma-separated): ")
        custom_domains = [d.strip() for d in domains.split(",") if d.strip()]
        if custom_domains:
            print("\nAdding custom domains:")
            for domain in custom_domains:
                print(f"- {domain}")
            include_domains.extend(custom_domains)
    
    # Ask for domains to exclude
    print("\nWould you like to exclude any domains? (y/n)")
    if input().strip().lower().startswith('y'):
        domains = input("Enter domains to exclude (comma-separated): ")
        exclude_domains = [d.strip() for d in domains.split(",") if d.strip()]
        if exclude_domains:
            print("\nExcluding domains:")
            for domain in exclude_domains:
                print(f"- {domain}")
    
    # Remove duplicates while preserving order
    include_domains = list(dict.fromkeys(include_domains))
    
    return include_domains, exclude_domains

def get_date_filter():
    """Get date/time range filter from user"""
    print("\nWould you like to filter articles by date? (y/n)")
    if input().strip().lower().startswith('y'):
        print("\nSelect time range:")
        print("1. Last hour")
        print("2. Last day")
        print("3. Last week")
        print("4. Last month")
        print("5. Last year")
        print("6. Custom date range")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        # Predefined time ranges
        if choice in ["1", "2", "3", "4", "5"]:
            time_ranges = {
                "1": "last_hour",
                "2": "last_day",
                "3": "last_week",
                "4": "last_month",
                "5": "last_year"
            }
            return {"time_range": time_ranges[choice]}
            
        # Custom date range
        elif choice == "6":
            try:
                print("\nEnter date range (YYYY-MM-DD):")
                start_date = input("From date: ").strip()
                end_date = input("To date: ").strip()
                
                # Convert to datetime objects for validation
                from datetime import datetime
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                
                return {
                    'start_date': start.isoformat(),
                    'end_date': end.isoformat()
                }
            except ValueError:
                print("\nInvalid date format. Using no date filter.")
                return None
    return None

def get_search_parameters():
    """Get search parameters from user"""
    params = {}
    
    # Number of sources
    max_results = input("How many sources to gather? (10-30): ").strip()
    params['max_results'] = int(max_results) if max_results.isdigit() and 10 <= int(max_results) <= 30 else 15
    
    # Minimum score
    min_score = input("\nMinimum relevance score (0.0-1.0, default=0.6): ").strip()
    params['min_score'] = float(min_score) if min_score else 0.6
    
    # Query modifiers
    print("\nSelect query modifiers (multiple choices allowed):")
    print("1. Scientific - add research-oriented terms")
    print("2. Recent - focus on latest content")
    print("3. Review - look for reviews and comparisons")
    print("4. Practical - find practical guides")
    print("Enter numbers separated by commas (e.g., 1,3) or press Enter to skip")
    
    modifiers_input = input("\nEnter your choices: ").strip()
    if modifiers_input:
        modifiers = []
        modifier_map = {
            "1": "scientific",
            "2": "recent",
            "3": "review",
            "4": "practical"
        }
        for choice in modifiers_input.split(','):
            if choice.strip() in modifier_map:
                modifiers.append(modifier_map[choice.strip()])
        if modifiers:
            params['query_modifiers'] = modifiers
    
    # Date filtering
    date_filter = get_date_filter()
    if date_filter:
        params['date_filter'] = date_filter
    
    # Domain filtering with multiple choices
    include_domains, exclude_domains = get_domains_filter()
    if include_domains:
        params['include_domains'] = include_domains
    if exclude_domains:
        params['exclude_domains'] = exclude_domains
    
    return params

def main():
    """Main CLI function"""
    try:
        manager = ResearchManager()
        
        print("\n=== Enhanced Research Tool ===")
        query = input("\nEnter research topic: ").strip()
        
        # Get search parameters
        print("\nWould you like to configure advanced search options? (y/n)")
        if input().strip().lower().startswith('y'):
            parameters = get_search_parameters()
        else:
            parameters = {
        'max_results': 10, 
        'min_score': 0.6,
        'topic': 'news',
        'days': 7  # Default to last 7 days
            }
            logger.info("Using default parameters with news configuration:")
            logger.info(f"Topic: {parameters['topic']}")
            logger.info(f"Days: {parameters['days']}")
            logger.info(f"Max Results: {parameters['max_results']}")
            logger.info(f"Min Score: {parameters['min_score']}")
        
        # 1. Perform research
        logger.info(f"\nInitiating research for: {query}")
        session_id = manager.perform_research(query, **parameters)
        
        print("\nResearch complete!")
        print("Data is saved and ready for processing")
        print(f"Session ID: {session_id}")
        
        # 2. Show gathered sources
        print("\nWould you like to see a summary of the gathered sources? (y/n)")
        if input().strip().lower().startswith('y'):
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
                        if details.get('Published'):
                            print(f"Published: {details['Published']}")
                        print("-" * 60)
        
        # 3. Process articles with GPT-4o-mini
        print("\nWould you like to process the articles with GPT-4o-mini? (y/n)")
        if input().strip().lower().startswith('y'):
            processor = MiniProcessor()
            try:
                print("\nProcessing articles...")
                processed_session = processor.process_and_save_session(session_id)
                print("\nArticles processed successfully!")
                
                # Get and display processing statistics
                if session_data := processor.db.get_session(processed_session):
                    if session_data.get('processed_data'):
                        display_processing_stats(session_data)
                    
                    # 4. Ask about blog generation
                    print("\nWould you like to generate a blog post from the processed data? (y/n)")
                    if input().strip().lower().startswith('y'):
                        print("\nGenerating blog post...")
                        blog_content = processor.generate_blog_summary(processed_session)
                        
                        print("\nBlog Post Generated:")
                        print(f"\nTitle: {blog_content['title']}")
                        print("\nIntroduction:")
                        print(blog_content['introduction'][:200] + "...")
                        
                        print("\nKey Sections:")
                        for section in blog_content['key_sections']:
                            print(f"\n- {section['heading']}")
                            print(f"  {section['content'][:100]}...")
                        
                        print("\nConclusion:")
                        print(blog_content['conclusion'][:200] + "...")
                        
                        print("\nBlog post has been generated and saved to the database.")
                
                    # Po przetworzeniu artykułów
                    print("\nWould you like to see the processed data? (y/n)")
                    if input().strip().lower().startswith('y'):
                        display_processed_data(processed_session)
                
            except ProcessingError as e:
                print(f"\nError during processing: {e}")
                return
                
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main()