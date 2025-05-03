"""
simple_test.py
A simple test script to verify the Proxycurl API key and endpoints.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

PROXYCURL_API_KEY = os.getenv("PROXYCURL_API_KEY") or "esbsFM1acuXDP7A6O_v_yw"
PROXYCURL_BASE_URL = "https://nubela.co/proxycurl/api"

def get_headers():
    """Get headers for Proxycurl API requests."""
    return {
        "Authorization": f"Bearer {PROXYCURL_API_KEY}"
    }

def test_company_profile():
    """Test the company profile endpoint with a known LinkedIn URL."""
    url = f"{PROXYCURL_BASE_URL}/linkedin/company"
    params = {
        "url": "https://www.linkedin.com/company/google/",
        "use_cache": "if-present"
    }
    
    print(f"Testing company profile endpoint with URL: {params['url']}")
    print(f"Full request URL: {url}")
    print(f"Headers: {get_headers()}")
    print(f"Params: {params}")
    
    try:
        resp = requests.get(
            url, 
            headers=get_headers(),
            params=params,
            timeout=15
        )
        resp.raise_for_status()
        
        data = resp.json()
        print(f"Success! Response status code: {resp.status_code}")
        print(f"Company name: {data.get('name')}")
        return True
    except requests.RequestException as e:
        print(f"Error: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return False

def test_person_profile():
    """Test the person profile endpoint with a known LinkedIn URL."""
    url = f"{PROXYCURL_BASE_URL}/linkedin/person"
    params = {
        "url": "https://www.linkedin.com/in/williamhgates/",
        "use_cache": "if-present"
    }
    
    print(f"Testing person profile endpoint with URL: {params['url']}")
    print(f"Full request URL: {url}")
    print(f"Headers: {get_headers()}")
    print(f"Params: {params}")
    
    try:
        resp = requests.get(
            url, 
            headers=get_headers(),
            params=params,
            timeout=15
        )
        resp.raise_for_status()
        
        data = resp.json()
        print(f"Success! Response status code: {resp.status_code}")
        print(f"Person name: {data.get('full_name')}")
        return True
    except requests.RequestException as e:
        print(f"Error: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return False

if __name__ == "__main__":
    print("Testing Proxycurl API...")
    print(f"API Key: {PROXYCURL_API_KEY[:5]}...{PROXYCURL_API_KEY[-5:]}")
    
    print("\n=== Testing Company Profile Endpoint ===")
    company_success = test_company_profile()
    
    print("\n=== Testing Person Profile Endpoint ===")
    person_success = test_person_profile()
    
    if company_success and person_success:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed.")
