"""Phase 2: submit applications through the career site's own form, with Playwright driving the
installed Edge headless. One module per backend; a backend without one falls back to the email."""
from pathlib import Path

from playwright.sync_api import sync_playwright

from job_agent.apply import greenhouse
from job_agent.apply.answers import build_answers
from job_agent.apply.base import ApplyResult
from job_agent.models import Job

APPLIERS = {greenhouse.NAME: greenhouse}


def can_apply(company: dict) -> bool:
    return company.get("source") in APPLIERS


def apply_job(job: Job, company: dict, cfg: dict, resume_pdf: Path, folder: Path) -> ApplyResult:
    """Fill the form for `job`; submits unless apply.dry_run is set or a required question has no answer.
    A screenshot of the filled form is saved next to the tailored resume either way."""
    answer = build_answers(cfg["applicant"], cfg["screening"], cfg.get("education"))
    applier = APPLIERS[company["source"]]
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page()
            return applier.apply(page, job, company, answer, resume_pdf,
                                 dry_run=bool(cfg.get("apply", {}).get("dry_run", True)),
                                 screenshot=folder / "form.png")
        finally:
            browser.close()
