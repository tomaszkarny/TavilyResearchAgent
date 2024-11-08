# src/research/complete_search.py
"""
Enhanced interactive search script with advanced filtering and database integration.
Extends the basic search functionality with additional filters and database integration.
"""
from .tavily_client import ResearchClient, SearchFilters, SortOrder
from .database.db import ResearchDatabase
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedSearchOptions:
    """Extended container for search options"""
    def __init__(self):
        self.query: str = ""
        self.max_results: int = 5
        self.max_age_days: Optional[int] = None
        self.min_score: float = 0.5
        self.domains: List[str] = []
        self.exclude_domains: List[str] = []
        self.sort_by: SortOrder = SortOrder.RELEVANCE
        self.group_similar: bool = False
        # New options
        self.content_types: List[str] = []  # e.g., ['article', 'blog', 'research', 'news']
        self.language: Optional[str] = None
        self.author: Optional[str] = None
        self.keywords: List[str] = []
        self.exclude_keywords: List[str] = []
        self.save_to_db: bool = True
        self.min_content_length: Optional[int] = None
        self.require_author: bool = False
        self.require_date: bool = False

def get_time_range() -> Optional[int]:
    """Get time range from user"""
    print("\nSelect time range for results:")
    print("1. Last 24 hours")
    print("2. Last week")
    print("3. Last month")
    print("4. Last 3 months")
    print("5. Last year")
    print("6. Custom range")
    print("7. No time limit")
    
    time_ranges = {
        "1": 1,      # 24 hours
        "2": 7,      # Week
        "3": 30,     # Month
        "4": 90,     # 3 months
        "5": 365,    # Year
    }
    
    choice = input("\nEnter your choice (1-7): ").strip()
    
    if choice in time_ranges:
        return time_ranges[choice]
    elif choice == "6":
        try:
            days = int(input("Enter maximum age in days: "))
            return max(1, days)
        except ValueError:
            print("Invalid input, using default of 30 days")
            return 30
    return None

def get_domain_filters():
    """Get domain inclusion/exclusion lists from user"""
    domains = []
    exclude_domains = []
    
    print("\nDomain filtering options:")
    print("1. Add domains to include (e.g., 'arxiv.org, github.com')")
    print("2. Add domains to exclude")
    print("3. No domain filtering")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        domains_input = input("Enter domains to include (comma-separated): ")
        domains = [d.strip() for d in domains_input.split(",") if d.strip()]
    elif choice == "2":
        domains_input = input("Enter domains to exclude (comma-separated): ")
        exclude_domains = [d.strip() for d in domains_input.split(",") if d.strip()]
    
    return domains, exclude_domains

def get_content_types() -> List[str]:
    """Get desired content types from user"""
    print("\nSelect content types (comma-separated):")
    print("Available types: article, blog, research, news, academic, documentation")
    types_input = input("Enter types or press Enter for all: ").strip()
    if types_input:
        return [t.strip() for t in types_input.split(",") if t.strip()]
    return []

def get_keywords_filter() -> tuple[List[str], List[str]]:
    """Get keyword inclusion/exclusion lists"""
    include_keywords = []
    exclude_keywords = []
    
    print("\nKeyword filtering options:")
    print("1. Add required keywords")
    print("2. Add excluded keywords")
    print("3. No keyword filtering")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        keywords = input("Enter required keywords (comma-separated): ")
        include_keywords = [k.strip() for k in keywords.split(",") if k.strip()]
    elif choice == "2":
        keywords = input("Enter excluded keywords (comma-separated): ")
        exclude_keywords = [k.strip() for k in keywords.split(",") if k.strip()]
    
    return include_keywords, exclude_keywords

def get_sort_order() -> SortOrder:
    """Get sorting preference from user"""
    print("\nSelect sorting order:")
    print("1. By relevance (default)")
    print("2. By date (newest first)")
    print("3. By combined score (relevance + freshness)")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "2":
        return SortOrder.DATE
    elif choice == "3":
        return SortOrder.SCORE
    return SortOrder.RELEVANCE

def get_enhanced_search_options() -> EnhancedSearchOptions:
    """Get all enhanced search options from user"""
    options = EnhancedSearchOptions()
    
    # Basic options
    print("\n=== Search Configuration ===")
    options.query = input("\nEnter your search query: ").strip()
    
    try:
        results = input("\nHow many results? (1-20, default=5): ").strip()
        if results:
            options.max_results = min(max(1, int(results)), 20)
    except ValueError:
        pass
    
    print("\nConfigure advanced options? (y/n)")
    if input().lower().startswith('y'):
        # Time range
        options.max_age_days = get_time_range()
        
        # Quality filters
        try:
            score = input("\nMinimum quality score (0.0-1.0, default=0.5): ")
            if score:
                options.min_score = min(max(0.0, float(score)), 1.0)
                
            min_length = input("Minimum content length in characters (Enter to skip): ")
            if min_length:
                options.min_content_length = max(0, int(min_length))
        except ValueError:
            pass
        
        # Content type filters
        options.content_types = get_content_types()
        
        # Domain filters
        options.domains, options.exclude_domains = get_domain_filters()
        
        # Keyword filters
        options.keywords, options.exclude_keywords = get_keywords_filter()
        
        # Language filter
        lang = input("\nFilter by language (e.g., en, es, fr - Enter to skip): ").strip()
        if lang:
            options.language = lang
        
        # Author filter
        author = input("\nFilter by author (Enter to skip): ").strip()
        if author:
            options.author = author
        
        # Metadata requirements
        print("\nRequire author information? (y/n)")
        options.require_author = input().lower().startswith('y')
        
        print("Require publication date? (y/n)")
        options.require_date = input().lower().startswith('y')
        
        # Result organization
        options.sort_by = get_sort_order()
        
        print("\nGroup similar results? (y/n)")
        options.group_similar = input().lower().startswith('y')
        
        # Database storage
        print("\nSave results to database? (y/n)")
        options.save_to_db = input().lower().startswith('y')
    
    return options

def display_result(idx: int, result: dict):
    """Display a single search result"""
    print(f"\nResult {idx}:")
    print("=" * 60)
    
    metadata = result.get('metadata', {})
    print(f"Score: {result.get('score', 0):.2f}")
    print(f"Title: {metadata.get('title', 'N/A')}")
    print(f"URL: {metadata.get('url', 'N/A')}")
    
    if author := metadata.get('author'):
        print(f"Author: {author}")
    
    if retrieved_at := metadata.get('retrieved_at'):
        age = datetime.utcnow() - retrieved_at
        print(f"Age: {age.days} days old")
        print(f"Retrieved: {retrieved_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if published_date := metadata.get('published_date'):
        print(f"Published: {published_date}")
    
    if language := metadata.get('language'):
        print(f"Language: {language}")
    
    print("\nContent Preview:")
    print("-" * 60)
    content = result.get('content', '')
    content_length = len(content)
    print(f"{content[:300]}...")
    print(f"\nContent length: {content_length} characters")
    print("-" * 60)

def perform_enhanced_search():
    """Perform search with enhanced options and database integration"""
    client = ResearchClient(mock_mode=False)
    db = ResearchDatabase()
    
    # Get search options
    options = get_enhanced_search_options()
    
    # Create search filters
    filters = SearchFilters(
        min_score=options.min_score,
        max_age_days=options.max_age_days,
        domains=options.domains if options.domains else None,
        exclude_domains=options.exclude_domains if options.exclude_domains else None,
        content_type=options.content_types if options.content_types else None
    )
    
    # Display configuration
    print("\n=== Search Configuration Summary ===")
    print(f"Query: {options.query}")
    print(f"Max results: {options.max_results}")
    if options.max_age_days:
        print(f"Time limit: {options.max_age_days} days")
    print(f"Minimum score: {options.min_score}")
    if options.min_content_length:
        print(f"Minimum content length: {options.min_content_length} characters")
    if options.content_types:
        print(f"Content types: {', '.join(options.content_types)}")
    if options.domains:
        print(f"Including domains: {', '.join(options.domains)}")
    if options.exclude_domains:
        print(f"Excluding domains: {', '.join(options.exclude_domains)}")
    if options.keywords:
        print(f"Required keywords: {', '.join(options.keywords)}")
    if options.exclude_keywords:
        print(f"Excluded keywords: {', '.join(options.exclude_keywords)}")
    if options.language:
        print(f"Language: {options.language}")
    if options.author:
        print(f"Author: {options.author}")
    print(f"Require author: {options.require_author}")
    print(f"Require date: {options.require_date}")
    print(f"Sort by: {options.sort_by.value}")
    print(f"Group similar: {options.group_similar}")
    print(f"Save to database: {options.save_to_db}")
    
    try:
        # Perform search
        results = client.search(
            query=options.query,
            filters=filters,
            sort_by=options.sort_by,
            max_results=options.max_results,
            group_similar=options.group_similar
        )
        
        # Post-process results
        filtered_results = []
        for result in results:
            # Apply additional filters
            content = result.get('content', '')
            metadata = result.get('metadata', {})
            
            # Content length filter
            if options.min_content_length and len(content) < options.min_content_length:
                continue
                
            # Keyword filters
            if options.keywords and not all(k.lower() in content.lower() for k in options.keywords):
                continue
            if options.exclude_keywords and any(k.lower() in content.lower() for k in options.exclude_keywords):
                continue
                
            # Language filter
            if options.language and metadata.get('language') != options.language:
                continue
                
            # Author filter
            if options.author and options.author.lower() not in metadata.get('author', '').lower():
                continue
                
            # Metadata requirements
            if options.require_author and not metadata.get('author'):
                continue
            if options.require_date and not metadata.get('published_date'):
                continue
                
            filtered_results.append(result)
        
        # Save to database if requested
        session_id = None
        if options.save_to_db and filtered_results:
            try:
                session_id = db.save_research_session(filtered_results, options.query)
                print(f"\nResults saved to database. Session ID: {session_id}")
            except Exception as e:
                logger.error(f"Error saving to database: {str(e)}")
        
        # Display results
        print(f"\nFound {len(filtered_results)} matching results:")
        for idx, result in enumerate(filtered_results, 1):
            display_result(idx, result)
            
            if idx < len(filtered_results):
                response = input("\nPress Enter for next result (or 'q' to quit): ")
                if response.lower() == 'q':
                    break
        
        return session_id
                    
    except Exception as e:
        logger.error(f"Error performing search: {str(e)}")
        raise

def main():
    """Main function with error handling"""
    print("=== Enhanced Search Tool ===")
    
    try:
        while True:
            session_id = perform_enhanced_search()
            if session_id:
                print(f"\nSession ID for database access: {session_id}")
            
            print("\nPerform another search? (y/n)")
            if not input().lower().startswith('y'):
                break
        
        print("\nThank you for using the enhanced search tool!")
        
    except KeyboardInterrupt:
        print("\nSearch cancelled by user.")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()