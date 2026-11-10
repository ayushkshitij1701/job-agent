"""Workday career sites (Salesforce, Target, Cisco, State Street, Maersk).

List:   POST https://{host}/wday/cxs/{tenant}/{site}/jobs
Detail: GET  https://{host}/wday/cxs/{tenant}/{site}{externalPath}
Both are open JSON endpoints; the search text is a ranking hint, not a filter.
"""
from job_agent.models import Job
from job_agent.text import html_to_text

NAME = "workday"
PAGE = 20
MAX_RESULTS = 200
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def _api(company: dict) -> str:
    return f"https://{company['host']}/wday/cxs/{company['tenant']}/{company['site']}"


def fetch(company: dict, session) -> list[Job]:
    jobs: list[Job] = []
    offset = 0
    total = 0
    while True:
        body = {
            "appliedFacets": company.get("applied_facets", {}),
            "limit": PAGE,
            "offset": offset,
            "searchText": company["search_text"],
        }
        resp = session.post(f"{_api(company)}/jobs", json=body, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        total = data.get("total") or total       # only the first page carries the real total
        page = parse_listing(data, company)
        jobs.extend(page)
        offset += PAGE
        if not page or offset >= total or offset >= MAX_RESULTS:
            return jobs


def parse_listing(data: dict, company: dict) -> list[Job]:
    jobs = []
    for posting in data.get("jobPostings", []):
        req_id = (posting.get("bulletFields") or [posting["externalPath"]])[0]
        jobs.append(Job(
            key=f"{company['name']}:{req_id}",
            company=company["name"],
            title=posting["title"],
            locations=(posting.get("locationsText", ""),),
            url=f"https://{company['host']}/{company['site']}{posting['externalPath']}",
            posted=posting.get("postedOn", ""),
            source=NAME,
        ))
    return jobs


def enrich(job: Job, company: dict, session) -> Job:
    external_path = job.url.split(f"/{company['site']}", 1)[1]
    resp = session.get(f"{_api(company)}{external_path}", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return parse_detail(job, resp.json())


def parse_detail(job: Job, data: dict) -> Job:
    info = data["jobPostingInfo"]
    locations = (info.get("location"), *(info.get("additionalLocations") or []))
    return job.with_(
        description=html_to_text(info.get("jobDescription", "")),
        locations=tuple(loc for loc in locations if loc),
        remote="remote" in (info.get("remoteType") or "").lower(),
        url=info.get("externalUrl") or job.url,
    )
