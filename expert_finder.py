"""
expert_finder.py
Minimal expert-ranker for Aquasana & competitor space.
Dependencies: requests, pandas, dotenv (optional)
"""

import os, re, requests, pandas as pd
from typing import List

CB_KEY  = os.getenv("CB_KEY")   or "YOUR_CRUNCHBASE_KEY"
PDL_KEY = os.getenv("PDL_KEY")  or "YOUR_PDL_KEY"

CB_BASE = "https://api.crunchbase.com/v4"

def cb_org_search(name: str):
    """Return first org item for a fuzzy company name."""
    url = f"{CB_BASE}/odm-organizations"
    resp = requests.get(url, params={"user_key": CB_KEY, "query": name, "page": 1})
    data = resp.json().get("data", {}).get("items", [])
    return data[0] if data else None

def cb_similar_companies(uuid: str) -> List[str]:
    url = f"{CB_BASE}/entities/organizations/{uuid}"
    resp = requests.get(url, params={"user_key": CB_KEY, "field_ids": "similar_companies"})
    sims = resp.json().get("similar_companies", [])
    return [c["identifier"]["value"] for c in sims]

PDL_URL = "https://api.peopledatalabs.com/v5/person/search"

TITLE_WEIGHTS = {"ceo": 5, "chief": 5, "founder": 5,
                 "president": 4, "vp": 4, "vice": 4,
                 "director": 3, "manager": 2}

def pdl_people(companies: List[str], size=200):
    regex = " OR ".join([f'"{c}"' for c in companies])
    title_query = '"CEO" OR "Chief" OR Founder OR "Vice" OR VP OR Director'
    query = f'(job_company_name:({regex}) AND job_title:({title_query}))'
    params = {"api_key": PDL_KEY, "query": query,
              "size": size, "pretty": "false", "dataset": "all"}
    return requests.get(PDL_URL, params=params).json().get("data", [])

def score_person(p, seed="aquasana", insiders=None):
    insiders = insiders or []
    title = (p.get("job_title") or "").lower()
    years = p.get("job_last_date", {}).get("num_years", 0)
    comp  = (p.get("job_company_name") or "").lower()
    score = TITLE_WEIGHTS.get(title.split()[0], 1) * 3
    score += int(years) * 2
    if comp in insiders:
        score += 5
    if re.search(seed, p.get("job_summary", "").lower()):
        score += 1
    return score

def find_and_rank(prompt: str, top_n=25):
    seed_company = prompt.split()[-1]  # "Aquasana" in our example
    seed_org = cb_org_search(seed_company)
    competitors = []

    if seed_org:
        uuid = seed_org["path"].split("/")[-1]
        competitors = cb_similar_companies(uuid)

    if not competitors:
        competitors = ["Culligan", "Pelican Water", "APEC Water",
                       "HomeWater", "SpringWell"]

    companies = [seed_company] + competitors
    people = pdl_people(companies)

    ranked = []
    for p in people:
        s = score_person(p, seed=seed_company.lower(),
                         insiders=[seed_company.lower()])
        ranked.append({"name": p["full_name"],
                       "title": p["job_title"],
                       "company": p["job_company_name"],
                       "email": p.get("emails", [{}])[0].get("address", "n/a"),
                       "score": s})

    df = pd.DataFrame(ranked).sort_values("score", ascending=False).head(top_n)
    df.to_csv(f"{seed_company}_experts.csv", index=False)
    return df

if __name__ == "__main__":
    df = find_and_rank("I'm looking to better understand Aquasana")
    print(df.head(10))
