import smtplib

from job_agent import notify
from job_agent.models import Job
from job_agent.tailor import TailorResult


class FakeSMTP:
    sent = []
    logins = []

    def __init__(self, host, port):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def login(self, user, password):
        FakeSMTP.logins.append((user, password))

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


def test_send_email_uses_gmail_ssl_and_attaches_files(tmp_path, monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setenv("SMTP_USER", "me@gmail.com")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "app-pw")
    md = tmp_path / "resume.md"
    md.write_text("# r", encoding="utf-8")
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    notify.send_email("me@gmail.com", "subject", "body", [md, pdf])

    assert FakeSMTP.logins[-1] == ("me@gmail.com", "app-pw")
    msg = FakeSMTP.sent[-1]
    assert msg["Subject"] == "subject"
    assert msg["To"] == "me@gmail.com"
    names = [part.get_filename() for part in msg.iter_attachments()]
    assert names == ["resume.md", "resume.pdf"]


def test_compose_match_email_lists_everything_you_need():
    job = Job(key="Salesforce:JR1", company="Salesforce", title="Software Engineer", locations=("India - Bangalore",),
              url="https://sf.example/job/1", posted="Posted Today", source="workday")
    result = TailorResult(resume_md="# r", changes=["moved FastAPI bullet first"],
                          added_skills=[{"term": "Redshift", "via": "category: any SQL database or dialect"}],
                          missing_requirements=["Kubernetes"], fell_back=False, violations=[])
    subject, body = notify.compose_match_email(job, 82, "strong backend match", result,
                                               referral_note="Ask Yash first.")
    assert subject == "[job-agent] Salesforce: Software Engineer (score 82)"
    for expected in ("https://sf.example/job/1", "India - Bangalore", "strong backend match",
                     "moved FastAPI bullet first", "Redshift", "any SQL database or dialect",
                     "Kubernetes", "Ask Yash first."):
        assert expected in body


def test_compose_match_email_says_when_tailoring_fell_back():
    job = Job(key="k", company="Cisco", title="SDE", locations=(), url="u", posted="", source="s")
    result = TailorResult(resume_md="# r", changes=[], added_skills=[], missing_requirements=[],
                          fell_back=True, violations=["new technology: Kubernetes"])
    _, body = notify.compose_match_email(job, 70, "ok", result, referral_note=None)
    assert "master resume attached unchanged" in body
    assert "Kubernetes" in body
