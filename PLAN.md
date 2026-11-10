# Job Agent — Plan

Status: draft, waiting on open questions (bottom of file).
Verified on 2026-11-07: every endpoint below was called with curl, with no login and no cookies.

## 1. What it does

| Group | Companies | Action |
|---|---|---|
| A. Referral | ServiceNow, Microsoft, Target, Cisco, Amazon, State Street, Maersk, Acumatica, Salesforce | Tailor the CV to the JD, email it to you (md + PDF). You edit if you want, get the referral, and apply yourself. Salesforce email also reminds you to ask Yash (see §4). |
| B. Auto-apply | List in `config.yaml` (12–14+ LPA, established) | Tailor the CV, apply automatically, then email you the job, score and CV diff to check later. |

## 2. Where the jobs come from (verified)

Four backends cover all 9 companies:

| Backend | Companies | Endpoint |
|---|---|---|
| Workday | Salesforce, Target, Cisco, State Street, Maersk | `POST https://{host}/wday/cxs/{tenant}/{site}/jobs` |
| SmartRecruiters | ServiceNow, Acumatica | `GET https://api.smartrecruiters.com/v1/companies/{id}/postings?country=in&q=...` |
| Eightfold | Microsoft | `GET https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query=...&location=India`; detail `GET /api/apply/v2/jobs/{position id}?domain=microsoft.com`. Needs a browser User-Agent; rate-limits bursts. |
| Amazon custom | Amazon | `GET https://www.amazon.jobs/en/search.json?base_query=...&country=IND` |

Workday tenants (host / tenant / site):
- Salesforce: `salesforce.wd12` / `salesforce` / `External_Career_Site`
- Target: `target.wd5` / `target` / `targetcareers`
- Cisco: `cisco.wd5` / `cisco` / `Cisco_Careers`
- State Street: `statestreet.wd1` / `statestreet` / `Global`. Needs the India location facet, because searching for "India" in the search text doesn't filter results here.
- Maersk: `maersk.wd3` / `maersk` / `Maersk_Careers`

Group B (2026-11-10, all 49 researched companies in `config.yaml`, research in COMPANIES.md) added two public
backends: **Greenhouse** (`GET boards-api.greenhouse.io/v1/boards/{board}/jobs`, detail `/jobs/{id}`) and
**Oracle HCM** (`GET {host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?...finder=findReqs;siteNumber=..`,
detail `recruitingCEJobRequisitionDetails?...finder=ById;Id="{id}",siteNumber=..`). Still without a fetcher
(skipped with a warning): Eightfold tenants other than Microsoft (session-gated), Avature (Siemens), iCIMS/Jobvite,
and the custom sites (Google, Apple, Goldman, ...). Siemens (referral) is on Avature.

## 3. Flow (runs every 12 hours via Windows Task Scheduler; command in README.md)

```
fetch jobs (per company) → drop already-seen (SQLite) → filter title/location
  → Claude scores job vs resume (0-100 + reason)
  → score ≥ threshold → tailor CV to the JD (§4a):
       Group A → email: job, score, link, tailored resume attached (md + PDF), referral reminder
       Group B → Playwright fills the form, uploads tailored PDF, submits
                 → email: job, score, link, CV diff, what was submitted
                 → if the site blocks it (login wall, CAPTCHA), falls back to a Group A style email
```

## 4. Salesforce referral — what we know

- Salesforce uses Workday. According to a Salesforce employee, the employee submits the referral inside Workday, and you then get an apply link.
- Some Workday forms have a "How did you hear about us → I know someone who works here" field. It's not confirmed whether Salesforce's form has it.
- Plan: when a Salesforce match appears, send you an email asking Yash (yash.sharma@salesforce.com) to refer you. If the form has the referrer field, the agent fills in his email there as well.

## 4a. CV tailoring per job (all groups)

`resume.md` is the master and is never edited by the agent. For each job the agent makes a copy, `out/<company>_<jobid>/resume.md`, plus a PDF (headless Edge, nothing to install). Group A gets the files to edit and use; Group B gets the diff after the agent has applied.

Allowed changes (minor tweaks to pass the ATS filter):
- Reorder bullets, skills and projects so the ones matching the JD come first.
- Rephrase existing bullets using the JD's own wording for things already on the resume
  (e.g. "PostgreSQL" ↔ "Postgres", "REST APIs" ↔ "RESTful services", "LLM" ↔ "GenAI").
- Reword the summary line to lead with the role the JD asks for.
- Add a skill to the Skills section only if it is in `tailor.skills_allowed_to_add` in `config.yaml`
  (quick-to-learn tech you have approved) and the JD asks for it.

Never:
- New numbers, metrics, responsibilities, tools or technologies not on the master resume.
- Changes to dates, titles, companies, education or publications.
- Technology that can't be picked up in a few days, even if many JDs ask for it.

Guard (code, not prompt): after Claude returns the tailored copy, the agent rejects it if
any number or any technology term appears that is not in the master resume or the allowlist.
Missing JD-required skills are listed in the email so you decide whether to add them to the allowlist.

## 4b. Your settings (`config.yaml`, answered 2026-11-07)

```yaml
llm:
  provider: gemini                # gemini | ollama; one class per provider in job_agent/llm/, rest of the agent
  gemini: {model: gemini-3.8-flash}          #   only calls client.ask_json(system=, user=, schema=)
  ollama: {model: qwen3.5:9b, url: http://localhost:11434}   # local, 6.6 GB on the 8 GB RTX 5050

notify:
  email: iayush45@gmail.com       # Gmail; SMTP_APP_PASSWORD from env

roles:                            # (2026-11-08) user is a 2026 graduate, ~6 months full-time + strong internships:
  max_level: 1                    # full-time SDE-1 is the floor (no internships, no campus programmes);
                                  # SDE-2 titles only at the three below; Senior/III never.
  level_2_ok_at: [Microsoft, ServiceNow, Salesforce]   # title filter + a level note to the scorer

locations:
  job_cities: [Hyderabad, Bangalore, Noida, Gurugram, Pune]   # priority order; used to rank matches
  include_remote: true                                        # remote (India) jobs count too
  company_must_have_office_in: [Bangalore, Hyderabad]        # Group B company filter

tailor:
  # Skills the agent may add when a JD asks for them. Two kinds:
  #   exact      – added only if the JD names this term
  #   categories – the agent decides per JD whether a JD term fits the category
  #                (e.g. JD says "Redshift" → fits "any SQL database"); every such
  #                addition is listed in the email with the category it matched,
  #                so you can see it and remove it
  skills_allowed_to_add:
    exact: [Flask, Django, Redis, MongoDB, GraphQL, Apache Spark, PySpark,
            Agentic AI, Transformer models, Concurrency, POSIX]
    categories:
      - any SQL database or dialect
      - any RAG / LLM-orchestration framework      # you already have LangChain, RAG, Multi-Agent Systems
  # Already on the master resume, never need adding: LangChain, RAG, Multi-Agent Systems, PostgreSQL, Snowflake

screening:                        # fixed answers for application forms (Group B)
  notice_period_days: 45
  current_ctc_lpa: 8
  expected_ctc:
    min_lpa: 12
    preferred_lpa: 14
    mode: company_average         # see below
  willing_to_relocate: true
```

**Expected CTC lookup:** the first time a company comes up, the agent asks Claude with the API's
web search tool for that company's typical SDE pay in India at your level, then picks a figure
inside your band (never below 12, 14+ when the company's range allows). The figure and its source
are saved per company in SQLite and shown in the email, so each company is looked up once and you
can override it in `config.yaml`. If nothing reliable is found, it uses 14 LPA.

## 5. Limits to know

- **Applying needs a browser; listing does not.** Every job feed is a plain HTTP API (no browser). Applying is not: Workday, Eightfold (Microsoft) and Amazon have no candidate-facing apply API, and SmartRecruiters' apply endpoint needs a company-issued `X-SmartToken` (verified 2026-11-07 in their docs), as do Greenhouse and Lever. So Group B applications go through Playwright, which runs **headless** (no window on screen) and fills the form itself — nothing manual. Playwright is only needed in phase 2.
- **Workday needs a separate account for each company.** You create those accounts yourself and solve any CAPTCHAs; the agent logs in with credentials from env vars and fills in the rest.
- **Salary isn't in the posts.** The 12–14+ LPA filter comes from the company list in Group C, not from the job post.
- **Group B submits without you.** Screening questions (notice period, expected CTC, work authorisation) are answered from fixed values in `config.yaml`; anything the form asks that isn't configured makes the agent stop and email you instead of guessing.

## 6. Project layout

```
job-agent/
  config.yaml            # companies, groups, filters, threshold
  .env.example           # ANTHROPIC_API_KEY, SMTP_USER, SMTP_APP_PASSWORD (never committed)
  job_agent/
    models.py            # Job dataclass
    sources/workday.py, smartrecruiters.py, microsoft.py, amazon.py
    store.py             # SQLite: seen jobs, application status
    resume.py            # PDF → text
    matcher.py           # Claude scoring
    notify.py            # email
    apply/               # Playwright form fillers (phase 2)
    main.py              # one run of the pipeline
  tests/                 # pytest, using saved JSON responses (no network)
```

## 7. Phases

1. **Watch + tailor + notify** — BUILT 2026-11-07 (42 tests passing, see README.md to run).
   fetchers (4 backends), SQLite store, title/location filters, Claude matcher, CV tailoring with code guard,
   Markdown→PDF via headless Edge, Gmail email. Fully covers Group A. Not yet run against the live APIs
   end-to-end with an API key — first real run is the next step.
2. **Auto-apply:** Playwright fillers for Group B sites, starting with whichever backends the Group B list uses most.
   2026-11-10: `playwright` installed (drives the installed Edge); PDF rendering moved to it (the plain
   `msedge --print-to-pdf` call hung after writing the file); Greenhouse + Oracle HCM fetchers built; all 49
   Group B companies in config. Until a backend's apply step exists, Group B matches are emailed like Group A.
   2026-11-10 (later): **Greenhouse apply built** (`job_agent/apply/`): answers by label regex from
   `applicant` / `screening` / `education` config, react-select + autocomplete handling, "Other" fallback for
   curated school lists, resume upload, submit only when every required question is answered, `apply.dry_run`
   (fill + form.png, no submit). Dry-run verified on the live Stripe and Zscaler forms. Not yet verified: a real
   submission (Greenhouse loads reCAPTCHA Enterprise; headless may be scored low). SmartRecruiters' apply page
   sits behind a DataDome bot check in headless mode → emails only, for now.
3. **Group B expansion:** fetchers for the pending backends (Avature for Siemens, Eightfold tenants, custom sites).

## 8. Open questions

- [Q-7] Approved 2026-11-07 for phase 1: `requests`, `pyyaml`, `pypdf` (reads PDF JDs), `pytest`.
  (`anthropic` was approved too, then dropped 2026-11-08 when the user chose Gemini | Ollama; both are called over REST with `requests`.)
  Phase 2: `playwright` approved 2026-11-10 (1.65.0); it drives the installed Edge (`channel="msedge"`), no Chromium download.
  Master resume = `resume.md`, never edited by the agent; tailored copies rendered to PDF via headless Edge,
  styled like the ohmycv export (blue headings, serif body).
- [Q-11] Roles: default = taken from your resume (Software Engineer / SDE / Backend Engineer)

Resolved 2026-11-07: resume is `job-agent/resume.md` (Q-8); no approval gate before applying (Q-3);
Gmail notifications (Q-9); no known Group B companies yet, I propose a list at phase 2 (Q-10);
skills allowlist and screening answers in §4b (Q-12, Q-13).
