import json

from job_agent.tailor import TailorResult, guard, tailor_resume

MASTER = """# Ayush Kshitij

Software Engineer with 1.5+ years of experience.

## Experience

### Software Engineer — Acies, Goa, India
- Built a data platform (FastAPI, Polars) for 5+ formats (Excel/CSV, PDF).
- Integrated AWS S3 and PostgreSQL with 12 authentication methods.

## Skills
- **Languages:** Python, Java, SQL
- **Frameworks & Tools:** React, Node.js, LangChain
"""

TAILOR_CFG = {
    "skills_allowed_to_add": {
        "exact": ["Flask", "Redis", "Apache Spark"],
        "categories": ["any SQL database or dialect"],
    }
}


def test_guard_passes_unchanged_resume():
    assert guard(MASTER, MASTER, jd="", allowed_terms=[]) == []


def test_guard_allows_reorder_and_rewording_with_plain_words():
    tailored = MASTER.replace("Built a data platform", "Delivered a scalable data platform")
    assert guard(MASTER, tailored, jd="", allowed_terms=[]) == []


def test_guard_rejects_new_technology():
    tailored = MASTER.replace("Python, Java, SQL", "Python, Java, SQL, Kubernetes")
    violations = guard(MASTER, tailored, jd="", allowed_terms=[])
    assert any("Kubernetes" in v for v in violations)


def test_guard_rejects_new_numbers():
    tailored = MASTER.replace("for 5+ formats", "for 5+ formats, cutting latency by 35%")
    violations = guard(MASTER, tailored, jd="", allowed_terms=[])
    assert any("35%" in v for v in violations)


def test_guard_allows_jd_term_that_is_a_form_of_a_master_term():
    tailored = MASTER.replace("PostgreSQL", "Postgres")
    assert guard(MASTER, tailored, jd="Experience with Postgres required", allowed_terms=[]) == []
    assert guard(MASTER, tailored, jd="unrelated", allowed_terms=[]) != []


def test_guard_allows_allowlisted_terms():
    tailored = MASTER.replace("React, Node.js", "React, Node.js, Flask, Apache Spark")
    assert guard(MASTER, tailored, jd="", allowed_terms=["Flask", "Apache Spark"]) == []


def test_guard_ignores_sentence_and_bullet_starts():
    tailored = MASTER.replace("- Integrated AWS S3", "- Shipped AWS S3")
    assert guard(MASTER, tailored, jd="", allowed_terms=[]) == []


class FakeClient:
    """Implements the LLM interface: returns queued payloads from ask_json and records the prompts sent."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.requests = []

    def ask_json(self, *, system, user, schema):
        self.requests.append({"system": system, "user": user, "schema": schema})
        return json.loads(json.dumps(self._payloads.pop(0)))


def _payload(resume, added=None, missing=None):
    return {"resume_markdown": resume, "changes": ["reordered skills"],
            "added_skills": added or [], "missing_requirements": missing or []}


def test_tailor_accepts_clean_output_with_category_addition():
    tailored = MASTER.replace("Python, Java, SQL", "Python, Java, SQL, Redshift")
    client = FakeClient([_payload(tailored, added=[{"term": "Redshift", "via": "category: any SQL database or dialect"}])])
    result = tailor_resume(client, MASTER, "Redshift experience", TAILOR_CFG)
    assert isinstance(result, TailorResult)
    assert result.resume_md == tailored
    assert result.fell_back is False
    assert result.added_skills == [{"term": "Redshift", "via": "category: any SQL database or dialect"}]
    assert len(client.requests) == 1


def test_tailor_retries_once_then_falls_back_to_master():
    bad = MASTER.replace("Python, Java, SQL", "Python, Java, SQL, Kubernetes")
    client = FakeClient([_payload(bad), _payload(bad)])
    result = tailor_resume(client, MASTER, "Kubernetes required", TAILOR_CFG)
    assert result.fell_back is True
    assert result.resume_md == MASTER
    assert any("Kubernetes" in v for v in result.violations)
    assert len(client.requests) == 2
    assert "Kubernetes" in client.requests[1]["user"]   # violations fed back


def test_tailor_rejects_addition_via_unknown_category():
    tailored = MASTER.replace("Python, Java, SQL", "Python, Java, SQL, Kubernetes")
    bad = _payload(tailored, added=[{"term": "Kubernetes", "via": "category: any container platform"}])
    client = FakeClient([bad, bad])
    result = tailor_resume(client, MASTER, "k8s", TAILOR_CFG)
    assert result.fell_back is True
