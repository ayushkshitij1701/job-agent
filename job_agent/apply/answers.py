"""Fixed answers for application-form questions, chosen by what the question's label says.
Pure logic (no browser): `build_answers(...)` returns `answer(label) -> value | SKIP | CHECK | None`,
and `pick_option(options, value)` maps a value onto a dropdown's actual option text.
None means "no rule": the filler leaves an optional field empty and reports a required one as unanswered."""
import re
from datetime import date, timedelta

SKIP = "<skip>"     # optional by design: leave empty even if the form would accept something
CHECK = "<check>"   # consent / agreement checkbox: tick it


def build_answers(applicant: dict, screening: dict, education: dict | None = None, today: date | None = None):
    today = today or date.today()
    edu = education or {}
    start = today + timedelta(days=screening["notice_period_days"])
    rules: list[tuple[str, str | None]] = [
        (r"preferred name|pronoun|if you selected other|if yes|offer deadline|conference|anything else|additional information|comments|sat or act|test score", SKIP),
        (r"first name|given name", applicant["first_name"]),
        (r"last name|surname|family name", applicant["last_name"]),
        (r"\bemail", applicant["email"]),
        (r"phone|mobile", applicant["phone"]),
        (r"linkedin", applicant["linkedin"]),
        (r"github|portfolio|website", applicant["github"]),
        (r"\bi agree\b|consent|acknowledge|privacy|terms|confidential|certify", CHECK),
        (r"currently work for|previously worked|former employee|procurement|contract award|relative|related to", "No"),
        (r"sponsorship|work permit|\bvisa\b", applicant["needs_sponsorship"]),
        (r"legal(ly)? (right|authori[sz]ed)|eligible to work|authori[sz]ed to work|right to work", applicant["work_authorized"]),
        (r"how did you (learn|hear)|how you (learned|heard)|\bsource\b", applicant["heard_about_us"]),
        (r"current (company|employer)|previous employer|\bemployer\b", applicant["current_company"]),
        (r"(current|job) title", applicant["current_title"]),
        (r"years? of .*experience|experience.*years", str(applicant["years_experience"])),
        (r"notice period", f"{screening['notice_period_days']} days"),
        (r"current (ctc|salary|compensation)", f"{screening['current_ctc_lpa']} LPA"),
        (r"expected (ctc|salary|compensation)", f"{screening['expected_ctc']['preferred_lpa']} LPA"),
        (r"relocat", "Yes" if screening.get("willing_to_relocate", True) else "No"),
        (r"available to start|start date|earliest|when can you (start|join)|joining date|availability", start.isoformat()),
        (r"\bsex\b|gender", applicant["gender"]),
        (r"disabilit", applicant["disability"]),
        (r"veteran", applicant["veteran"]),
        (r"ethnic|\brace\b|hispanic|latino", "Decline"),
        (r"\bgpa\b|cgpa|grade point", edu.get("gpa")),
        (r"school|university|college|institution", edu.get("school")),
        (r"degree", edu.get("degree")),
        (r"discipline|major|field of study", edu.get("discipline")),
        (r"graduat", edu.get("end_year")),
        (r"home address|street|postal|zip|pin ?code", applicant.get("address") or None),
        (r"country", "India"),
        (r"\bcity\b|location|residence|reside|where (are you|do you) (based|live)", applicant["location"]),
    ]
    compiled = [(re.compile(p, re.I), v) for p, v in rules]

    def answer(label: str):
        text = label.replace("*", " ")
        for pattern, value in compiled:
            if pattern.search(text):
                return None if value is None else str(value)
        return None

    return answer


def pick_option(options: list[str], wanted: str) -> str | None:
    """The option text that best matches `wanted`, or None."""
    w = wanted.strip().lower()
    if not w:
        return None
    lowered = [(o, o.strip().lower()) for o in options if o.strip()]
    for o, lo in lowered:
        if lo == w:
            return o
    if w in ("yes", "no"):                              # "No" must not match "...sponsorship now..."
        return next((o for o, lo in lowered if re.match(rf"{w}\b", lo)), None)
    for o, lo in lowered:                               # "Goa, India" over "Old Goa, Goa, India"
        if len(w) >= 3 and lo.startswith(w):
            return o
    for o, lo in lowered:                               # whole-word containment either way
        if lo.startswith("select"):
            continue
        if (len(w) >= 3 and re.search(rf"\b{re.escape(w)}\b", lo)) or (len(lo) >= 4 and re.search(rf"\b{re.escape(lo)}\b", w)):
            return o
    if w == "decline":
        return next((o for o, lo in lowered if re.search(r"decline|prefer not|do not wish|rather not", lo)), None)
    m = re.match(r"(\d{4})-(\d{2})-\d{2}$", w)
    if m:                                               # a date against quarter / month labels
        year, month = m.group(1), int(m.group(2))
        quarter = f"q{(month - 1) // 3 + 1} {year}"
        month_name = date(int(year), month, 1).strftime("%B").lower()
        return next((o for o, lo in lowered if quarter in lo or (month_name in lo and year in lo)), None)
    words = {t for t in re.findall(r"[a-z]{4,}", w)}     # last resort: share a meaningful word ("careers site" ~ "Company Website")
    scored = [(len(words & set(re.findall(r"[a-z]{4,}", lo))), o) for o, lo in lowered]
    best = max(scored, default=(0, None))
    return best[1] if best[0] else None
