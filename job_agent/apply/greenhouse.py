"""Greenhouse job-board application form. Hosted boards and the forms companies embed on their own
sites both serve https://job-boards.greenhouse.io/embed/job_app?for={board}&token={job id}.

Walks every question container (a <fieldset>, or a <div> whose direct child is a <label>), picks the
answer from the label text, fills text/select/react-select/checkbox/file controls, and submits only
when every required question got an answer. Controls already handled are stamped so a nested
container (Greenhouse wraps the file "Attach" button in its own labelled div) is not filled twice."""
import re
from pathlib import Path

from job_agent.apply.answers import CHECK, SKIP, pick_option
from job_agent.apply.base import ApplyResult
from job_agent.models import Job

NAME = "greenhouse"
EMBED = "https://job-boards.greenhouse.io/embed/job_app"
CONFIRMED = re.compile(r"thank you|application (has been|was) (submitted|received)|we('ve| have) received", re.I)
SCHOOL = re.compile(r"school|university|college|institution", re.I)
DONE = "data-job-agent"
NOT_DONE = f":not([{DONE}])"
CONTROLS = ", ".join(f"{sel}{NOT_DONE}" for sel in
                     ("input:not([type=hidden])", "textarea", "[role=combobox]", "select"))


def form_url(company: dict, job: Job) -> str:
    return f"{EMBED}?for={company['board']}&token={job.key.split(':', 1)[1]}"


def apply(page, job: Job, company: dict, answer, resume_pdf: Path, *, dry_run: bool,
          screenshot: Path | None = None, url: str | None = None) -> ApplyResult:
    page.goto(url or form_url(company, job), wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    result = ApplyResult(dry_run=dry_run)
    containers = page.locator("fieldset, div:has(> label)")
    for i in range(containers.count()):
        box = containers.nth(i)
        if box.locator(CONTROLS).count() == 0:
            continue
        question = _clean(box.locator("legend, label").first.inner_text())
        if not question or question in ("Attach", "Enter manually"):
            continue
        try:
            _fill(page, box, question, answer, resume_pdf, result)
        except Exception as e:          # one odd widget must not stop the rest; it is reported, not submitted
            result.unanswered.append(f"{question} (could not fill: {type(e).__name__})")
        _stamp(box)
    if screenshot:
        page.screenshot(path=str(screenshot), full_page=True)
    if result.unanswered or dry_run:
        return result
    page.get_by_role("button", name=re.compile("submit", re.I)).first.click()
    try:
        page.get_by_text(CONFIRMED).first.wait_for(timeout=30000)
        result.submitted = True
    except Exception:
        result.error = "no confirmation after submit; page says: " + _clean(page.locator("body").inner_text())[:300]
    return result


def _fill(page, box, question: str, answer, resume_pdf: Path, result: ApplyResult) -> None:
    required = "*" in question
    q = question.replace("*", "").strip()
    files = box.locator(f"input[type=file]{NOT_DONE}")
    if files.count():
        name = (files.first.get_attribute("name") or q).lower()
        if "resume" in name or "cv" in name:
            files.first.set_input_files(str(resume_pdf))
            result.filled.append(q)
        else:
            result.skipped.append(q)                     # cover letter and other uploads stay empty
        return
    value = answer(q)
    tel = box.locator(f"input[type=tel]{NOT_DONE}")
    combos = box.locator(f"[role=combobox]{NOT_DONE}")
    checks = box.locator(f"input[type=checkbox]{NOT_DONE}, input[type=radio]{NOT_DONE}")
    selects = box.locator(f"select{NOT_DONE}")
    areas = box.locator(f"textarea{NOT_DONE}")
    texts = box.locator(", ".join(f"input[type={t}]{NOT_DONE}" for t in ("text", "email", "url", "number"))
                        + f", input:not([type]){NOT_DONE}")
    if tel.count():                                      # phone = country picker + national number
        if combos.count():
            _choose_combo(page, combos.first, "India")
        digits = re.sub(r"\D", "", value or "")
        tel.first.fill(digits[-10:] if len(digits) > 10 else digits)
        result.filled.append(q)
        return
    if value == SKIP:
        result.skipped.append(q)
        return
    if checks.count():
        labels = [_clean(t) for t in _check_labels(checks)]
        if value == CHECK:
            for k in range(checks.count()):
                checks.nth(k).check()
            result.filled.append(q)
        elif value and (pick := pick_option(labels, value)):
            checks.nth(labels.index(pick)).check()
            result.filled.append(f"{q} = {pick}")
        elif required:
            result.unanswered.append(_with_options(q, labels))
        return
    fallback = "Other" if SCHOOL.search(q) else None     # curated school lists: "Other" + the name in the next field
    if combos.count():
        pick = _choose_combo(page, combos.first, value, fallback) if value else None
        if pick:
            result.filled.append(f"{q} = {pick}")
        elif required:
            result.unanswered.append(q if not value else f"{q} (no option matching '{value}')")
        return
    if selects.count():
        options = selects.first.evaluate("el => [...el.options].map(o => o.text)")
        pick = (pick_option(options, value) or (fallback and pick_option(options, fallback))) if value else None
        if pick:
            selects.first.select_option(label=pick)
            result.filled.append(f"{q} = {pick}")
        elif required:
            result.unanswered.append(_with_options(q, options))
        return
    target = areas.first if areas.count() else texts.first if texts.count() else None
    if target is None:
        return
    if value and value != CHECK:
        target.fill(value)
        result.filled.append(q)
    elif required:
        result.unanswered.append(q)


def _choose_combo(page, combo, wanted: str, fallback: str | None = None) -> str | None:
    """react-select: open, read the visible options, click the best match. Long or autocomplete lists
    are searched by typing — the full value first, then just its first word, since react-select hides
    every option that does not contain the typed text ("Bachelor of Technology" vs "Bachelor's Degree").
    `fallback` (e.g. "Other") is chosen when nothing matches."""
    combo.click()
    page.wait_for_timeout(300)
    options = _visible_options(page)
    pick = pick_option(options, wanted) if 0 < len(options) <= 40 else None
    if not pick:
        first_word = re.match(r"[A-Za-z0-9]+", wanted)
        queries = [wanted[:30], first_word.group(0) if first_word else wanted[:10]]
        for query, target in [(qu, wanted) for qu in dict.fromkeys(queries)] + ([(fallback, fallback)] if fallback else []):
            combo.fill("")
            combo.press_sequentially(query, delay=15)
            page.wait_for_timeout(2500)                  # autocomplete lists fetch over the network
            options = _visible_options(page)
            pick = pick_option(options, target)
            if pick:
                break
    if pick:
        page.locator("[role=option]:visible").filter(has_text=re.compile(rf"^\s*{re.escape(pick)}\s*$")).first.click()
    else:
        page.keyboard.press("Escape")
    return pick


def _visible_options(page) -> list[str]:
    return [_clean(t) for t in page.locator("[role=option]:visible").all_inner_texts()]


def _check_labels(checks) -> list[str]:
    return [c.evaluate("el => (el.closest('label') || (el.id && document.querySelector(`label[for=\"${el.id}\"]`)) || {innerText: ''}).innerText")
            for c in checks.all()]


def _with_options(q: str, options: list[str]) -> str:
    shown = [o for o in options if o and not o.lower().startswith("select")][:8]
    return f"{q} (options: {', '.join(shown)})" if shown else q


def _stamp(box) -> None:
    box.locator(CONTROLS).evaluate_all(f"els => els.forEach(e => e.setAttribute('{DONE}', '1'))")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()
