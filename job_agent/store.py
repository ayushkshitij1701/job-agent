import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from job_agent.models import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    key        TEXT PRIMARY KEY,
    company    TEXT NOT NULL,
    title      TEXT NOT NULL,
    url        TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    status     TEXT NOT NULL,   -- notified | applied | needs_answer | apply_failed
                                -- | skipped_title | skipped_level | skipped_location | skipped_score
    score      INTEGER,
    reason     TEXT
)
"""


class Store:
    """Every job the agent has seen, so it never emails or applies twice."""

    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def seen(self, key: str) -> bool:
        return self.get(key) is not None

    def get(self, key: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE key = ?", (key,)).fetchone()
        return dict(row) if row else None

    def add(self, job: Job, status: str, score: int | None = None, reason: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO jobs (key, company, title, url, first_seen, status, score, reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET status = excluded.status, score = excluded.score, "
            "reason = excluded.reason",
            (job.key, job.company, job.title, job.url, datetime.now(timezone.utc).isoformat(),
             status, score, reason),
        )
        self.conn.commit()

    def set_status(self, key: str, status: str) -> None:
        self.conn.execute("UPDATE jobs SET status = ? WHERE key = ?", (status, key))
        self.conn.commit()

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    def close(self) -> None:
        self.conn.close()
