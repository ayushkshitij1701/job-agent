"""Tailor the master resume to one job description, within hard limits.

Claude may reorder and reword; it may not add claims. The guard below checks that in code:
every number, and every word containing a capital letter or digit (how technology names look),
must already be on the master resume, be on the user's allowlist, or be a JD spelling of a
master term (e.g. "Postgres" for "PostgreSQL"). One retry with the violations, then fall back
to the master resume unchanged.
"""
import re
from dataclasses import dataclass

from job_agent.llm import LLM

SCHEMA = {
    "type": "object",
    "properties": {
        "resume_markdown": {"type": "string"},
        "changes": {"type": "array", "items": {"type": "string"}},
        "added_skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "via": {"type": "string", "description": "'exact' or 'category: <category text>'"},
                },
                "required": ["term", "via"],
                "additionalProperties": False,
            },
        },
        "missing_requirements": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["resume_markdown", "changes", "added_skills", "missing_requirements"],
    "additionalProperties": False,
}

SYSTEM = """You tailor a candidate's Markdown resume to one job description so it passes an ATS keyword
filter. Make only minor edits. Return the complete resume as Markdown.

ALLOWED:
- Reorder bullets, skills and projects so those matching the JD come first.
- Reword existing bullets using the JD's own terms for things already on the resume
  (e.g. "PostgreSQL" -> "Postgres", "REST APIs" -> "RESTful services", "LLM" -> "GenAI").
- Rewrite the one-line summary to lead with the role the JD names.
- Add a skill to the Skills section only if the JD asks for it AND it is on the allowlist below:
  either an exact term, or a term that fits one of the allowlist categories. Report each addition
  in added_skills with via = "exact" or via = "category: <the category text copied exactly>".

NEVER:
- Add numbers, metrics, tools, technologies or responsibilities that are not on the master resume.
- Change dates, titles, companies, education or publications.
- Add anything not on the allowlist, even if the JD requires it. List such gaps in missing_requirements.
"""

NUMBER_RE = re.compile(r"\d[\d,.]*\+?%?")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.]*[A-Za-z0-9+#]|[A-Za-z]")
LINE_START_RE = re.compile(r"(?:^|\n)[\s\-*#>]*(?:\d+\.\s*)?$")


@dataclass
class TailorResult:
    resume_md: str
    changes: list[str]
    added_skills: list[dict]
    missing_requirements: list[str]
    fell_back: bool
    violations: list[str]


def _words(text: str) -> set[str]:
    return {w.lower() for w in WORD_RE.findall(text)}


def _at_sentence_start(text: str, pos: int) -> bool:
    before = text[:pos]
    return bool(LINE_START_RE.search(before)) or before.rstrip().endswith((".", "!", "?", ":"))


def _jd_spelling_of_master_term(word: str, jd_words: set[str], master_words: set[str]) -> bool:
    if word not in jd_words or len(word) < 4:
        return False
    return any(len(m) >= 4 and (word in m or m in word) for m in master_words)


def guard(master: str, tailored: str, jd: str, allowed_terms: list[str]) -> list[str]:
    master_words, jd_words = _words(master), _words(jd)
    allow_words = {w for term in allowed_terms for w in _words(term)}
    violations = []
    for number in sorted(set(NUMBER_RE.findall(tailored)) - set(NUMBER_RE.findall(master))):
        violations.append(f"new number: {number}")
    seen = set()
    for match in WORD_RE.finditer(tailored):
        word = match.group()
        lower = word.lower()
        if lower in seen or not re.search(r"[A-Z0-9]", word) or _at_sentence_start(tailored, match.start()):
            continue
        seen.add(lower)
        if lower in master_words or lower in allow_words:
            continue
        if _jd_spelling_of_master_term(lower, jd_words, master_words):
            continue
        violations.append(f"new technology or name: {word}")
    return violations


def _allowed_terms(added_skills: list[dict], tailor_cfg: dict) -> tuple[list[str], list[str]]:
    """Split Claude's reported additions into allowed terms and violations, per config."""
    allow = tailor_cfg["skills_allowed_to_add"]
    exact = {t.lower() for t in allow.get("exact", [])}
    categories = set(allow.get("categories", []))
    allowed, violations = [], []
    for item in added_skills:
        term, via = item["term"], item["via"]
        if via == "exact" and term.lower() in exact:
            allowed.append(term)
        elif via.startswith("category:") and via.split(":", 1)[1].strip() in categories:
            allowed.append(term)
        else:
            violations.append(f"skill added outside allowlist: {term} ({via})")
    return allowed, violations


def _prompt(master: str, jd: str, tailor_cfg: dict) -> str:
    allow = tailor_cfg["skills_allowed_to_add"]
    return (
        f"ALLOWLIST exact terms: {', '.join(allow.get('exact', []))}\n"
        f"ALLOWLIST categories: {'; '.join(allow.get('categories', []))}\n\n"
        f"MASTER RESUME:\n{master}\n\nJOB DESCRIPTION:\n{jd}"
    )


def tailor_resume(client: LLM, master: str, jd: str, tailor_cfg: dict) -> TailorResult:
    user = _prompt(master, jd, tailor_cfg)
    violations: list[str] = []
    for _attempt in range(2):
        if violations:
            user += "\n\nYour previous version broke these rules; fix them and return the full resume again:\n- " \
                    + "\n- ".join(violations)
        data = client.ask_json(system=SYSTEM, user=user, schema=SCHEMA)
        allowed, violations = _allowed_terms(data["added_skills"], tailor_cfg)
        violations += guard(master, data["resume_markdown"], jd, allowed)
        if not violations:
            return TailorResult(data["resume_markdown"], data["changes"], data["added_skills"],
                                data["missing_requirements"], fell_back=False, violations=[])
    return TailorResult(master, [], [], data["missing_requirements"], fell_back=True, violations=violations)
