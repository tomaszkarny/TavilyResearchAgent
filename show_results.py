from src.research.verify_results import display_processed_data
import sys

def main():
    # Use command line argument if provided, otherwise use default session ID
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
    else:
        # Twoje ostatnie ID sesji
        session_id = "6740fab9b1aa5a95b5679679"
    
    try:
        print(f"\nFetching results for session: {session_id}")
        results = display_processed_data(session_id)
        
        if not results:
            print("\nNo processed data found for this session.")
            print("Make sure you have:")
            print("1. Correct session ID")
            print("2. Processed the articles with GPT-4o-mini")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nPlease check:")
        print("1. MongoDB connection")
        print("2. Session ID format")
        print("3. Database permissions")

if __name__ == "__main__":
    main() 