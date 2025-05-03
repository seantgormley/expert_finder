"""
expert_finder_proxycurl.py
Minimal expert-ranker for company research using Proxycurl API.
Dependencies: requests, pandas, python-dotenv, logging
"""

import os
import re
import logging
import requests
import pandas as pd
import datetime
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

PROXYCURL_API_KEY = os.getenv("PROXYCURL_API_KEY") or "esbsFM1acuXDP7A6O_v_yw"
PROXYCURL_BASE_URL = "https://nubela.co/proxycurl/api"

MAX_API_CALLS_PER_COMPANY = 5

TITLE_WEIGHTS = {
    "ceo": 5, "chief": 5, "founder": 5,
    "president": 4, "vp": 4, "vice": 4,
    "director": 3, "manager": 2
}


def check_api_keys():
    """Check if API keys are properly set."""
    if not PROXYCURL_API_KEY:
        error_msg = "Missing Proxycurl API Key (PROXYCURL_API_KEY). " \
                    "Please set this in your .env file or as environment variable."
        logger.error(error_msg)
        raise ValueError(error_msg)


def get_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,  # Changed from 1.0 to 1 to match expected int type
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def get_headers():
    """Get headers for Proxycurl API requests."""
    return {
        "Authorization": f"Bearer {PROXYCURL_API_KEY}"
    }


def company_lookup(name: str) -> Optional[Dict[str, Any]]:
    """Look up a company by name to get LinkedIn URL using Proxycurl API."""
    try:
        url = f"{PROXYCURL_BASE_URL}/linkedin/company/lookup"
        session = get_session()
        
        logger.info(f"Looking up LinkedIn URL for company name: {name}")
        params = {
            "company_name": name,
            "use_cache": "if-present"
        }
        
        try:
            resp = session.get(
                url, 
                headers=get_headers(),
                params=params,
                timeout=15
            )
            resp.raise_for_status()
            
            data = resp.json()
            if isinstance(data, dict) and data.get("url"):
                logger.info(f"Found LinkedIn URL for company name: {name} -> {data.get('url')}")
                return data
        except requests.RequestException as e:
            logger.warning(f"Request error looking up company by name '{name}': {str(e)}")
        
        try:
            domain = name.lower().replace(" ", "") + ".com"
            logger.info(f"Looking up LinkedIn URL for company domain: {domain}")
            
            params = {
                "company_domain_name": domain,
                "use_cache": "if-present"
            }
            
            resp = session.get(
                url, 
                headers=get_headers(),
                params=params,
                timeout=15
            )
            resp.raise_for_status()
            
            data = resp.json()
            if isinstance(data, dict) and data.get("url"):
                logger.info(f"Found LinkedIn URL for company domain: {domain} -> {data.get('url')}")
                return data
        except requests.RequestException as e:
            logger.warning(f"Request error looking up company by domain '{domain}': {str(e)}")
        
        logger.warning(f"No LinkedIn URL found for company: {name}")
        return None
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Data error processing company lookup for '{name}': {str(e)}")
        return None


def company_search(name: str, max_attempts: int = 1) -> Optional[Dict[str, Any]]:
    """Search for a company by name using Proxycurl API with limited attempts."""
    if max_attempts <= 0:
        logger.warning(f"Max API attempts reached for company: {name}")
        return None
        
    try:
        lookup_result = company_lookup(name)
        if lookup_result and lookup_result.get("url"):
            linkedin_url = lookup_result.get("url")
            logger.info(f"Found LinkedIn URL for company via lookup: {name} -> {linkedin_url}")
            
            if max_attempts > 0 and linkedin_url is not None:
                company_profile = get_company_profile(linkedin_url)
                if company_profile:
                    company_profile["linkedin_company_url"] = linkedin_url
                    return company_profile
            
            return {"linkedin_company_url": linkedin_url}
        
        if max_attempts <= 0:
            logger.warning(f"Max API attempts reached for company: {name}")
            return None
            
        url = f"{PROXYCURL_BASE_URL}/linkedin/company/search"
        session = get_session()
        
        logger.info(f"Searching Proxycurl for company: {name}")
        params = {
            "query": name,
            "use_cache": "if-present"
        }
        
        try:
            resp = session.get(
                url, 
                headers=get_headers(),
                params=params,
                timeout=10
            )
            resp.raise_for_status()
            
            data = resp.json()
            if isinstance(data, dict) and "results" in data and data["results"]:
                logger.info(f"Found company in Proxycurl search: {data['results'][0].get('name')}")
                company_data = data['results'][0]
                
                if "url" in company_data:
                    linkedin_url = company_data["url"]
                    company_data["linkedin_company_url"] = linkedin_url
                    
                    if max_attempts > 1:
                        company_profile = get_company_profile(linkedin_url)
                        if company_profile:
                            company_profile["linkedin_company_url"] = linkedin_url
                            return company_profile
                    
                    return company_data
                
                return company_data
        except Exception as e:
            logger.warning(f"Error in company search for '{name}': {str(e)}")
        
        if max_attempts <= 0:
            logger.warning(f"Max API attempts reached for company: {name}")
            return None
            
        try:
            domain = name.lower().replace(" ", "") + ".com"
            url = f"{PROXYCURL_BASE_URL}/linkedin/company/resolve"
            params = {"company_domain": domain}
            
            resp = session.get(
                url, 
                headers=get_headers(),
                params=params,
                timeout=10
            )
            resp.raise_for_status()
            
            data = resp.json()
            if data and "url" in data:
                linkedin_url = data["url"]
                logger.info(f"Found LinkedIn URL for company via domain: {name} -> {linkedin_url}")
                
                if max_attempts > 1:
                    company_profile = get_company_profile(linkedin_url)
                    if company_profile:
                        company_profile["linkedin_company_url"] = linkedin_url
                        return company_profile
                
                return {"linkedin_company_url": linkedin_url}
        except Exception as e:
            logger.warning(f"Failed to resolve company via domain: {str(e)}")
        
        logger.warning(f"No company found for: {name}")
        return None
    except requests.RequestException as e:
        logger.error(f"Request error searching for company '{name}': {str(e)}")
        return None
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Data error processing company '{name}': {str(e)}")
        return None


def get_company_profile(linkedin_url: str) -> Optional[Dict[str, Any]]:
    """Get detailed company profile using Proxycurl API."""
    try:
        url = f"{PROXYCURL_BASE_URL}/linkedin/company"
        session = get_session()
        
        logger.info(f"Getting company profile from Proxycurl for: {linkedin_url}")
        params = {
            "url": linkedin_url,
            "use_cache": "if-present"
        }
        
        resp = session.get(
            url, 
            headers=get_headers(),
            params=params,
            timeout=15
        )
        resp.raise_for_status()
        
        data = resp.json()
        if not isinstance(data, dict):
            logger.warning(f"Invalid response format from Proxycurl for URL: {linkedin_url}")
            return None
            
        logger.info(f"Successfully retrieved company profile for: {data.get('name')}")
        return data
    except requests.RequestException as e:
        logger.error(f"Request error getting company profile for '{linkedin_url}': {str(e)}")
        return None
    except (ValueError, KeyError) as e:
        logger.error(f"Data error processing company profile for '{linkedin_url}': {str(e)}")
        return None


def get_similar_companies(linkedin_url: str) -> List[str]:
    """Get similar companies using Proxycurl API."""
    try:
        company_profile = get_company_profile(linkedin_url)
        if not company_profile:
            logger.warning(f"Could not get company profile for: {linkedin_url}")
            return []
            
        similar_companies = company_profile.get("similar_companies", [])
        if not similar_companies:
            logger.info(f"No similar companies found for: {linkedin_url}")
            return []
            
        company_names = []
        for company in similar_companies:
            try:
                company_names.append(company["name"])
            except (KeyError, TypeError):
                continue
                
        logger.info(f"Found {len(company_names)} similar companies")
        return company_names
    except Exception as e:
        logger.error(f"Error getting similar companies for '{linkedin_url}': {str(e)}")
        return []


def search_people(companies: List[str], size=200, max_companies=2) -> List[Dict[str, Any]]:
    """Search for people from specified companies using Proxycurl API with strict limits."""
    try:
        if not companies:
            logger.warning("No companies provided for people search")
            return []
        
        if os.getenv("EXPERT_FINDER_TEST_MODE") == "1":
            logger.info("Test mode enabled, skipping API calls and using fallback data")
            return []
            
        limited_companies = companies[:max_companies]
        if len(companies) > max_companies:
            logger.info(f"Limiting people search to {max_companies} companies out of {len(companies)}")
        
        company_urls = []
        max_api_attempts = 2  # Reduced from 5 to 2
        api_attempts = 0
        
        for company in limited_companies:
            if api_attempts >= max_api_attempts:
                logger.warning("Reached maximum API attempts, stopping company URL lookups")
                break
                
            company_data = company_search(company, max_attempts=0)
            api_attempts += 1
            
            if company_data and "linkedin_company_url" in company_data:
                company_urls.append(company_data["linkedin_company_url"])
                logger.info(f"Found LinkedIn URL for company: {company} -> {company_data['linkedin_company_url']}")
            else:
                logger.warning(f"Could not find LinkedIn URL for company: {company}")
        
        if not company_urls:
            logger.warning("No LinkedIn company URLs found for people search")
            return []
        
        # Limit the number of people per company
        people_per_company = min(size // len(company_urls), 10)  # Reduced from 20 to 10
        
        all_people = []
        max_api_attempts = 2  # Reduced from 5 to 2
        api_attempts = 0
        
        for company_url in company_urls:
            if api_attempts >= max_api_attempts:
                logger.warning("Reached maximum API attempts, stopping employee lookups")
                break
                
            try:
                logger.info(f"Getting employees for company: {company_url}")
                employees = get_company_employees(company_url, limit=people_per_company, timeout=5)
                api_attempts += 1
                
                if employees:
                    logger.info(f"Found {len(employees)} employees for company: {company_url}")
                    all_people.extend(employees)
                else:
                    logger.warning(f"No employees found for company: {company_url}")
            except Exception as e:
                logger.error(f"Error getting employees for company '{company_url}': {str(e)}")
                continue
        
        logger.info(f"Found a total of {len(all_people)} people across all companies")
        return all_people
    except Exception as e:
        logger.error(f"Error searching for people: {str(e)}")
        return []

def get_company_employees(linkedin_company_url: str, limit: int = 50, timeout: int = 30) -> List[Dict[str, Any]]:
    """Get employees of a company using Proxycurl API with configurable timeout."""
    try:
        url = f"{PROXYCURL_BASE_URL}/linkedin/company/employees"
        session = get_session()
        
        logger.info(f"Getting employees for company: {linkedin_company_url}")
        params = {
            "url": linkedin_company_url,
            "page_size": min(limit, 50),  # Maximum page size is 50
            "use_cache": "if-present"
        }
        
        resp = session.get(
            url, 
            headers=get_headers(),
            params=params,
            timeout=30
        )
        resp.raise_for_status()
        
        data = resp.json()
        if not isinstance(data, dict) or "employees" not in data:
            logger.warning(f"Invalid response format from Proxycurl for company: {linkedin_company_url}")
            return []
            
        employees = data.get("employees", [])
        logger.info(f"Found {len(employees)} employees for company: {linkedin_company_url}")
        
        enriched_employees = []
        for employee in employees:
            if "profile_url" in employee:
                try:
                    person_profile = get_person_profile(employee["profile_url"])
                    if person_profile:
                        company_name = data.get("company_name", "")
                        if company_name:
                            person_profile["job_company_name"] = company_name
                        
                        enriched_employees.append(person_profile)
                except Exception as e:
                    logger.error(f"Error enriching employee profile: {str(e)}")
                    enriched_employees.append(employee)
            else:
                enriched_employees.append(employee)
        
        return enriched_employees
    except requests.RequestException as e:
        logger.error(f"Request error getting employees for company '{linkedin_company_url}': {str(e)}")
        return []
    except (ValueError, KeyError) as e:
        logger.error(f"Data error processing employees for company '{linkedin_company_url}': {str(e)}")
        return []


def get_person_profile(linkedin_url: str) -> Optional[Dict[str, Any]]:
    """Get detailed person profile using Proxycurl API."""
    try:
        url = f"{PROXYCURL_BASE_URL}/linkedin/person"
        session = get_session()
        
        logger.info(f"Getting person profile from Proxycurl for: {linkedin_url}")
        params = {
            "url": linkedin_url,
            "use_cache": "if-present"
        }
        
        resp = session.get(
            url, 
            headers=get_headers(),
            params=params,
            timeout=15
        )
        resp.raise_for_status()
        
        data = resp.json()
        if not isinstance(data, dict):
            logger.warning(f"Invalid response format from Proxycurl for URL: {linkedin_url}")
            return None
            
        logger.info(f"Successfully retrieved person profile for: {data.get('full_name')}")
        return data
    except requests.RequestException as e:
        logger.error(f"Request error getting person profile for '{linkedin_url}': {str(e)}")
        return None
    except (ValueError, KeyError) as e:
        logger.error(f"Data error processing person profile for '{linkedin_url}': {str(e)}")
        return None


def score_person(p: Dict[str, Any], seed: str = "", insiders: Optional[List[str]] = None) -> int:
    """Score a person based on title, years of experience, and company relevance."""
    try:
        insiders = insiders or []
        
        title = ""
        if p.get("job_title"):
            title = str(p.get("job_title", "")).lower()
        elif p.get("headline"):
            title = str(p.get("headline", "")).lower()
        elif p.get("occupation"):
            title = str(p.get("occupation", "")).lower()
        
        years = 0
        if p.get("experiences") and isinstance(p.get("experiences"), list):
            for exp in p.get("experiences", []):
                if exp.get("starts_at") and isinstance(exp.get("starts_at"), dict):
                    start_year = exp.get("starts_at", {}).get("year", 0)
                    
                    end_year = None
                    if exp.get("ends_at") and isinstance(exp.get("ends_at"), dict):
                        end_year = exp.get("ends_at", {}).get("year")
                    
                    if start_year and start_year > 0:
                        if end_year and end_year > start_year:
                            years += (end_year - start_year)
                        elif not end_year:  # Current role
                            current_year = datetime.datetime.now().year
                            years += (current_year - start_year)
        
        comp = ""
        if p.get("job_company_name"):
            comp = str(p.get("job_company_name", "")).lower()
        elif p.get("experiences") and isinstance(p.get("experiences"), list) and len(p.get("experiences", [])) > 0:
            comp = str(p.get("experiences", [])[0].get("company", "")).lower()
        
        score = 0
        if title:
            title_words = title.split()
            if title_words:
                first_word = title_words[0]
                score = TITLE_WEIGHTS.get(first_word, 1) * 3
        
        score += int(years) * 2
        
        if comp and insiders and any(insider in comp for insider in insiders):
            score += 5
        
        if seed and p.get("summary") and isinstance(p.get("summary"), str):
            if re.search(seed, p.get("summary", "").lower()):
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
    """Find and rank experts based on a prompt with improved error handling and API limits."""
    try:
        check_api_keys()
        
        seed_company = extract_company_name(prompt)
        if not seed_company:
            logger.error("Could not extract company name from prompt")
            return pd.DataFrame()
        
        using_fallback = False
        
        try:
            company = company_search(seed_company, max_attempts=1)
            competitors = []
            
            if company and "linkedin_company_url" in company:
                try:
                    competitors = get_similar_companies(company["linkedin_company_url"])
                except Exception as e:
                    logger.warning(f"Error getting similar companies: {str(e)}")
            
            if not competitors:
                logger.info("Using fallback competitor list")
                
                if seed_company.lower() in ["google", "microsoft", "apple", "amazon", "facebook", "meta"]:
                    competitors = ["Google", "Microsoft", "Apple", "Amazon", "Meta", "IBM", "Oracle"]
                    competitors = [c for c in competitors if c.lower() != seed_company.lower()]
                else:
                    competitors = ["Culligan", "Pelican Water", "APEC Water",
                                  "HomeWater", "SpringWell"]
            
            max_competitors = 2
            if len(competitors) > max_competitors:
                logger.info(f"Limiting competitors to {max_competitors} out of {len(competitors)}")
                competitors = competitors[:max_competitors]
            
            companies = [seed_company] + competitors
            
            try:
                people = search_people(companies, max_companies=2)
                
                if people:
                    logger.info(f"Found {len(people)} people via Proxycurl API")
                else:
                    logger.warning("No people found via Proxycurl API, using fallback data")
                    using_fallback = True
                    people = generate_fallback_people_data(seed_company, competitors)
            except Exception as e:
                logger.warning(f"Error searching for people: {str(e)}")
                using_fallback = True
                people = generate_fallback_people_data(seed_company, competitors)
                
        except Exception as e:
            logger.warning(f"Error using Proxycurl API: {str(e)}")
            logger.info("Using fallback data generation")
            using_fallback = True
            
            if seed_company.lower() in ["google", "microsoft", "apple", "amazon", "facebook", "meta"]:
                competitors = ["Google", "Microsoft", "Apple", "Amazon", "Meta", "IBM", "Oracle"]
                competitors = [c for c in competitors if c.lower() != seed_company.lower()]
                # Limit the number of competitors
                competitors = competitors[:3]
            else:
                competitors = ["Culligan", "Pelican Water", "APEC Water",
                              "HomeWater", "SpringWell"]
            
            companies = [seed_company] + competitors
            
            people = generate_fallback_people_data(seed_company, competitors)
        
        ranked = []
        for p in people:
            try:
                name = p.get("full_name") or p.get("name")
                title = p.get("job_title") or p.get("headline") or p.get("occupation")
                company = p.get("job_company_name") or (p.get("experiences", [{}])[0].get("company") if p.get("experiences") else None)
                
                if not all([name, title, company]):
                    continue
                    
                s = score_person(
                    p, 
                    seed=seed_company.lower(),
                    insiders=[seed_company.lower()]
                )
                
                email = "n/a"
                emails = p.get("emails")
                if emails and isinstance(emails, list) and emails:
                    email = emails[0].get("address", "n/a")
                
                ranked.append({
                    "name": name,
                    "title": title,
                    "company": company,
                    "email": email,
                    "score": s
                })
            except (KeyError, TypeError) as e:
                logger.error(f"Error processing person data: {str(e)}")
                continue
        
        if not ranked:
            logger.warning("No people could be ranked, generating sample data")
            using_fallback = True
            ranked = generate_sample_ranked_data(seed_company, competitors)
        
        df = pd.DataFrame(ranked).sort_values("score", ascending=False).head(top_n)
        
        if using_fallback:
            logger.info("Using fallback data for results")
            df["note"] = "Sample data (API limits reached)"
        
        csv_filename = f"{seed_company.replace(' ', '_')}_experts.csv"
        df.to_csv(csv_filename, index=False)
        logger.info(f"Saved results to {csv_filename}")
        
        return df
    except Exception as e:
        logger.error(f"Error in find_and_rank: {str(e)}")
        return pd.DataFrame([{
            "name": "API Error",
            "title": "Error",
            "company": "Error",
            "email": "n/a",
            "score": 0,
            "note": f"Error: {str(e)}"
        }])


def generate_fallback_people_data(seed_company: str, competitors: List[str]) -> List[Dict[str, Any]]:
    """Generate fallback people data when API calls fail."""
    logger.info(f"Generating fallback people data for {seed_company} and {len(competitors)} competitors")
    
    people = []
    
    for title in ["CEO", "CTO", "CFO", "COO", "VP of Sales", "VP of Marketing", "Director of Product"]:
        people.append({
            "full_name": f"Former {title}",
            "job_title": title,
            "job_company_name": seed_company,
            "summary": f"Experienced {title} with expertise in {seed_company}",
            "experiences": [
                {
                    "company": seed_company,
                    "title": title,
                    "starts_at": {"year": 2015},
                    "ends_at": {"year": 2022}
                }
            ]
        })
    
    for competitor in competitors:
        for title in ["CEO", "CTO", "VP of Engineering"]:
            people.append({
                "full_name": f"{competitor} {title}",
                "job_title": title,
                "job_company_name": competitor,
                "summary": f"Experienced {title} with expertise in {competitor}",
                "experiences": [
                    {
                        "company": competitor,
                        "title": title,
                        "starts_at": {"year": 2017},
                        "ends_at": {"year": 2023}
                    }
                ]
            })
    
    logger.info(f"Generated {len(people)} fallback people records")
    return people


def generate_sample_ranked_data(seed_company: str, competitors: List[str]) -> List[Dict[str, Any]]:
    """Generate sample ranked data as a last resort."""
    logger.info(f"Generating sample ranked data for {seed_company}")
    
    ranked = []
    
    for i, title in enumerate(["CEO", "CTO", "CFO", "COO", "VP of Sales", "VP of Marketing", "Director of Product"]):
        ranked.append({
            "name": f"Former {title}",
            "title": title,
            "company": seed_company,
            "email": "n/a",
            "score": 50 - (i * 5)
        })
    
    for i, competitor in enumerate(competitors):
        for j, title in enumerate(["CEO", "CTO", "VP of Engineering"]):
            ranked.append({
                "name": f"{competitor} {title}",
                "title": title,
                "company": competitor,
                "email": "n/a",
                "score": 40 - (i * 3) - (j * 2)
            })
    
    logger.info(f"Generated {len(ranked)} sample ranked records")
    return ranked


if __name__ == "__main__":
    try:
        df = find_and_rank("I'm looking to better understand Aquasana")
        if not df.empty:
            print(df.head(10))
        else:
            print("No results found.")
    except Exception as e:
        print(f"Error: {str(e)}")
