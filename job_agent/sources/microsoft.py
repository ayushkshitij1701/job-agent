"""Microsoft careers (Eightfold).

List:   GET https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query=...&location=India
Detail: GET https://apply.careers.microsoft.com/api/apply/v2/jobs/{position id}?domain=microsoft.com
The listing carries no description; the detail call fills it. The position id is the
number at the end of positionUrl, not displayJobId.
"""
from datetime import datetime, timezone

from job_agent.models import Job
from job_agent.text import html_to_text

NAME = "microsoft"
SITE = "https://apply.careers.microsoft.com"
SEARCH = f"{SITE}/api/pcsx/search"
DETAIL = f"{SITE}/api/apply/v2/jobs"
PAGE = 20
MAX_RESULTS = 200
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}


def fetch(company: dict, session) -> list[Job]:
    jobs: list[Job] = []
    start = 0
    while True:
        params = {"domain": "microsoft.com", "query": company["query"], "location": "India",
                  "start": start, "num": PAGE}
        resp = session.get(SEARCH, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        page = parse_listing(data, company)
        jobs.extend(page)
        start += PAGE
        if not page or start >= data["data"].get("count", 0) or start >= MAX_RESULTS:
            return jobs


def _posted(position: dict) -> str:
    ts = position.get("postedTs")
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat() if ts else ""


def parse_listing(data: dict, company: dict) -> list[Job]:
    jobs = []
    for position in data["data"].get("positions", []):
        jobs.append(Job(
            key=f"{company['name']}:{position['displayJobId']}",
            company=company["name"],
            title=position["name"],
            locations=tuple(position.get("locations") or []),
            url=f"{SITE}{position['positionUrl']}",
            posted=_posted(position),
            source=NAME,
            remote=position.get("workLocationOption") == "remote",
        ))
    return jobs


def enrich(job: Job, company: dict, session) -> Job:
    position_id = job.url.rsplit("/", 1)[1]
    resp = session.get(f"{DETAIL}/{position_id}", params={"domain": "microsoft.com"}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return parse_detail(job, resp.json())


def parse_detail(job: Job, data: dict) -> Job:
    return job.with_(
        description=html_to_text(data.get("job_description", "")),
        locations=tuple(data.get("locations") or job.locations),
        url=data.get("canonicalPositionUrl") or job.url,
    )
