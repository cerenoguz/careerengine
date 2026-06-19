# CareerEngine

> **Status:** In active development — V2.1, June 2026

CareerEngine is a job-discovery and ranking pipeline built for the developer to help with early-career software engineering search.

It collects active roles from validated public job sources, evaluates them against a candidate profile, ranks them, and generates a daily opportunity report. The goal is to reduce the time spent manually checking careers pages while keeping application decisions fully manual.

## What it does

* Collects active roles from public ATS platforms including Greenhouse, Ashby, Lever, and Workable.
* Normalizes job listings into a shared format.
* Filters for software engineering, backend, full-stack, data, AI/ML, developer tools, infrastructure, healthtech, and fintech-related roles.
* Scores roles using title fit, technical overlap, degree relevance, seniority signals, work-authorization wording, and profile-to-description similarity.
* Prioritizes explicit internships, new-grad roles, SWE I, and other early-career opportunities.
* Prevents senior, staff, principal, lead, manager, and director roles from receiving early-career bonuses.
* Sends the top-ranked opportunities in a daily email report.
* Generates a ranked TXT attachment for additional qualified opportunities below the email cutoff.
* Tracks jobs shown in the main email body to prevent repeat recommendations.
* Records source health, delivery state, and recommendation diagnostics.

## Ranking flow

CareerEngine builds one shared candidate pool each day:

```text
Active qualified jobs
- roles already shown in an email body
= ranked candidate pool
```

The ranked list is split into:

```text
#1–#25   Daily email body
#26–#N   Additional qualified opportunities attachment
```

Roles in the attachment remain eligible for future runs. They are ranked again alongside newly discovered jobs rather than being treated as permanently delivered.

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

## Tech stack

* Python
* SQLite
* GitHub Actions
* Greenhouse, Ashby, Lever, and Workable public job sources
* Sentence-Transformers with `all-MiniLM-L6-v2`
* pytest
* SMTP email delivery

## Local setup

```bash
git clone https://github.com/cerenoguz/careerengine.git
cd careerengine

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python -m pytest
python -m src.main
```

Local runs generate reports without sending email unless SMTP environment variables are configured.

## Project structure

```text
config/
  companies.yaml
  candidate_profile.txt

src/
  collectors/      Public ATS collectors
  ranking/         Fit scoring and semantic similarity
  reporting/       Email and attachment generation
  storage/         SQLite delivery and deduplication state
  compliance/      Source-access safeguards

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

* Public ATS job collection
* Rule-based fit scoring
* Early-career ranking calibration
* Daily email reporting
* Ranked additional-opportunities attachment
* Seen-job tracking and delivery auditing
* Sentence-BERT semantic matching in shadow mode
* GitHub Actions automation
* Test coverage for ranking, delivery, reports, and collectors

In progress:

* Production validation of the revised backlog behavior
* Controlled rollout of semantic ranking
* Compliant collectors for large companies with custom careers sites

## Notes for contributors

`config/candidate_profile.txt`, local SQLite files, generated reports, and SMTP credentials are local runtime configuration. They should not be committed to a public repository.

