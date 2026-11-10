"""SmartRecruiters public Posting API (ServiceNow, Acumatica).

List:   GET https://api.smartrecruiters.com/v1/companies/{company}/postings?country=in&q=...
Detail: GET https://api.smartrecruiters.com/v1/companies/{company}/postings/{id}
"""
from job_agent.models import Job
from job_agent.text import html_to_text

NAME = "smartrecruiters"
API = "https://api.smartrecruiters.com/v1/companies"
PAGE = 100
DETAIL_SECTIONS = ("jobDescription", "qualifications", "additionalInformation")


def fetch(company: dict, session) -> list[Job]:
    jobs: list[Job] = []
    offset = 0
    while True:
        params = {"country": "in", "q": company["query"], "limit": PAGE, "offset": offset}
        resp = session.get(f"{API}/{company['company_id']}/postings", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        page = parse_listing(data, company)
        jobs.extend(page)
        offset += PAGE
        if not page or offset >= data.get("totalFound", 0):
            return jobs


def _clean_location(location: dict) -> str:
    # fullLocation comes as "Hyderabad, , India"; drop the empty region
    parts = [p.strip() for p in (location.get("fullLocation") or "").split(",") if p.strip()]
    return ", ".join(parts) or location.get("city", "")


def parse_listing(data: dict, company: dict) -> list[Job]:
    jobs = []
    for posting in data.get("content", []):
        location = posting.get("location") or {}
        jobs.append(Job(
            key=f"{company['name']}:{posting['id']}",
            company=company["name"],
            title=posting["name"],
            locations=(_clean_location(location),),
            url=f"https://jobs.smartrecruiters.com/{company['company_id']}/{posting['id']}",
            posted=posting.get("releasedDate", ""),
            source=NAME,
            remote=bool(location.get("remote")),
        ))
    return jobs


def enrich(job: Job, company: dict, session) -> Job:
    posting_id = job.key.split(":", 1)[1]
    resp = session.get(f"{API}/{company['company_id']}/postings/{posting_id}", timeout=30)
    resp.raise_for_status()
    return parse_detail(job, resp.json())


def parse_detail(job: Job, data: dict) -> Job:
    sections = data.get("jobAd", {}).get("sections", {})
    text = "\n".join(
        html_to_text(sections[name]["text"])
        for name in DETAIL_SECTIONS
        if sections.get(name, {}).get("text")
    )
    return job.with_(description=text, url=data.get("postingUrl") or job.url)
