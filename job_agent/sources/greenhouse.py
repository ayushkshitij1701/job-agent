"""Greenhouse Job Board API (Stripe, Twilio, Zscaler, Commvault, ...). Public, no key, no search:
the list is every open job on the board, filtered client-side by title/location like the others.

List:   GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs
Detail: GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{id}   (content = HTML-escaped HTML)
"""
import html

from job_agent.models import Job
from job_agent.text import html_to_text

NAME = "greenhouse"
API = "https://boards-api.greenhouse.io/v1/boards"


def fetch(company: dict, session) -> list[Job]:
    resp = session.get(f"{API}/{company['board']}/jobs", timeout=60)
    resp.raise_for_status()
    return parse_listing(resp.json(), company)


def parse_listing(data: dict, company: dict) -> list[Job]:
    jobs = []
    for posting in data.get("jobs", []):
        location = (posting.get("location") or {}).get("name", "")
        jobs.append(Job(
            key=f"{company['name']}:{posting['id']}",
            company=company["name"],
            title=posting["title"],
            locations=(location,),
            url=posting["absolute_url"],
            posted=posting.get("first_published") or posting.get("updated_at", ""),
            source=NAME,
            remote="remote" in location.lower(),
        ))
    return jobs


def enrich(job: Job, company: dict, session) -> Job:
    posting_id = job.key.split(":", 1)[1]
    resp = session.get(f"{API}/{company['board']}/jobs/{posting_id}", timeout=30)
    resp.raise_for_status()
    return parse_detail(job, resp.json())


def parse_detail(job: Job, data: dict) -> Job:
    description = html_to_text(html.unescape(data.get("content") or ""))
    offices = [o.get("location") or o.get("name", "") for o in data.get("offices", [])]
    locations = job.locations + tuple(o for o in offices if o and o not in job.locations)
    return job.with_(description=description, locations=locations)
