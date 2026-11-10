import logging

from job_agent.models import Job

from . import amazon, greenhouse, microsoft, oracle_hcm, smartrecruiters, workday

log = logging.getLogger(__name__)

SOURCES = {m.NAME: m for m in (workday, smartrecruiters, microsoft, amazon, greenhouse, oracle_hcm)}


def fetch_all(companies: list[dict], session, sources: dict = SOURCES) -> list[Job]:
    """Fetch listings for every company; one company failing must not stop the others."""
    jobs: list[Job] = []
    for company in companies:
        source = sources.get(company["source"])
        if source is None:                  # backend listed in config but no fetcher written yet (COMPANIES.md)
            log.warning("no fetcher for %s (%s); skipped", company["name"], company["source"])
            continue
        try:
            jobs.extend(source.fetch(company, session))
        except Exception:
            log.exception("fetch failed for %s", company["name"])
    return jobs
