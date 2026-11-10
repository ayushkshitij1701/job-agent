from job_agent.matcher import score_job
from job_agent.models import Job
from tests.test_tailor import FakeClient


def test_score_job_sends_resume_as_system_and_job_as_user():
    client = FakeClient([{"score": 78, "reason": "Python and FastAPI match"}])
    job = Job(key="Cisco:1", company="Cisco", title="Software Engineer", locations=("Bangalore",),
              url="u", posted="", source="workday", description="Python, FastAPI, 2+ years")
    score, reason = score_job(client, "# Resume\nPython", job)
    assert (score, reason) == (78, "Python and FastAPI match")
    req = client.requests[0]
    assert "# Resume" in req["system"]
    assert "FastAPI, 2+ years" in req["user"]
    assert req["schema"]["required"] == ["score", "reason"]


def test_score_job_tells_the_scorer_the_target_level():
    client = FakeClient([{"score": 10, "reason": "x"}])
    job = Job(key="k", company="Amazon", title="SDE", locations=(), url="u", posted="", source="s")
    score_job(client, "r", job, {"max_level": 1, "level_2_ok_at": ["Microsoft", "Salesforce"]})
    system = client.requests[0]["system"]
    assert "SDE-1" in system and "except at Microsoft, Salesforce" in system
    assert "Not internships" in system and "6 months" in system


def test_score_job_without_roles_config_adds_no_level_note():
    client = FakeClient([{"score": 10, "reason": "x"}])
    job = Job(key="k", company="c", title="t", locations=(), url="u", posted="", source="s")
    score_job(client, "r", job)
    assert "TARGET LEVEL" not in client.requests[0]["system"]


def test_score_job_clamps_to_0_100():
    client = FakeClient([{"score": 140, "reason": "x"}])
    job = Job(key="k", company="c", title="t", locations=(), url="u", posted="", source="s")
    assert score_job(client, "r", job)[0] == 100
