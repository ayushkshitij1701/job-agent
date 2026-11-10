"""Oracle HCM Recruiting Cloud candidate-experience REST (JPMorgan, Oracle, Dell, Uber). Public, no key.

List:   GET https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList
            &finder=findReqs;siteNumber={site},keyword="...",selectedLocationsFacet={facet},limit=25,offset=0
Detail: GET https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all&onlyData=true
            &finder=ById;Id="{id}",siteNumber={site}
Oracle rejects the finder when ';' ',' '=' are percent-encoded, so the query string is built by hand.
"""
from urllib.parse import quote

from job_agent.models import Job
from job_agent.text import html_to_text

NAME = "oracle_hcm"
PAGE = 25
MAX_RESULTS = 200
HEADERS = {"User-Agent": "Mozilla/5.0"}
DETAIL_SECTIONS = ("ExternalDescriptionStr", "ExternalResponsibilitiesStr", "ExternalQualificationsStr")


def _api(company: dict, resource: str, finder: str) -> str:
    return (f"https://{company['host']}/hcmRestApi/resources/latest/{resource}"
            f"?onlyData=true&expand={'requisitionList' if resource.endswith('Requisitions') else 'all'}"
            f"&finder={quote(finder, safe=';,=')}")


def _list_url(company: dict, offset: int) -> str:
    finder = f'findReqs;siteNumber={company["site"]},keyword="{company["keyword"]}",limit={PAGE},offset={offset}'
    if company.get("location_facet"):
        finder += f",selectedLocationsFacet={company['location_facet']}"
    return _api(company, "recruitingCEJobRequisitions", finder)


def fetch(company: dict, session) -> list[Job]:
    jobs: list[Job] = []
    offset, total = 0, 0
    while True:
        resp = session.get(_list_url(company, offset), headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        page = parse_listing(data, company)
        jobs.extend(page)
        total = (data.get("items") or [{}])[0].get("TotalJobsCount") or total
        offset += PAGE
        if not page or offset >= min(total, MAX_RESULTS):
            return jobs


def parse_listing(data: dict, company: dict) -> list[Job]:
    jobs = []
    site = company.get("ui_site", company["site"])
    for req in (data.get("items") or [{}])[0].get("requisitionList", []):
        jobs.append(Job(
            key=f"{company['name']}:{req['Id']}",
            company=company["name"],
            title=req["Title"],
            locations=(req.get("PrimaryLocation") or "",),
            url=f"https://{company['host']}/hcmUI/CandidateExperience/en/sites/{site}/job/{req['Id']}",
            posted=req.get("PostedDate", ""),
            source=NAME,
            remote=(req.get("WorkplaceType") or "").lower() == "remote",
        ))
    return jobs


def enrich(job: Job, company: dict, session) -> Job:
    req_id = job.key.split(":", 1)[1]
    url = _api(company, "recruitingCEJobRequisitionDetails", f'ById;Id="{req_id}",siteNumber={company["site"]}')
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return parse_detail(job, resp.json())


def parse_detail(job: Job, data: dict) -> Job:
    item = (data.get("items") or [{}])[0]
    text = "\n".join(html_to_text(item[name]) for name in DETAIL_SECTIONS if item.get(name))
    extra = tuple(loc["Name"] for loc in item.get("secondaryLocations", []) if loc.get("Name") not in job.locations)
    return job.with_(description=text, locations=job.locations + extra)
