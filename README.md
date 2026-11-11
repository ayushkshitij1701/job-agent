# job-agent

Finds new software-engineering openings on company career sites, scores each one against `resume.md`,
tailors a copy of the resume to the job description, and either emails you the result or applies for you.

- **Group A — referral companies** (`companies.referral`): you get an email with the tailored CV (`.md` + `.pdf`)
  and a reminder to get the referral; you apply yourself.
- **Group B — auto-apply companies** (`companies.auto_apply`): the agent fills and submits the application form
  where the career site allows it (Greenhouse today), then emails you what it did. Other backends email you the
  tailored CV with an "apply yourself" note.

Design and decisions: `PLAN.md`. Research behind the Group B list (backend, pay, standing per company): `COMPANIES.md`.

## Setup (once)

```powershell
cd C:\Source\Repos\job-agent
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # then fill in SMTP_APP_PASSWORD (and GEMINI_API_KEY if you use Gemini)
```

- `.env` holds the secrets and is git-ignored: `SMTP_USER` / `SMTP_APP_PASSWORD` (a Gmail app password:
  Google account → Security → 2-Step Verification → App passwords) and `GEMINI_API_KEY` (Google AI Studio →
  Get API key; only for the Gemini provider).
- Local model: install Ollama (ollama.com), then `ollama pull qwen3.5:9b`.
- Browser automation (PDF rendering and auto-apply) drives the Microsoft Edge already on the machine through
  Playwright (`channel="msedge"`, headless) — no `playwright install` / Chromium download.

## Run

```powershell
.venv\Scripts\python -m job_agent.main
```

Flags override `config.yaml` for that run only:

```powershell
.venv\Scripts\python -m job_agent.main --model qwen3.5:4b              # another Ollama model
.venv\Scripts\python -m job_agent.main --think                         # Qwen reasons first (slower)
.venv\Scripts\python -m job_agent.main --provider gemini               # Gemini with its config model
.venv\Scripts\python -m job_agent.main --provider gemini --model gemini-3.6-flash
```

Each run only looks at jobs it has not seen before (tracked in `jobs.db`, one row per job with its status).
Per match it writes `out\<Company>_<id>\resume.md`, `resume.pdf`, `job.json` (and `form.png` when a form was
filled) and sends one email. The first run is big (every current opening); later runs only see new postings.

## What a run does

```
fetch listings (every company in config) → drop already-seen → title filter → level filter → fetch the JD
  → location filter → score vs resume (0-100) → score ≥ match.min_score → tailor the CV → PDF
      Group A, or Group B without a form filler → email: job, score, tailored CV, referral / apply-yourself note
      Group B with a form filler → fill + submit the application → email: what was answered, form.png
```

Career-site backends with a fetcher: Workday, SmartRecruiters, Greenhouse, Oracle HCM, Microsoft (Eightfold),
Amazon. A company on any other backend is skipped with a log warning until its fetcher is written.

## Configuration (`config.yaml`)

| Block | What it controls |
|---|---|
| `llm` | `provider: ollama \| gemini` and each provider's model. Ollama `think: false` skips the reasoning chain (~4 s vs ~55 s per call, same scores in our tests). |
| `notify.to` | where the emails go |
| `roles` | title words to include/exclude; `max_level: 1` keeps SDE-1 titles only (`SDE II`, `Engineer 2` = level 2, `Senior`/`III`/`Lead` = 3), `level_2_ok_at` lists the companies where SDE-2 titles pass |
| `locations` | cities in priority order, whether India-remote counts |
| `match.min_score` | fit score needed to act on a job |
| `tailor.skills_allowed_to_add` | the only skills the tailoring step may add to the CV (exact terms, or categories such as "any SQL database") |
| `screening`, `applicant`, `education` | answers used on application forms: notice period, CTC, work authorisation, contact details, address, school/degree |
| `apply.dry_run` | `true` = fill the form and attach `form.png`, never submit; set `false` to let it submit |
| `companies.referral` / `companies.auto_apply` | the two groups, each entry with its backend ids |

`resume.md` is the master resume and is never edited; every job gets its own tailored copy under `out\`.
The tailoring step may reorder and reword, and may add only skills from `tailor.skills_allowed_to_add` when
the JD asks for them; a code guard rejects any other new claim, number or technology.

## Choosing the model

- `ollama` (default) — a local model on your GPU, `qwen3.5:9b`. Ollama runs as a background service after
  install; the model sits in VRAM only while in use and is unloaded a few minutes after the last request.
- `gemini` — Google's API, `gemini-3.8-flash` (free tier), needs `GEMINI_API_KEY`.

Adding another provider = one new class in `job_agent/llm/` (request/response shape only) plus one line in
`job_agent/llm/__init__.py`. Nothing else changes.

## Auto-apply (Group B)

For a Group B company whose backend has a form filler (today: Greenhouse — Stripe, Twilio, Zscaler, Commvault,
Databricks, Rubrik, MongoDB, Razorpay, Groww), a match is tailored, then the agent opens the application form in
headless Edge, fills it from `applicant`, `screening` and `education`, uploads the tailored PDF, and submits.
The email subject says what happened:

- `APPLIED:` submitted; the body lists every answer given.
- `NEEDS YOUR ANSWER:` the form asked something not in config — nothing was submitted; apply yourself, or add
  the answer to config (the job is not retried automatically).
- `APPLY FAILED:` the site did not confirm the submission (bot check, changed form); apply yourself.
- `DRY RUN:` `apply.dry_run` is true — filled, `form.png` attached, not submitted.

Start with `apply.dry_run: true`, look at a couple of `form.png`, then set it to `false`.
Not automatic yet: SmartRecruiters (its apply page is behind a DataDome bot check that blocks headless browsers),
Workday (needs an account per company), and the custom career sites — those email you the tailored CV instead.

## Schedule every 12 hours

The agent is not a service: it runs once per trigger and exits. Windows Task Scheduler fires it while the
laptop is on and awake; `StartWhenAvailable` runs a missed slot as soon as the laptop wakes up. Run once in
PowerShell:

```powershell
$action  = New-ScheduledTaskAction -Execute "C:\Source\Repos\job-agent\.venv\Scripts\python.exe" `
             -Argument "-m job_agent.main" -WorkingDirectory "C:\Source\Repos\job-agent"
$trigger = New-ScheduledTaskTrigger -Once -At 09:00 -RepetitionInterval (New-TimeSpan -Hours 12)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "job-agent" -Action $action -Trigger $trigger -Settings $settings
```

Remove with `Unregister-ScheduledTask -TaskName "job-agent"`.

## Tests

```powershell
.venv\Scripts\python -m pytest
```

Pure-Python tests use saved JSON responses (no network); the PDF and form-filling tests run in the real
headless Edge against local files. Nothing in the suite touches a live career site.

## Layout

```
job_agent/
  main.py              one run of the pipeline; CLI flags
  config.py            .env + config.yaml loading
  models.py            Job dataclass
  sources/             one fetcher per career-site backend (workday, smartrecruiters, greenhouse, oracle_hcm, microsoft, amazon)
  filters.py           title / level / location rules
  store.py             SQLite: every job seen and what was done
  llm/                 provider classes (gemini, ollama) behind one ask_json() interface
  matcher.py           fit score
  tailor.py            CV tailoring + the guard against new claims
  render.py            Markdown → HTML → PDF
  apply/               form fillers (greenhouse) + the answer rules
  notify.py            Gmail
tests/                 pytest; fixtures/ holds the saved API responses
```
