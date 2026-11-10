# Group B (auto-apply) — proposed company list

Researched 2026-11-10 against each company's live careers backend, levels.fyi / Glassdoor / AmbitionBox for pay,
and filings or press for standing. Pay = reported entry-level total comp in India; all crowdsourced, treat as ±30%.
Criteria: (1) engineering office in Bangalore or Hyderabad, (2) 12–14+ LPA at SDE-1, (3) established — listed or
clearly profitable. "Apply" = how the application form works, which decides how much Playwright code each needs.

Decision 2026-11-10: keep all 49 (dropped ones included) — all are in `config.yaml` under `companies.auto_apply`;
Siemens added to the referral group (Avature backend, fetcher pending). Fetchers now exist for Workday,
SmartRecruiters, Greenhouse and Oracle HCM (33 of the 49); the rest are skipped with a log warning until written.

## Tier 1 — all three criteria, SDE-1-level postings live now, public apply form (no account)

| Company | Backend (ids for config.yaml) | Blr/Hyd | Entry pay | Standing | Apply |
|---|---|---|---|---|---|
| Stripe | Greenhouse `stripe` | Blr — "Software Engineer, New Grad" open ([link](https://stripe.com/jobs/search?gh_jid=8130876)) | L1 ₹57.8L ([levels.fyi](https://www.levels.fyi/companies/stripe/salaries/software-engineer/locations/greater-bengaluru)) | Private, "robustly profitable" ([2025 letter](https://stripe.com/newsroom/news/stripe-2025-update)) | public form |
| Twilio | Greenhouse `twilio` | Remote-India — "Software Engineer (L3)" open ([link](https://job-boards.greenhouse.io/twilio/jobs/8319386)) | IC1 ₹27.6L ([levels.fyi](https://www.levels.fyi/companies/twilio/salaries/software-engineer/locations/india)) | NYSE TWLO, GAAP-profitable FY25 ([release](https://investors.twilio.com/news-releases/news-release-details/twilio-announces-fourth-quarter-and-full-year-2025-results)) | public form |
| Arista Networks | SmartRecruiters `AristaNetworks` | Blr — "Software Engineer (Platform/EOS/Networking)" open ([link](https://jobs.smartrecruiters.com/AristaNetworks/744000157964409-software-engineer-platform-eos-networking-)) | L2 ₹21.7L ([levels.fyi](https://www.levels.fyi/companies/arista-networks/salaries/software-engineer/levels/2/locations/greater-bengaluru)) | NYSE ANET, NI $3.5B 2025 | public form |
| Zscaler | Greenhouse `zscaler` | Blr + Hyd — "Software Development Engineer – Java" Hyd open ([link](https://job-boards.greenhouse.io/zscaler/jobs/5261571007)) | Assoc. SE ₹15–17L ([levels.fyi](https://www.levels.fyi/companies/zscaler/salaries/software-engineer)) — at the bar | NASDAQ ZS, GAAP loss / non-GAAP profit FY25 ([8-K](https://www.sec.gov/Archives/edgar/data/1713683/000171368325000138/zs-07312025_991.htm)) | public form |
| Commvault | Greenhouse `commvault` | Blr + Hyd — senior titles only today ([board](https://job-boards.greenhouse.io/commvault)) | Engineer ₹23.3L ([levels.fyi](https://www.levels.fyi/companies/commvault/salaries/software-engineer/locations/greater-bengaluru)) | NASDAQ CVLT, NI $76M FY25 | public form |

## Tier 2 — all three criteria, but needs a new fetcher and/or an account to apply

| Company | Backend (ids) | Blr/Hyd | Entry pay | Standing | Apply |
|---|---|---|---|---|---|
| NVIDIA | Workday `nvidia.wd5` / `nvidia` / `NVIDIAExternalCareerSite` | Blr + Hyd (mostly Senior titles) | IC1 ₹27.5L ([levels.fyi](https://www.levels.fyi/companies/nvidia/salaries/software-engineer/locations/india)) | NASDAQ NVDA | Workday account per company |
| Palo Alto Networks | Workday `paloaltonetworks.wd5` / `paloaltonetworks` / `panwexternalcareers` | Blr + Hyd (mostly Senior/Staff) | ₹34.8L ([levels.fyi](https://www.levels.fyi/companies/palo-alto-networks/salaries/software-engineer/locations/india)) | NASDAQ PANW | Workday account |
| Visa | Workday `visa.wd5` / `visa` / `Visa` | Blr only; Senior/Lead today (1–2 yr roles existed earlier in 2026) | L3 ₹22.9L ([levels.fyi](https://www.levels.fyi/companies/visa/salaries/software-engineer/locations/india)) | NYSE V | Workday account |
| Atlassian | custom JSON `atlassian.com/endpoint/careers/listings` → iCIMS | Blr / Remote-India — "Software Engineer II" open ([link](https://careers-apac-atlassian.icims.com/jobs/27346/software-engineer-ii/job)) | P30 ₹40–45L ([levels.fyi](https://www.levels.fyi/companies/atlassian/salaries/software-engineer?country=14)) | NASDAQ TEAM (GAAP loss, strong FCF) | iCIMS profile |
| AMD | custom JSON `careers.amd.com/api/jobs` → iCIMS | Blr + Hyd — SDE titles open ([link](https://global-external-amd.icims.com/jobs/92144/login)) | L5 ₹27.8L ([levels.fyi](https://www.levels.fyi/companies/amd/salaries/software-engineer/locations/india)) | NASDAQ AMD | iCIMS profile |
| JPMorgan Chase | Oracle HCM `jpmc.fa.oraclecloud.com` site `CX_1001` (public REST) | Blr + Hyd — "Software Engineer II" open ([link](https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210804303)) | 502 ₹18.5L ([levels.fyi](https://www.levels.fyi/companies/jpmorgan-chase/salaries/software-engineer/locations/greater-bengaluru)); SWE I base ₹12.5–17.75L ([Glassdoor](https://www.glassdoor.co.in/Salary/JPMorgan-Chase-and-Co-SEP-Software-Engineer-I-Salaries-E5224839_D_KO22,45.htm)) | NYSE JPM | email + verification code |
| Oracle | Oracle HCM `eeho.fa.us2.oraclecloud.com` site `CX_45001` (public REST) | Hyd + Blr (237 India "software developer" reqs; no "Developer 1" today) | IC1 ₹24.2L ([levels.fyi](https://www.levels.fyi/companies/oracle/salaries/software-engineer/levels/ic-1/locations/greater-bengaluru)); ₹11–15L ([Glassdoor](https://www.glassdoor.co.in/Salary/Oracle-IC1-Salaries-E1737_D_KO7,10.htm)) | NYSE ORCL | email + verification code |
| Adobe | Workday `adobe.wd5` / `adobe` / `external_experienced` | Blr — no SDE titles open today | P10 ₹25.7L ([levels.fyi](https://www.levels.fyi/companies/adobe/salaries/software-engineer/locations/india)) | NASDAQ ADBE | Workday account |
| Nutanix | Jobvite `jobs.jobvite.com/nutanix` (HTML, no JSON found) | Blr — MTS titles (5–9 yrs today) | MTS1 ₹30.7L ([levels.fyi](https://www.levels.fyi/companies/nutanix/salaries/software-engineer)) | NASDAQ NTNX | Jobvite form |
| Pegasystems | custom (pega.com, Drupal) | Blr — "Software Engineer, GenAI Engineering" open ([link](https://www.pega.com/about/careers/24124/software-engineer-genai-engineering-ai/ml)); Hyd senior | ₹12–19L ([Glassdoor](https://www.glassdoor.co.in/Salary/Pegasystems-Hyderabad-Salaries-EI_IE5936.0,11_IL.12,21_IM1076.htm)) | NASDAQ PEGA | native form |
| Goldman Sachs | custom (higher.gs.com, JS-only) | Blr + Hyd — Associate SWE indexed ([link](https://higher.gs.com/roles/168913)) | Analyst ₹20–28L ([Glassdoor](https://www.glassdoor.co.in/Salary/Goldman-Sachs-Software-Engineering-Analyst-Salaries-E2800_D_KO14,42.htm)) | NYSE GS | Playwright-only, account |
| Apple | custom (jobs.apple.com) | Blr + Hyd — 191 SWE results live ([search](https://jobs.apple.com/en-in/search?location=india-INDC&team=software-engineering-SFTWR)) | ICT2 ₹36L ([levels.fyi](https://www.levels.fyi/companies/apple/salaries/software-engineer/locations/greater-bengaluru)) | NASDAQ AAPL | Apple ID, heavy anti-bot |
| Google | custom (google.com/about/careers, JS-only) | Blr + Hyd — only "PhD, Early Career" indexed for entry level | L3 ₹39.1L ([levels.fyi](https://www.levels.fyi/companies/google/salaries/software-engineer/levels/l3/locations/greater-bengaluru)) | NASDAQ GOOGL | Google account, anti-bot |

## Your call — fails one criterion

| Company | Issue | Otherwise |
|---|---|---|
| Databricks | Private, VC-funded, no GAAP profit disclosed (self-reported positive FCF, $134B valuation Feb 2026) | Greenhouse `databricks`; Blr "Software Engineer, Infrastructure" open; L3 ₹61.6L |
| Postman | Private; profitability undisclosed; last priced round 2021, secondary valuation halved | Workday `postman.wd108` / `postman` / `careers`; Blr "Software Engineer" open; IC1 ₹29.2L |
| PhonePe | Loss-making: FY26 net loss ₹2,792 cr on ₹7,920 cr revenue; IPO postponed ([Inc42](https://inc42.com/buzz/ipo-bound-phonepe-posts-%e2%82%b92792-cr-loss-in-fy26-revenue-up-11-5-yoy/)) | SmartRecruiters `PHONEPELIMITED`; 10 "Software Engineer" Blr postings; SE1 ₹28.1L |
| SAP Labs India | Entry pay at/below bar: ₹11L avg base ([Glassdoor](https://www.glassdoor.co.in/Salary/SAP-Developer-Associate-Bangalore-Salaries-EJI_IE10471.0,3_KO4,23_IL.24,33_IM1091.htm)), ₹14.5L TC ([levels.fyi](https://www.levels.fyi/companies/sap/salaries/software-engineer/locations/india)) | SmartRecruiters `SAPITBusinessSysteme`; Blr; NYSE SAP |
| Freshworks | Engineering is mostly Chennai; Blr/Hyd have senior titles only | SmartRecruiters `Freshworks`; ₹14L; NASDAQ FRSH, GAAP-profitable 2025 |
| Rubrik | GAAP net loss FY26 (EPS −$1.78), positive FCF; Blr senior-only today | Greenhouse `rubrik`; L3 ₹66.6L; NYSE RBRK |
| LinkedIn | Blr postings are all Senior/Staff | SmartRecruiters `linkedin3`; IC1 ₹47L |
| Intuit | Blr postings are Senior/Staff only (5+ yrs) | custom (TalentBrew) → Avature; SWE1 ₹31L; NASDAQ INTU |
| Uber | Oracle HCM backend but the REST site id was not found; job pages JS-only | L3 ₹37.4L; NYSE UBER |
| Qualcomm, PayPal, Walmart, Morgan Stanley, Micron | Listings behind Eightfold/Workday that reject non-browser clients — fetching needs Playwright, not verified | Qualcomm ₹20.5L, PayPal ₹39.3L, Walmart ₹20.5L, MS ₹21.4L, Micron ₹12.65L |

## Dropped (reason)

Mastercard (eng hub is Pune), Expedia (Gurgaon only), MongoDB (Gurugram only), Sprinklr (no SWE in Blr/Hyd),
Zoho (Chennai), Dell (entry ₹10.5–12.4L, below bar), Flipkart / Myntra / Swiggy (loss-making FY26),
Razorpay (loss FY25, no SDE postings), Groww / Zerodha / Zomato (no engineering postings or no job board),
Chargebee (1 job listed, profitability unverifiable), Rippling (private, listings unverifiable),
Confluent (acquired by IBM Mar 2026).

## What phase 2 builds, in order

1. **Greenhouse fetcher** (`GET boards-api.greenhouse.io/v1/boards/<token>/jobs`, public JSON) — covers 5 of 6
   Tier-1/your-call boards. Then **Greenhouse + SmartRecruiters apply** (public forms, no login) — that makes
   Stripe, Twilio, Arista, Zscaler, Commvault fully automatic.
2. **Oracle HCM fetcher** (public REST) — JPMorgan, Oracle. Apply there asks for an emailed verification code,
   so the agent fetches the code from your Gmail over IMAP (same app password) or falls back to emailing you.
3. **Workday apply** — NVIDIA, Palo Alto, Visa, Adobe. Fetching already works; applying needs an account per
   company that you create once (CAPTCHA at signup); the agent logs in from env vars.
4. Custom sites (Atlassian, AMD, Pega, Goldman, Apple, Google) — one fetcher/filler each; last, if at all.

Until a company's apply step exists, it behaves like Group A: tailored CV emailed to you, you apply.
