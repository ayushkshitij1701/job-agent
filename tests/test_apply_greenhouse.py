"""The Greenhouse filler against a local copy of the form structure, in the real (headless) Edge."""
from datetime import date

import pytest
from playwright.sync_api import sync_playwright

from job_agent.apply import greenhouse
from job_agent.apply.answers import build_answers
from job_agent.models import Job
from job_agent.render import EDGE
from tests.test_answers import APPLICANT, EDUCATION, SCREENING

pytestmark = pytest.mark.skipif(not EDGE.exists(), reason="Microsoft Edge not installed")

STRIPE = {"name": "Stripe", "source": "greenhouse", "board": "stripe"}
JOB = Job(key="Stripe:8130876", company="Stripe", title="Software Engineer, New Grad", locations=("Bengaluru",),
          url="https://stripe.com/jobs/search?gh_jid=8130876", posted="", source="greenhouse")

FORM = """<!doctype html><html><body><form>
<div><label for="first_name">First Name*</label><input id="first_name" type="text"></div>
<div><label for="last_name">Last Name*</label><input id="last_name" type="text"></div>
<div><label for="email">Email*</label><input id="email" type="email"></div>
<div><label for="phone">Phone*</label><input id="phone" type="tel"></div>
<div><label>Resume/CV*</label><div><label>Attach</label><input type="file" name="resume"></div></div>
<div><label>Cover Letter</label><div><label>Attach</label><input type="file" name="cover_letter"></div></div>
<div><label for="sex">Sex*</label><select id="sex"><option value="">Select...</option><option>Female</option><option>Male</option></select></div>
<div><label for="cc">Current Company*</label><input id="cc" type="text"></div>
<div><label for="school">School*</label><select id="school"><option value="">Select...</option><option>IIIT Bangalore</option><option>Other</option></select></div>
<fieldset><legend>When are you available to start full-time? *</legend>
  <label><input type="checkbox" value="q4">Q4 2026 (October - December)</label>
  <label><input type="checkbox" value="q1">Q1 2027 (January - March)</label></fieldset>
<div><label>Privacy Policy *</label><div><label><input type="checkbox" id="agree">I Agree</label></div></div>
<div><label for="pron">Pronouns</label><input id="pron" type="text"></div>
<div><label for="notes">Anything else?</label><textarea id="notes"></textarea></div>
{extra}
<button type="submit" onclick="document.body.innerHTML='<p>Thank you for applying!</p>'; return false;">Submit application</button>
</form></body></html>"""
UNKNOWN = '<div><label for="fav">What is your favourite programming paradigm?*</label><input id="fav" type="text"></div>'


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        yield browser.new_page()
        browser.close()


def _run(page, tmp_path, *, extra="", dry_run=False):
    html = tmp_path / "form.html"
    html.write_text(FORM.replace("{extra}", extra), encoding="utf-8")
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    answer = build_answers(APPLICANT, SCREENING, EDUCATION, today=date(2026, 11, 10))
    return greenhouse.apply(page, JOB, STRIPE, answer, pdf, dry_run=dry_run,
                            screenshot=tmp_path / "form.png", url=html.as_uri())


def test_fills_every_answerable_field_and_submits(page, tmp_path):
    result = _run(page, tmp_path)
    assert result.submitted and result.status == "applied"
    assert result.unanswered == []
    assert "First Name" in result.filled and "Resume/CV" in result.filled and "Phone" in result.filled
    assert "Sex = Male" in result.filled
    assert "School = Other" in result.filled                      # KIIT is not in the list -> "Other"
    assert "When are you available to start full-time? = Q4 2026 (October - December)" in result.filled
    assert "Privacy Policy" in result.filled
    assert set(result.skipped) >= {"Cover Letter", "Pronouns", "Anything else?"}
    assert (tmp_path / "form.png").exists()


def test_values_land_in_the_right_controls(page, tmp_path):
    _run(page, tmp_path, dry_run=True)                           # dry run leaves the form on screen
    assert page.input_value("#first_name") == "Ayush"
    assert page.input_value("#phone") == "7318367493"           # national number, country code dropped
    assert page.input_value("#cc") == "Acies"
    assert page.input_value("#sex") == "Male"
    assert page.is_checked("#agree")
    assert page.is_checked("input[value=q4]") and not page.is_checked("input[value=q1]")
    assert page.input_value("#pron") == ""


def test_required_question_without_an_answer_blocks_submission(page, tmp_path):
    result = _run(page, tmp_path, extra=UNKNOWN)
    assert not result.submitted and result.status == "needs_answer"
    assert result.unanswered == ["What is your favourite programming paradigm?"]
    assert "Thank you" not in page.locator("body").inner_text()


def test_dry_run_fills_but_never_submits(page, tmp_path):
    result = _run(page, tmp_path, dry_run=True)
    assert not result.submitted and result.dry_run and result.status == "notified"
    assert "Thank you" not in page.locator("body").inner_text()
    assert (tmp_path / "form.png").exists()
