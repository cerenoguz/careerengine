# CareerEngine

> https://cerenoguz.github.io/careerengine/

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
* Scores every eligible role from 0–100 on level, role fit, skills overlap, semantic similarity to the candidate profile, and work-authorization wording.
* Prioritizes new-grad roles, SWE I, and other early-career opportunities; excludes internships and roles targeting grad years outside the candidate's own.
* Excludes senior-level roles outright: senior/staff/principal/lead/manager titles, numbered levels above II (III, IV, 4+, L4+), and postings that require more than three years of experience. A junior-sounding description never overrides a senior title.
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

## Ranking

Ranking happens in two steps: hard eligibility gates first, then one match score.

**1. Eligibility gates** — a job that fails any of these is never ranked, and none can be traded off against a high score:

* Not an internship and not targeting an excluded grad year
* No hard work-authorization restriction (citizenship, green card, clearance, export control)
* Level gate: no senior-level title, no numbered level above II, no PhD-titled role, and no requirement of more than three years of experience. Years are read from the *required* part of the posting (ranges use their lower bound; "preferred" experience never counts against a role)
* An engineering or data job title, based in the U.S. or U.S.-remote, and relevant to Computer Science or Mathematics

**2. Match score (0–100)** — a weighted average of five components, each normalized to 0–1:

| Component | Weight | What it measures |
|---|---|---|
| Level | 30% | Explicit new-grad / early-career / "I" roles score highest; unlabelled roles are neutral; "II", 2–3 required years, and senior-scope language score lower |
| Role | 25% | How close the job title is to backend, full-stack, and software engineering, versus adjacent or specialized roles |
| Skills | 20% | Of the technologies the posting asks for, how many the candidate knows (requirements and title count more than company boilerplate; related technologies earn partial credit) |
| Semantic | 15% | Sentence-BERT similarity between the candidate profile and the role's responsibilities and requirements, chunked so nothing is lost to the model's input window |
| Authorization | 10% | Sponsorship and work-authorization wording |

Scores map to bands: **Excellent** (80+), **Strong** (70+), **Good** (60+), **Fair**. The same number is used for ordering, for the email, and for the dashboard. Postings that are the same role listed once per office are merged into one entry with all locations.

## The tech, and the numbers

**Stack:** Python · SQLite · GitHub Actions (scheduled daily) · Sentence-Transformers (`all-MiniLM-L6-v2`) · pytest · SMTP email delivery · Next.js + Supabase dashboard

**Sources:** Greenhouse, Ashby, Lever, and Workable public ATS APIs, plus two custom collectors built for public JSON endpoints outside those platforms (Amazon, Netflix)

As of the most recent run:

| | |
|---|---|
| Companies tracked | **75** |
| Sources reachable per run | **74 / 75** |
| Job postings scanned per run | **~11,800** |
| Qualified & ranked opportunities live | **234** |
| Automated tests | **205**, all passing |
| Email delivery schedule | Daily, 1:00 PM Turkey time |

## Project structure

```text
config/
  companies.yaml
  candidate_profile.txt

src/
  collectors/      Public ATS and custom-API collectors
  ranking/         Eligibility gates, match score, and semantic similarity
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
* Hard eligibility gates (seniority, years required, internships, grad year, work authorization, location) followed by a single 0–100 match score
* Daily HTML + plain-text email reporting
* Ranked additional-opportunities attachment
* Seen-job tracking and delivery auditing
* Sentence-BERT semantic matching as one component of the match score
* GitHub Actions automation, scheduled daily
* Supabase-backed tracking dashboard
* 205 automated tests covering ranking, delivery, reports, and collectors

In progress:

* Production validation of the revised backlog behavior
* Compliant collectors for additional large companies with custom careers sites

## Notes for contributors

`config/candidate_profile.txt`, local SQLite files, generated reports, and SMTP credentials are local runtime configuration. They should not be committed to a public repository.

The email greeting name defaults to "there" and can be personalized via the `CAREERENGINE_RECIPIENT_NAME` environment variable — see `.env.example`.

## License

MIT — see `LICENSE`.
