# CareerEngine

> **Status:** In active development — V2.2, September 2026

Job hunting as a new grad means checking the same dozens of company career pages every single day, hoping to catch a new posting before hundreds of other applicants do, while also trying to figure out — role by role — whether a company will even sponsor a visa if you need one. That's a lot of repetitive, tedious checking for very little signal, and it's easy to miss a good opportunity simply because you didn't refresh the right page at the right time.

CareerEngine is that daily checking, automated. It quietly watches a curated list of companies known to be worth a new grad's time — including a number of "under the radar" ones with genuinely good visa-sponsorship track records — and every day it tells you what's new, and only what's actually a good fit for your background. No noise, no re-reading the same postings twice, no manually cross-referencing whether a company sponsors. You open one email, or one dashboard, and know exactly what's worth your time today.

## How to use it

If you're the one it's built for: you don't have to do anything. It runs automatically every day and emails you a ranked list of new opportunities, with a dashboard to track what you've applied to.

If you want to run your own copy:

```bash
git clone https://github.com/cerenoguz/careerengine.git
cd careerengine

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp config/candidate_profile.example.txt config/candidate_profile.txt
# then edit config/candidate_profile.txt with your own background

python -m pytest
python -m src.main
```

That runs the whole pipeline locally and writes a report to `reports/daily_report.txt` — no email is sent unless you configure SMTP credentials (see `.env.example`). To get daily emails automatically, set the secrets listed in `.env.example` on a fork of this repo and let `.github/workflows/daily.yml` run on its schedule.

## What it does

* Collects active roles from public ATS platforms including Greenhouse, Ashby, Lever, and Workable, plus verified public JSON endpoints for select large employers outside those platforms (Amazon, Netflix).
* Normalizes job listings into a shared format.
* Filters for software engineering, backend, full-stack, data, AI/ML, developer tools, infrastructure, healthtech, and fintech-related roles.
* Scores roles using title fit, technical overlap, degree relevance, seniority signals, work-authorization wording, and profile-to-description similarity.
* Prioritizes new-grad roles, SWE I, and other early-career opportunities; excludes internships and roles targeting grad years outside the candidate's own.
* Prevents senior, staff, principal, lead, manager, and director roles from receiving early-career bonuses.
* Sends the top newly discovered opportunities in a daily email report, ranked best-fit first.
* Generates a ranked TXT attachment for additional qualified opportunities below the top-ranked cutoff.
* Tracks previously seen jobs to identify newly discovered opportunities for the email body.
* Records source health, delivery state, and recommendation diagnostics.
* Syncs ranked opportunities to a Supabase-backed dashboard for tracking application status.

## Ranking flow

CareerEngine builds one shared ranked candidate pool each day from all active qualified jobs.

The pool is split into:

```text
#1–#25   Top-ranked cutoff
#26–#N   Additional qualified opportunities attachment
```

The daily email body lists the top newly discovered jobs, ranked best-fit first, not just the top-ranked roles overall. Roles below the top-ranked cutoff remain eligible for future runs — they are ranked again alongside newly discovered jobs rather than being treated as permanently delivered.

## Ranking signals

The current scoring model considers:

* Software engineering and backend relevance
* Python, Java, TypeScript, SQL, REST APIs, PostgreSQL, Docker, cloud systems, data pipelines, and ML/LLM overlap
* Computer Science and Mathematics degree relevance
* Internship and early-career signals
* Seniority penalties and blockers
* Work-authorization wording when present
* Lexical profile-to-description similarity

Sentence-BERT semantic similarity is currently running in shadow mode. It is calculated for evaluation but does not yet affect the live recommendation order.

## The tech, and the numbers

**Stack:** Python · SQLite · GitHub Actions (scheduled daily) · Sentence-Transformers (`all-MiniLM-L6-v2`) · pytest · SMTP email delivery · Next.js + Supabase dashboard

**Sources:** Greenhouse, Ashby, Lever, and Workable public ATS APIs, plus two custom collectors built for public JSON endpoints outside those platforms (Amazon, Netflix)

As of the most recent run:

| | |
|---|---|
| Companies tracked | **75** |
| Sources reachable per run | **74 / 75** |
| Job postings scanned per run | **~11,800** |
| Qualified & ranked opportunities live | **239** |
| Automated tests | **104**, all passing |
| Email delivery schedule | Daily, 1:00 PM Turkey time |

## Project structure

```text
config/
  companies.yaml
  candidate_profile.txt

src/
  collectors/      Public ATS and custom-API collectors
  ranking/         Fit scoring and semantic similarity
  reporting/       Email and attachment generation
  storage/         SQLite delivery and deduplication state
  compliance/      Source-access safeguards
  dashboard/       Supabase sync for the tracking dashboard

dashboard/
  Next.js + Supabase frontend for tracking application status

tests/
  Collector, ranking, reporting, delivery, and backlog tests

scripts/
  Source validation and maintenance utilities
```

## Compliance

CareerEngine only uses validated public job sources. It does not access logged-in pages, bypass CAPTCHAs, rotate proxies, evade rate limits, or scrape blocked sources.

See `LEGAL_AND_COMPLIANCE.md`, `TERMS_OF_USE.md`, and `robots_policy.md` for project policies.

## Current status

Implemented:

* Public ATS job collection, plus custom collectors for select large employers (Amazon, Netflix)
* Rule-based fit scoring with internship and off-target grad-year exclusions
* Early-career ranking calibration
* Daily HTML + plain-text email reporting
* Ranked additional-opportunities attachment
* Seen-job tracking and delivery auditing
* Sentence-BERT semantic matching in shadow mode
* GitHub Actions automation, scheduled daily
* Supabase-backed tracking dashboard
* 104 automated tests covering ranking, delivery, reports, and collectors

In progress:

* Production validation of the revised backlog behavior
* Controlled rollout of semantic ranking
* Compliant collectors for additional large companies with custom careers sites

## Notes for contributors

`config/candidate_profile.txt`, local SQLite files, generated reports, and SMTP credentials are local runtime configuration. They should not be committed to a public repository.

The email greeting name defaults to "there" and can be personalized via the `CAREERENGINE_RECIPIENT_NAME` environment variable — see `.env.example`.
