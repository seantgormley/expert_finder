"""
expert_finder_improved.py
Improved expert-ranker for company research with better API integration.
Dependencies: requests, pandas, python-dotenv, logging
"""

import os
import re
import logging
import requests
import pandas as pd
from typing import List, Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('expert_finder')

CB_KEY = os.getenv("CB_KEY")
PDL_KEY = os.getenv("PDL_KEY")
CB_BASE = "https://api.crunchbase.com/v4"
PDL_URL = "https://api.peopledatalabs.com/v5/person/search"

TITLE_WEIGHTS = {
    "ceo": 5, "chief": 5, "founder": 5,
    "president": 4, "vp": 4, "vice": 4,
    "director": 3, "manager": 2
}


def check_api_keys():
    """Check if API keys are properly set."""
    missing_keys = []
    
    if not CB_KEY or CB_KEY == "YOUR_CRUNCHBASE_KEY":
        missing_keys.append("Crunchbase API Key (CB_KEY)")
    
    if not PDL_KEY or PDL_KEY == "YOUR_PDL_KEY":
        missing_keys.append("People Data Labs API Key (PDL_KEY)")
    
    if missing_keys:
        error_msg = f"Missing API keys: {', '.join(missing_keys)}. " \
                    f"Please set these in your .env file or as environment variables."
        logger.error(error_msg)
        raise ValueError(error_msg)


def get_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def validate_crunchbase_response(data: Any) -> bool:
    """Validate Crunchbase API response format."""
    if not isinstance(data, dict):
        return False
    if "data" not in data or not isinstance(data["data"], dict):
        return False
    if "items" not in data["data"] or not isinstance(data["data"]["items"], list):
        return False
    return True

def cb_org_search(name: str) -> Optional[Dict[str, Any]]:
    """Return first org item for a fuzzy company name with improved error handling."""
    try:
        url = f"{CB_BASE}/odm-organizations"
        session = get_session()
        
        logger.info(f"Searching Crunchbase for organization: {name}")
        resp = session.get(
            url, 
            params={"user_key": CB_KEY, "query": name, "page": 1},
            timeout=10
        )
        resp.raise_for_status()
        
        data = resp.json()
        if not validate_crunchbase_response(data):
            logger.warning(f"Invalid response format from Crunchbase for query: {name}")
            return None
            
        items = data.get("data", {}).get("items", [])
        if not items:
            logger.info(f"No organizations found in Crunchbase for query: {name}")
            return None
            
        logger.info(f"Found organization in Crunchbase: {items[0].get('properties', {}).get('name')}")
        return items[0]
    except requests.RequestException as e:
        logger.error(f"Request error searching for organization '{name}': {str(e)}")
        return None
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Data error processing organization '{name}': {str(e)}")
        return None

def cb_similar_companies(uuid: str) -> List[str]:
    """Find similar companies for a given organization UUID with improved error handling."""
    try:
        url = f"{CB_BASE}/entities/organizations/{uuid}"
        session = get_session()
        
        logger.info(f"Searching Crunchbase for similar companies to UUID: {uuid}")
        resp = session.get(
            url, 
            params={"user_key": CB_KEY, "field_ids": "similar_companies"},
            timeout=10
        )
        resp.raise_for_status()
        
        data = resp.json()
        if not isinstance(data, dict):
            logger.warning(f"Invalid response format from Crunchbase for UUID: {uuid}")
            return []
            
        sims = data.get("similar_companies", [])
        if not sims:
            logger.info(f"No similar companies found in Crunchbase for UUID: {uuid}")
            return []
            
        companies = []
        for c in sims:
            try:
                companies.append(c["identifier"]["value"])
            except (KeyError, TypeError):
                continue
                
        logger.info(f"Found {len(companies)} similar companies in Crunchbase")
        return companies
    except requests.RequestException as e:
        logger.error(f"Request error searching for similar companies to '{uuid}': {str(e)}")
        return []
    except (ValueError, KeyError) as e:
        logger.error(f"Data error processing similar companies to '{uuid}': {str(e)}")
        return []


def validate_pdl_response(data: Any) -> bool:
    """Validate People Data Labs API response format."""
    if not isinstance(data, dict):
        return False
    if "data" not in data or not isinstance(data["data"], list):
        return False
    return True

def pdl_people(companies: List[str], size=200) -> List[Dict[str, Any]]:
    """Search for people from specified companies with improved error handling."""
    try:
        if not companies:
            logger.warning("No companies provided for PDL search")
            return []
            
        regex = " OR ".join([f'"{c}"' for c in companies])
        title_query = '"CEO" OR "Chief" OR Founder OR "Vice" OR VP OR Director'
        query = f'(job_company_name:({regex}) AND job_title:({title_query}))'
        
        params = {
            "api_key": PDL_KEY, 
            "query": query,
            "size": size, 
            "pretty": "false", 
            "dataset": "all"
        }
        
        session = get_session()
        logger.info(f"Searching PDL for people from {len(companies)} companies")
        resp = session.get(PDL_URL, params=params, timeout=15)
        resp.raise_for_status()
        
        data = resp.json()
        if not validate_pdl_response(data):
            logger.warning("Invalid response format from PDL")
            return []
            
        people_data = data.get("data", [])
        logger.info(f"Found {len(people_data)} people in PDL")
        return people_data
    except requests.RequestException as e:
        logger.error(f"Request error searching for people: {str(e)}")
        return []
    except (ValueError, KeyError) as e:
        logger.error(f"Data error processing people search: {str(e)}")
        return []


def score_person(p: Dict[str, Any], seed: str = "", insiders: Optional[List[str]] = None) -> int:
    """Score a person based on title, years of experience, and company relevance."""
    try:
        insiders = insiders or []
        
        title = ""
        if p.get("job_title"):
            title = str(p.get("job_title", "")).lower()
        
        years = 0
        if p.get("job_last_date") and isinstance(p.get("job_last_date"), dict):
            years = p.get("job_last_date", {}).get("num_years", 0)
            if not isinstance(years, (int, float)):
                years = 0
        
        comp = ""
        if p.get("job_company_name"):
            comp = str(p.get("job_company_name", "")).lower()
        
        score = 0
        if title and " " in title:
            first_word = title.split()[0]
            score = TITLE_WEIGHTS.get(first_word, 1) * 3
        
        score += int(years) * 2
        
        if comp and insiders and comp in insiders:
            score += 5
        
        if seed and p.get("job_summary") and isinstance(p.get("job_summary"), str):
            if re.search(seed, p.get("job_summary", "").lower()):
                score += 1
                
        return score
    except Exception as e:
        logger.error(f"Error scoring person: {str(e)}")
        return 0


def extract_company_name(prompt: str) -> str:
    """Extract company name from a prompt more intelligently."""
    try:
        cleaned_prompt = re.sub(
            r'^.*?(get smart on|learn about|understand|research)\s+', 
            '', 
            prompt.lower()
        )
        
        company_name = cleaned_prompt.strip()
        
        if len(company_name.split()) > 3:
            company_name = ' '.join(company_name.split()[-3:])
        
        company_name = ' '.join(word.capitalize() for word in company_name.split())
        
        logger.info(f"Extracted company name from prompt: {company_name}")
        return company_name
    except Exception as e:
        logger.error(f"Error extracting company name: {str(e)}")
        last_word = prompt.split()[-1] if prompt and len(prompt.split()) > 0 else ""
        logger.info(f"Falling back to last word as company name: {last_word}")
        return last_word


def find_and_rank(prompt: str, top_n: int = 25) -> pd.DataFrame:
    """Find and rank experts based on a prompt with improved error handling."""
    try:
        check_api_keys()
        
        seed_company = extract_company_name(prompt)
        if not seed_company:
            logger.error("Could not extract company name from prompt")
            return pd.DataFrame()
            
        seed_org = cb_org_search(seed_company)
        competitors = []
        
        if seed_org:
            try:
                uuid = seed_org["path"].split("/")[-1]
                competitors = cb_similar_companies(uuid)
            except (KeyError, IndexError) as e:
                logger.error(f"Error extracting UUID from organization data: {str(e)}")
        
        if not competitors:
            logger.info("Using fallback competitor list")
            competitors = ["Culligan", "Pelican Water", "APEC Water",
                          "HomeWater", "SpringWell"]
        
        companies = [seed_company] + competitors
        
        people = pdl_people(companies)
        if not people:
            logger.warning("No people found for the specified companies")
            return pd.DataFrame()
        
        ranked = []
        for p in people:
            try:
                if not all(key in p for key in ["full_name", "job_title", "job_company_name"]):
                    continue
                    
                s = score_person(
                    p, 
                    seed=seed_company.lower(),
                    insiders=[seed_company.lower()]
                )
                
                ranked.append({
                    "name": p["full_name"],
                    "title": p["job_title"],
                    "company": p["job_company_name"],
                    "email": p.get("emails", [{}])[0].get("address", "n/a") if p.get("emails") else "n/a",
                    "score": s
                })
            except (KeyError, TypeError) as e:
                logger.error(f"Error processing person data: {str(e)}")
                continue
        
        if not ranked:
            logger.warning("No people could be ranked")
            return pd.DataFrame()
            
        df = pd.DataFrame(ranked).sort_values("score", ascending=False).head(top_n)
        
        csv_filename = f"{seed_company.replace(' ', '_')}_experts.csv"
        df.to_csv(csv_filename, index=False)
        logger.info(f"Saved results to {csv_filename}")
        
        return df
    except Exception as e:
        logger.error(f"Error in find_and_rank: {str(e)}")
        return pd.DataFrame()

if __name__ == "__main__":
    try:
        df = find_and_rank("I'm looking to better understand Aquasana")
        if not df.empty:
            print(df.head(10))
        else:
            print("No results found.")
    except Exception as e:
        print(f"Error: {str(e)}")
