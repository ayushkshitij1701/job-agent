# job-agent

Watches the career sites in `config.yaml`, scores each new opening against `resume.md`,
tailors a copy of the resume to the job description, and emails you the result.
Design and decisions: `PLAN.md`. Company research for the auto-apply list: `COMPANIES.md`.

Career-site backends with a fetcher: Workday, SmartRecruiters, Greenhouse, Oracle HCM, Microsoft (Eightfold),
Amazon. Companies in `config.yaml` on any other backend are skipped with a log warning until theirs is written.

## Setup (once)

```powershell
cd C:\Source\Repos\job-agent
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # then fill in SMTP_APP_PASSWORD (and GEMINI_API_KEY if you use Gemini)
```

- `SMTP_APP_PASSWORD`: a Gmail app password (Google account → Security → 2-Step Verification → App passwords).
- `GEMINI_API_KEY`: from Google AI Studio (aistudio.google.com → Get API key). Only for `--provider gemini`.
- Auto-apply (phase 2) drives the Microsoft Edge already on the machine through Playwright
  (`channel="msedge"`, headless) — no `playwright install` / Chromium download needed.

## Choosing the model

`config.yaml` → `llm.provider`:

- `ollama` (default) — a local model on your GPU, model `qwen3.5:9b`. Install Ollama (ollama.com),
  then `ollama pull qwen3.5:9b`. Ollama runs as a background service after install; the model sits in
  VRAM only while in use and is unloaded a few minutes after the last request.
  `think: false` keeps the model from writing a reasoning chain before each answer (~4 s vs ~55 s a call,
  same scores in our tests); set `think: true` to compare.
- `gemini` — Google's API, model `gemini-3.8-flash` (free tier), needs `GEMINI_API_KEY`.

Adding another provider = one new class in `job_agent/llm/` (request/response shape only) plus
one line in `job_agent/llm/__init__.py`. Nothing else changes.

## Run

```powershell
.venv\Scripts\python -m job_agent.main
```

Flags override `config.yaml` for that run only (no flags = the config values):

```powershell
.venv\Scripts\python -m job_agent.main --model qwen3.5:4b              # another Ollama model
.venv\Scripts\python -m job_agent.main --think                         # Qwen reasons first (slower)
.venv\Scripts\python -m job_agent.main --provider gemini               # Gemini with its config model
.venv\Scripts\python -m job_agent.main --provider gemini --model gemini-3.6-flash
```

`--model` applies to whichever provider is active; `--think` / `--no-think` only affect Ollama.

Each run looks only at jobs it has not seen before (tracked in `jobs.db`). Output per match:
`out\<Company>_<id>\resume.md`, `resume.pdf`, `job.json`, plus an email with the fit score,
the changes made, and anything the JD asks for that is not on your resume.

## Auto-apply (Group B)

For companies under `companies.auto_apply` whose backend has a form filler (today: Greenhouse — Stripe,
Twilio, Zscaler, Commvault, Databricks, Rubrik, MongoDB, Razorpay, Groww), a match is tailored, then the
agent opens the application form in headless Edge, fills it from `applicant`, `screening` and `education`
in `config.yaml`, uploads the tailored PDF, and submits. You get an email per job with the subject prefixed:

- `APPLIED:` submitted; the body lists every answer given.
- `NEEDS YOUR ANSWER:` the form asked something not in config (e.g. a home address) — nothing was
  submitted; apply yourself or add the answer to config and it will not be retried automatically.
- `APPLY FAILED:` the site did not confirm the submission (bot check, changed form); apply yourself.
- `DRY RUN:` `apply.dry_run` is true — filled, screenshot attached (`form.png`), not submitted.

Start with `apply.dry_run: true`, look at a couple of `form.png`, then set it to `false`.
Other backends (SmartRecruiters is behind a DataDome bot check; Workday needs an account) still email you
the tailored CV with an "apply yourself" note.

## Schedule every 12 hours

The agent is not a service: it runs once per trigger and exits. Windows Task Scheduler fires it
while the laptop is on and awake; `StartWhenAvailable` runs a missed slot as soon as the laptop
wakes up. Run once in PowerShell:

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
