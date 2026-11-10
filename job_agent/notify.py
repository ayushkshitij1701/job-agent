import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from job_agent.apply.base import ApplyResult
from job_agent.models import Job
from job_agent.tailor import TailorResult

SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 465


def send_email(to: str, subject: str, body: str, attachments: list[Path]) -> None:
    user, password = os.environ["SMTP_USER"], os.environ["SMTP_APP_PASSWORD"]
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = user, to, subject
    msg.set_content(body)
    for path in attachments:
        ctype, _ = mimetypes.guess_type(path.name)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)


def compose_match_email(job: Job, score: int, reason: str, result: TailorResult,
                        referral_note: str | None) -> tuple[str, str]:
    subject = f"[job-agent] {job.company}: {job.title} (score {score})"
    lines = [
        f"{job.company} — {job.title}",
        f"Location: {', '.join(job.locations) or 'n/a'}",
        f"Posted: {job.posted or 'n/a'}",
        f"Apply: {job.url}",
        "",
        f"Fit score: {score}/100 — {reason}",
    ]
    if referral_note:
        lines += ["", f"REFERRAL: {referral_note}"]
    lines += ["", "TAILORED RESUME (attached as .md and .pdf)"]
    if result.fell_back:
        lines += ["Tailoring was rejected twice by the guard, so the master resume attached unchanged.",
                  "Rejected because:"] + [f"  - {v}" for v in result.violations]
    else:
        lines += ["Changes:"] + [f"  - {c}" for c in result.changes or ["none"]]
        if result.added_skills:
            lines += ["Skills added from your allowlist:"] + \
                     [f"  - {s['term']} ({s['via']})" for s in result.added_skills]
    if result.missing_requirements:
        lines += ["", "JD asks for these, which are not on your resume or allowlist:"] + \
                 [f"  - {m}" for m in result.missing_requirements]
    return subject, "\n".join(lines) + "\n"


def with_apply_outcome(subject: str, body: str, outcome: ApplyResult) -> tuple[str, str]:
    """Prefix the subject with what happened on the form and describe it at the top of the body."""
    if outcome.submitted:
        tag, lines = "APPLIED", ["APPLICATION SUBMITTED automatically. Answers given:"]
    elif outcome.unanswered:
        tag, lines = "NEEDS YOUR ANSWER", ["NOT SUBMITTED - the form asks these and I have no answer configured:"] + \
                     [f"  - {u}" for u in outcome.unanswered] + ["Apply yourself at the link above, or add the answer to config.yaml.", "", "Filled so far:"]
    elif outcome.error:
        tag, lines = "APPLY FAILED", [f"NOT SUBMITTED - {outcome.error}", "Apply yourself at the link above.", "", "Filled before it failed:"]
    else:
        tag, lines = "DRY RUN", ["FORM FILLED BUT NOT SUBMITTED (apply.dry_run is true in config.yaml).",
                                 "Check form.png in the output folder, then set apply.dry_run: false.", "", "Answers given:"]
    lines += [f"  - {f}" for f in outcome.filled or ["none"]]
    if outcome.skipped:
        lines += ["Left empty on purpose: " + ", ".join(outcome.skipped)]
    return subject.replace("[job-agent] ", f"[job-agent] {tag}: ", 1), "\n".join(lines) + "\n\n" + body
