from job_agent.llm import LLM
from job_agent.models import Job

SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "description": "0-100 fit of the candidate for this job"},
        "reason": {"type": "string", "description": "one or two sentences"},
    },
    "required": ["score", "reason"],
    "additionalProperties": False,
}

SYSTEM = """You score how well a candidate fits a job posting, from 0 (no fit) to 100 (ideal).
Weigh: required skills and languages present on the resume, years of experience asked vs held,
role level (the candidate is a 2026 graduate with 2+ years of combined internship and job experience,
of which ~6 months is full-time; principal/staff/manager roles score low), and domain.
Be strict: 80+ means the candidate meets nearly every stated requirement.
If the job description is missing, score on title and location only and say so in the reason.

CANDIDATE RESUME:
"""


def level_note(roles: dict | None) -> str:
    """Level rule for the scorer, from roles.max_level / roles.level_2_ok_at in config.yaml."""
    if not roles or "max_level" not in roles:
        return ""
    ok = ", ".join(roles.get("level_2_ok_at", []))
    note = ("\n\nTARGET LEVEL: full-time SDE-1 / entry-level engineer roles. Not internships, not campus or "
            "university hiring programmes. A job that needs 3+ years or SDE-2 and above responsibilities scores below 50")
    return note + (f", except at {ok}, where SDE-2 level is fine." if ok else ".")


def score_job(client: LLM, resume_md: str, job: Job, roles: dict | None = None) -> tuple[int, str]:
    user = (
        f"Company: {job.company}\nTitle: {job.title}\nLocations: {', '.join(job.locations)}\n\n"
        f"JOB DESCRIPTION:\n{job.description or '(not available)'}"
    )
    data = client.ask_json(system=SYSTEM + resume_md + level_note(roles), user=user, schema=SCHEMA)
    score = max(0, min(100, int(data["score"])))
    return score, data["reason"]
