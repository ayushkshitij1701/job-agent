from job_agent.models import Job
from job_agent.store import Store


def make_job(key="Cisco:123"):
    return Job(key=key, company="Cisco", title="Software Engineer", locations=("Bangalore",),
               url="https://example.com/j/123", posted="2026-11-07", source="workday")


def test_add_then_seen_and_get(tmp_path):
    store = Store(tmp_path / "jobs.db")
    assert not store.seen("Cisco:123")
    store.add(make_job(), status="notified", score=82, reason="strong Python match")
    assert store.seen("Cisco:123")
    row = store.get("Cisco:123")
    assert row["status"] == "notified"
    assert row["score"] == 82
    assert row["reason"] == "strong Python match"
    assert row["title"] == "Software Engineer"
    assert row["first_seen"]


def test_set_status_and_persistence_across_instances(tmp_path):
    path = tmp_path / "jobs.db"
    Store(path).add(make_job(), status="skipped_title")
    store = Store(path)
    store.set_status("Cisco:123", "notified")
    assert store.get("Cisco:123")["status"] == "notified"
    assert store.get("missing") is None


def test_add_same_key_twice_keeps_one_row(tmp_path):
    store = Store(tmp_path / "jobs.db")
    store.add(make_job(), status="skipped_score", score=40)
    store.add(make_job(), status="notified", score=90)
    assert store.count() == 1
    assert store.get("Cisco:123")["status"] == "notified"
