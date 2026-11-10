"""One run: fetch listings -> drop seen -> title filter -> enrich -> location filter
-> score -> tailor -> render -> email -> record. Schedule it with Windows Task Scheduler."""
import argparse
import json
import logging
import re
import sys
from dataclasses import asdict
from pathlib import Path

import requests

from job_agent.apply import apply_job, can_apply
from job_agent.config import load_config, load_env
from job_agent.filters import level_matches, location_matches, location_rank, title_matches
from job_agent.llm import PROVIDERS, make_client
from job_agent.matcher import score_job
from job_agent.models import Job
from job_agent.notify import compose_match_email, send_email, with_apply_outcome
from job_agent.render import html_to_pdf, render_resume_html
from job_agent.sources import SOURCES, fetch_all
from job_agent.store import Store
from job_agent.tailor import TailorResult, tailor_resume

log = logging.getLogger("job_agent")

# Group B companies get this until their apply step exists (phase 2); until then they behave like Group A.
AUTO_APPLY_NOTE = "Auto-apply for this site is not built yet - apply yourself at the link above."


def write_outputs(out_dir: Path, job: Job, result: TailorResult) -> list[Path]:
    folder = out_dir / re.sub(r"[^A-Za-z0-9]+", "_", job.key).strip("_")
    folder.mkdir(parents=True, exist_ok=True)
    md_path, html_path, pdf_path = folder / "resume.md", folder / "resume.html", folder / "resume.pdf"
    md_path.write_text(result.resume_md, encoding="utf-8")
    html_path.write_text(render_resume_html(result.resume_md), encoding="utf-8")
    html_to_pdf(html_path, pdf_path)
    (folder / "job.json").write_text(json.dumps(asdict(job), indent=2), encoding="utf-8")
    return [md_path, pdf_path]


def run(cfg: dict, *, client, session, send) -> list[Job]:
    """Process every new job for the referral companies; returns the jobs that were emailed."""
    resume = Path(cfg["resume_path"]).read_text(encoding="utf-8")
    store = Store(cfg["db_path"])
    auto_apply = {c["name"]: c for c in cfg["companies"].get("auto_apply", [])}
    companies = {c["name"]: c for c in cfg["companies"]["referral"]} | auto_apply
    roles, locations = cfg["roles"], cfg["locations"]
    notified: list[Job] = []

    jobs = [j for j in fetch_all(companies.values(), session, SOURCES) if not store.seen(j.key)]
    log.info("%d new jobs to look at", len(jobs))
    candidates = []
    for job in jobs:
        if not title_matches(job.title, roles["include"], roles["exclude"]):
            store.add(job, "skipped_title")
            continue
        if not level_matches(job.title, job.company, roles):
            store.add(job, "skipped_level")
            continue
        try:
            job = SOURCES[job.source].enrich(job, companies[job.company], session)
        except Exception:
            log.exception("enrich failed for %s; will retry next run", job.key)
            continue
        if not location_matches(job, locations["job_cities"], locations["include_remote"]):
            store.add(job, "skipped_location")
            continue
        candidates.append(job)

    rank = lambda j: location_rank(j, locations["job_cities"]) if location_rank(j, locations["job_cities"]) is not None else len(locations["job_cities"])
    for job in sorted(candidates, key=rank):
        try:
            score, reason = score_job(client, resume, job, roles)
            if score < cfg["match"]["min_score"]:
                store.add(job, "skipped_score", score, reason)
                continue
            result = tailor_resume(client, resume, job.description, cfg["tailor"])
            attachments = write_outputs(Path(cfg["out_dir"]), job, result)
            company = companies[job.company]
            outcome = None
            if job.company in auto_apply and can_apply(company):
                outcome = apply_job(job, company, cfg, attachments[1], attachments[0].parent)
            note = company.get("referral_note") or (AUTO_APPLY_NOTE if job.company in auto_apply and not outcome else None)
            subject, body = compose_match_email(job, score, reason, result, note)
            if outcome:
                subject, body = with_apply_outcome(subject, body, outcome)
                if (attachments[0].parent / "form.png").exists():
                    attachments.append(attachments[0].parent / "form.png")
            send(cfg["notify"]["to"], subject, body, attachments)
        except Exception:
            log.exception("score/tailor/apply/email failed for %s; will retry next run", job.key)
            continue
        status = outcome.status if outcome else "notified"
        store.add(job, status, score, reason)
        notified.append(job)
        log.info("%s: %s (score %d)", status, job.key, score)
    return notified


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m job_agent.main", description="One run of the job agent.")
    p.add_argument("--provider", choices=sorted(PROVIDERS), help="override llm.provider from config.yaml")
    p.add_argument("--model", help="override the model of the chosen provider (e.g. qwen3.5:4b, gemini-3.6-flash)")
    p.add_argument("--think", action=argparse.BooleanOptionalAction, default=None,
                   help="ollama only: --think lets the model reason before answering (slower), --no-think skips it")
    return p.parse_args(argv)


def apply_llm_overrides(llm_cfg: dict, args: argparse.Namespace) -> dict:
    """Command-line flags win over config.yaml; anything not given keeps the config value."""
    if args.provider:
        llm_cfg["provider"] = args.provider
    if args.model:
        llm_cfg.setdefault(llm_cfg["provider"], {})["model"] = args.model
    if args.think is not None:
        llm_cfg.setdefault("ollama", {})["think"] = args.think
    return llm_cfg


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    load_env(root / ".env")
    cfg = load_config(root / "config.yaml")
    for key in ("resume_path", "db_path", "out_dir"):
        cfg[key] = str(root / cfg[key])
    llm_cfg = apply_llm_overrides(cfg["llm"], args)
    log.info("llm: %s / %s", llm_cfg["provider"], llm_cfg[llm_cfg["provider"]]["model"])
    session = requests.Session()
    notified = run(cfg, client=make_client(llm_cfg, session), session=session, send=send_email)
    print(f"{len(notified)} job(s) emailed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
