"""amazon.jobs search API. The listing already carries the full description, so no detail call.

List: GET https://www.amazon.jobs/en/search.json?base_query=...&loc_query=India&country=IND
"""
from job_agent.models import Job
from job_agent.text import html_to_text

NAME = "amazon"
SITE = "https://www.amazon.jobs"
SEARCH = f"{SITE}/en/search.json"
PAGE = 100
MAX_RESULTS = 300
DESCRIPTION_FIELDS = ("description", "basic_qualifications", "preferred_qualifications")


def fetch(company: dict, session) -> list[Job]:
    jobs: list[Job] = []
    offset = 0
    while True:
        params = {"base_query": company["query"], "loc_query": "India", "country": "IND",
                  "result_limit": PAGE, "offset": offset}
        resp = session.get(SEARCH, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        page = parse_listing(data, company)
        jobs.extend(page)
        offset += PAGE
        if not page or offset >= data.get("hits", 0) or offset >= MAX_RESULTS:
            return jobs


def parse_listing(data: dict, company: dict) -> list[Job]:
    jobs = []
    for posting in data.get("jobs", []):
        description = "\n".join(html_to_text(posting.get(f) or "") for f in DESCRIPTION_FIELDS)
        jobs.append(Job(
            key=f"{company['name']}:{posting['id_icims']}",
            company=company["name"],
            title=posting["title"],
            locations=(posting.get("normalized_location") or posting.get("location", ""),),
            url=f"{SITE}{posting['job_path']}",
            posted=posting.get("posted_date", ""),
            source=NAME,
            description=description,
        ))
    return jobs


def enrich(job: Job, company: dict, session) -> Job:
    return job
