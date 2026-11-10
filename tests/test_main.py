import json

import yaml

from job_agent import main
from job_agent.models import Job
from job_agent.store import Store
from tests.test_tailor import FakeClient

RESUME = "# Ayush\n\n## Skills\n- Python, FastAPI\n"


def _config(tmp_path):
    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    cfg["db_path"] = str(tmp_path / "jobs.db")
    cfg["out_dir"] = str(tmp_path / "out")
    cfg["resume_path"] = str(tmp_path / "resume.md")
    (tmp_path / "resume.md").write_text(RESUME, encoding="utf-8")
    cfg["companies"]["referral"] = [{"name": "Cisco", "source": "fake"}]
    return cfg


def _job(key, title, locations=("Bangalore, India",)):
    return Job(key=key, company="Cisco", title=title, locations=locations, url=f"https://x/{key}",
               posted="today", source="fake")


class FakeSource:
    NAME = "fake"

    def __init__(self, jobs, description="Python FastAPI role"):
        self._jobs, self._description = jobs, description
        self.enriched = []

    def fetch(self, company, session):
        return list(self._jobs)

    def enrich(self, job, company, session):
        self.enriched.append(job.key)
        return job.with_(description=self._description)


def _tailored(resume):
    return {"resume_markdown": resume, "changes": ["none"], "added_skills": [], "missing_requirements": []}


def test_run_notifies_on_match_and_skips_the_rest(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    source = FakeSource([
        _job("Cisco:1", "Software Engineer"),
        _job("Cisco:2", "Account Executive"),
        _job("Cisco:3", "Software Engineer", locations=("Austin, US",)),
        _job("Cisco:4", "SDE I"),
    ])
    monkeypatch.setattr(main, "SOURCES", {"fake": source})
    client = FakeClient([
        {"score": 85, "reason": "great"}, _tailored(RESUME),      # Cisco:1 -> notified
        {"score": 20, "reason": "weak"},                           # Cisco:4 -> skipped_score
    ])
    sent = []
    monkeypatch.setattr(main, "html_to_pdf", lambda html, pdf: pdf.write_bytes(b"%PDF"))

    notified = main.run(cfg, client=client, session=None, send=lambda *a: sent.append(a))

    assert [j.key for j in notified] == ["Cisco:1"]
    assert source.enriched == ["Cisco:1", "Cisco:3", "Cisco:4"]          # title-filtered before enrich
    store = Store(tmp_path / "jobs.db")
    assert store.get("Cisco:1")["status"] == "notified"
    assert store.get("Cisco:2")["status"] == "skipped_title"
    assert store.get("Cisco:3")["status"] == "skipped_location"
    assert store.get("Cisco:4")["status"] == "skipped_score"
    to, subject, body, attachments = sent[0]
    assert to == cfg["notify"]["to"]
    assert "Cisco: Software Engineer (score 85)" == subject.removeprefix("[job-agent] ")
    assert [p.name for p in attachments] == ["resume.md", "resume.pdf"]
    assert attachments[0].read_text(encoding="utf-8") == RESUME
    assert (tmp_path / "out" / "Cisco_1" / "job.json").exists()
    assert json.loads((tmp_path / "out" / "Cisco_1" / "job.json").read_text())["title"] == "Software Engineer"


def test_run_handles_auto_apply_companies_like_referral_until_apply_exists(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    cfg["companies"]["referral"] = []
    cfg["companies"]["auto_apply"] = [{"name": "Cisco", "source": "fake"}]      # _job() uses company Cisco
    monkeypatch.setattr(main, "SOURCES", {"fake": FakeSource([_job("Cisco:1", "Software Engineer")])})
    monkeypatch.setattr(main, "html_to_pdf", lambda html, pdf: pdf.write_bytes(b"%PDF"))
    sent = []
    notified = main.run(cfg, client=FakeClient([{"score": 90, "reason": "fit"}, _tailored(RESUME)]),
                        session=None, send=lambda *a: sent.append(a))
    assert [j.key for j in notified] == ["Cisco:1"]
    assert main.AUTO_APPLY_NOTE in sent[0][2]


def test_run_applies_when_the_backend_has_an_applier(tmp_path, monkeypatch):
    from job_agent.apply.base import ApplyResult
    cfg = _config(tmp_path)
    cfg["companies"]["referral"] = []
    cfg["companies"]["auto_apply"] = [{"name": "Cisco", "source": "fake"}]
    monkeypatch.setattr(main, "SOURCES", {"fake": FakeSource([_job("Cisco:1", "Software Engineer")])})
    monkeypatch.setattr(main, "html_to_pdf", lambda html, pdf: pdf.write_bytes(b"%PDF"))
    monkeypatch.setattr(main, "can_apply", lambda company: True)
    calls = []

    def fake_apply(job, company, cfg_, pdf, folder):
        calls.append((job.key, pdf.name, folder.name))
        return ApplyResult(submitted=True, filled=["First Name"])

    monkeypatch.setattr(main, "apply_job", fake_apply)
    sent = []
    main.run(cfg, client=FakeClient([{"score": 90, "reason": "fit"}, _tailored(RESUME)]),
             session=None, send=lambda *a: sent.append(a))
    assert calls == [("Cisco:1", "resume.pdf", "Cisco_1")]
    assert sent[0][1].startswith("[job-agent] APPLIED: ")
    assert main.AUTO_APPLY_NOTE not in sent[0][2]
    assert Store(tmp_path / "jobs.db").get("Cisco:1")["status"] == "applied"


def test_run_skips_sde2_titles_outside_the_allowed_companies(tmp_path, monkeypatch):
    cfg = _config(tmp_path)                                               # company is Cisco: SDE-1 only
    source = FakeSource([_job("Cisco:1", "Software Engineer II"), _job("Cisco:2", "Senior Software Engineer")])
    monkeypatch.setattr(main, "SOURCES", {"fake": source})
    notified = main.run(cfg, client=FakeClient([]), session=None, send=lambda *a: None)
    assert notified == []
    assert source.enriched == []                                          # filtered before enrich
    store = Store(tmp_path / "jobs.db")
    assert store.get("Cisco:1")["status"] == "skipped_level"
    assert store.get("Cisco:2")["status"] == "skipped_level"


def test_run_skips_jobs_already_seen(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    Store(tmp_path / "jobs.db").add(_job("Cisco:1", "Software Engineer"), status="notified")
    source = FakeSource([_job("Cisco:1", "Software Engineer")])
    monkeypatch.setattr(main, "SOURCES", {"fake": source})
    client = FakeClient([])
    notified = main.run(cfg, client=client, session=None, send=lambda *a: None)
    assert notified == []
    assert source.enriched == []


def test_run_continues_when_one_job_fails_to_render(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    source = FakeSource([_job("Cisco:1", "Software Engineer"), _job("Cisco:2", "Software Engineer")])
    monkeypatch.setattr(main, "SOURCES", {"fake": source})
    client = FakeClient([{"score": 85, "reason": "a"}, _tailored(RESUME),
                         {"score": 85, "reason": "b"}, _tailored(RESUME)])
    pdfs = []

    def flaky_pdf(html, pdf):
        pdfs.append(pdf)
        if len(pdfs) == 1:
            raise RuntimeError("edge hung")
        pdf.write_bytes(b"%PDF")

    monkeypatch.setattr(main, "html_to_pdf", flaky_pdf)
    sent = []
    notified = main.run(cfg, client=client, session=None, send=lambda *a: sent.append(a))
    assert [j.key for j in notified] == ["Cisco:2"]
    assert len(sent) == 1
    store = Store(tmp_path / "jobs.db")
    assert not store.seen("Cisco:1")                      # retried next run
    assert store.get("Cisco:2")["status"] == "notified"


def test_run_continues_when_scoring_one_job_fails(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    source = FakeSource([_job("Cisco:1", "Software Engineer"), _job("Cisco:2", "Software Engineer")])
    monkeypatch.setattr(main, "SOURCES", {"fake": source})

    class TimesOutOnce(FakeClient):
        def ask_json(self, **kw):
            if not self.requests:
                self.requests.append(kw)
                raise TimeoutError("ollama read timed out")
            return super().ask_json(**kw)

    client = TimesOutOnce([{"score": 20, "reason": "weak"}])
    notified = main.run(cfg, client=client, session=None, send=lambda *a: None)
    assert notified == []
    store = Store(tmp_path / "jobs.db")
    assert not store.seen("Cisco:1")                      # retried next run
    assert store.get("Cisco:2")["status"] == "skipped_score"


def _llm_cfg():
    return {"provider": "ollama", "ollama": {"model": "qwen3.5:9b", "think": False}, "gemini": {"model": "gemini-3.8-flash"}}


def test_cli_no_flags_keeps_config():
    assert main.apply_llm_overrides(_llm_cfg(), main.parse_args([])) == _llm_cfg()


def test_cli_model_and_think_override_current_provider():
    llm = main.apply_llm_overrides(_llm_cfg(), main.parse_args(["--model", "qwen3.5:4b", "--think"]))
    assert llm["provider"] == "ollama"
    assert llm["ollama"] == {"model": "qwen3.5:4b", "think": True}
    assert llm["gemini"]["model"] == "gemini-3.8-flash"


def test_cli_provider_switch_applies_model_to_that_provider():
    args = main.parse_args(["--provider", "gemini", "--model", "gemini-3.6-flash", "--no-think"])
    llm = main.apply_llm_overrides(_llm_cfg(), args)
    assert llm["provider"] == "gemini"
    assert llm["gemini"]["model"] == "gemini-3.6-flash"
    assert llm["ollama"] == {"model": "qwen3.5:9b", "think": False}


def test_run_leaves_job_unseen_when_enrich_fails(tmp_path, monkeypatch):
    cfg = _config(tmp_path)

    class BrokenSource(FakeSource):
        def enrich(self, job, company, session):
            raise RuntimeError("503")

    monkeypatch.setattr(main, "SOURCES", {"fake": BrokenSource([_job("Cisco:1", "Software Engineer")])})
    notified = main.run(cfg, client=FakeClient([]), session=None, send=lambda *a: None)
    assert notified == []
    assert not Store(tmp_path / "jobs.db").seen("Cisco:1")      # retried next run
