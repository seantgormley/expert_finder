"""
test_proxycurl.py
Simple test script for the Proxycurl API integration.
"""

import os
import pandas as pd
from expert_finder_proxycurl import find_and_rank, check_api_keys

def test_api_key():
    """Test that the API key is properly set up."""
    try:
        check_api_keys()
        print("✅ API key check passed")
        return True
    except ValueError as e:
        print(f"❌ API key check failed: {str(e)}")
        return False

def test_find_and_rank_with_fallback():
    """Test the find_and_rank function with fallback data."""
    print("Testing find_and_rank with fallback data...")
    
    os.environ["EXPERT_FINDER_TEST_MODE"] = "1"
    
    try:
        result = find_and_rank("I'm trying to get smart on Google", top_n=5)
        
        if result.empty:
            print("❌ No results found")
            return False
        
        print("\nResults:")
        print(result)
        
        expected_columns = ["name", "title", "company", "email", "score"]
        missing_columns = [col for col in expected_columns if col not in result.columns]
        
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            return False
        
        if "note" not in result.columns:
            print("❌ Missing 'note' column which should indicate sample data")
            return False
            
        if not all(result["note"].str.contains("Sample data")):
            print("❌ Note column doesn't indicate sample data")
            return False
        
        print("\n✅ find_and_rank test with fallback data completed successfully")
        return True
    finally:
        os.environ.pop("EXPERT_FINDER_TEST_MODE", None)

if __name__ == "__main__":
    print("Testing Proxycurl API integration...")
    
    if test_api_key():
        test_find_and_rank_with_fallback()
    else:
        print("Skipping find_and_rank test due to API key issues")
