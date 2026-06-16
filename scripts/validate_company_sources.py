import csv
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests


HEADERS = {
    "User-Agent": "CareerEngineSourceValidator/1.0 (+personal job search project)",
    "Accept": "application/json",
}

TIMEOUT_SECONDS = 12
REQUEST_DELAY_SECONDS = 0.2

OUTPUT_CSV = Path("reports/source_validation.csv")
OUTPUT_TXT = Path("reports/source_validation.txt")


COMPANIES = [
    ("Ramp", "https://ramp.com/careers"),
    ("Deel", "https://www.deel.com/careers"),
    ("Vercel", "https://vercel.com/careers"),
    ("Retool", "https://retool.com/careers"),
    ("PostHog", "https://posthog.com/careers"),
    ("Clerk", "https://clerk.com/careers"),
    ("Supabase", "https://supabase.com/careers"),
    ("Linear", "https://linear.app/jobs"),
    ("Airtable", "https://airtable.com/careers"),
    ("Plaid", "https://plaid.com/careers"),
    ("Stripe", "https://stripe.com/jobs"),
    ("Notion", "https://www.notion.so/careers"),
    ("Figma", "https://www.figma.com/careers"),
    ("Brex", "https://www.brex.com/careers"),
    ("Scale AI", "https://scale.com/careers"),
    ("Datadog", "https://www.datadoghq.com/careers/"),
    ("MongoDB", "https://www.mongodb.com/careers"),
    ("Elastic", "https://www.elastic.co/careers"),
    ("Confluent", "https://www.confluent.io/careers"),
    ("Snowflake", "https://careers.snowflake.com/"),
    ("HashiCorp", "https://www.hashicorp.com/careers"),
    ("Cloudflare", "https://www.cloudflare.com/careers/"),
    ("DigitalOcean", "https://www.digitalocean.com/careers"),
    ("GitLab", "https://about.gitlab.com/jobs/"),
    ("Twilio", "https://www.twilio.com/company/jobs"),
    ("Atlassian", "https://www.atlassian.com/company/careers"),
    ("Dropbox", "https://www.dropbox.com/jobs"),
    ("Zoom", "https://careers.zoom.us/"),
    ("HubSpot", "https://www.hubspot.com/careers"),
    ("Shopify", "https://www.shopify.com/careers"),
    ("Airbnb", "https://careers.airbnb.com/"),
    ("Spotify", "https://www.spotifyjobs.com/"),
    ("Lyft", "https://www.lyft.com/careers"),
    ("Uber", "https://www.uber.com/careers/"),
    ("DoorDash", "https://careers.doordash.com/"),
    ("Robinhood", "https://careers.robinhood.com/"),
    ("Duolingo", "https://careers.duolingo.com/"),
    ("Pinterest", "https://www.pinterestcareers.com/"),
    ("Snap", "https://www.snap.com/en-US/jobs"),
    ("Discord", "https://discord.com/careers"),
    ("OpenAI", "https://openai.com/careers/"),
    ("Anthropic", "https://www.anthropic.com/careers"),
    ("Hugging Face", "https://huggingface.co/careers"),
    ("Perplexity", "https://www.perplexity.ai/careers"),
    ("Cohere", "https://cohere.com/careers"),
    ("WHOOP", "https://www.whoop.com/careers/"),
    ("Tempus", "https://www.tempus.com/careers/"),
    ("Flatiron Health", "https://flatiron.com/careers/"),
    ("Komodo Health", "https://www.komodohealth.com/careers/"),
    ("PathAI", "https://www.pathai.com/careers/"),
    ("Verily", "https://verily.com/careers"),
    ("Tesla", "https://www.tesla.com/careers"),
    ("NVIDIA", "https://www.nvidia.com/en-us/about-nvidia/careers/"),
    ("Intel", "https://www.intel.com/content/www/us/en/jobs/jobs-at-intel.html"),
    ("AMD", "https://www.amd.com/en/corporate/careers"),
    ("Oracle", "https://www.oracle.com/careers/"),
    ("Microsoft", "https://careers.microsoft.com/"),
    ("Amazon", "https://www.amazon.jobs/"),
    ("Google", "https://careers.google.com/"),
]


EXTRA_SLUGS = {
    "Scale AI": ["scale", "scaleai"],
    "DigitalOcean": ["digitalocean", "digital-ocean"],
    "HashiCorp": ["hashicorp"],
    "Hugging Face": ["huggingface", "hugging-face"],
    "Flatiron Health": ["flatironhealth", "flatiron-health", "flatiron"],
    "Komodo Health": ["komodohealth", "komodo-health", "komodo"],
    "Color Health": ["color", "color-health"],
    "WHOOP": ["whoop"],
    "PathAI": ["pathai", "path-ai"],
    "OpenAI": ["openai"],
    "Perplexity": ["perplexity"],
    "MongoDB": ["mongodb", "mongo-db"],
    "Snowflake": ["snowflake"],
    "DoorDash": ["doordash", "door-dash"],
}


@dataclass
class ValidationResult:
    company: str
    career_url: str
    source_type: str
    source_url: str
    status: str
    http_code: int | None
    jobs_found: int
    reason: str


def normalize_slug(value: str) -> str:
    value = value.lower().strip()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value


def domain_slug(career_url: str) -> str | None:
    parsed = urlparse(career_url)
    host = parsed.netloc.lower().replace("www.", "")

    if not host:
        return None

    first_part = host.split(".")[0]
    return normalize_slug(first_part)


def slug_candidates(company: str, career_url: str) -> list[str]:
    candidates: list[str] = []

    company_slug = normalize_slug(company)
    compact_company_slug = company_slug.replace("-", "")

    candidates.append(company_slug)

    if compact_company_slug != company_slug:
        candidates.append(compact_company_slug)

    parsed_domain_slug = domain_slug(career_url)
    if parsed_domain_slug:
        candidates.append(parsed_domain_slug)

    candidates.extend(EXTRA_SLUGS.get(company, []))

    deduplicated: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduplicated:
            deduplicated.append(candidate)

    return deduplicated


def count_jobs(payload: object, source_type: str) -> int:
    if isinstance(payload, list):
        return len(payload)

    if not isinstance(payload, dict):
        return 0

    possible_keys = ["jobs", "postings", "results", "data"]

    for key in possible_keys:
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)

    return 0


def fetch_json(url: str) -> tuple[str, int | None, int, str]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        return "timeout", None, 0, "Request timed out."
    except requests.exceptions.RequestException as error:
        return "network_error", None, 0, str(error)

    if response.status_code == 404:
        return "not_found", response.status_code, 0, "Endpoint not found."

    if response.status_code == 403:
        return "blocked_403", response.status_code, 0, "Access blocked."

    if response.status_code == 429:
        return "rate_limited_429", response.status_code, 0, "Rate limited."

    if response.status_code != 200:
        return "http_error", response.status_code, 0, f"HTTP {response.status_code}"

    try:
        payload = response.json()
    except json.JSONDecodeError:
        return "parse_error", response.status_code, 0, "Response was not JSON."

    job_count = count_jobs(payload, "unknown")

    if job_count == 0:
        return "no_jobs_found", response.status_code, 0, "Valid JSON but no jobs detected."

    return "success", response.status_code, job_count, "OK"


def candidate_urls(slug: str) -> list[tuple[str, str]]:
    return [
        (
            "ashby",
            f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
        ),
        (
            "greenhouse",
            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
        ),
        (
            "lever",
            f"https://api.lever.co/v0/postings/{slug}?mode=json",
        ),
    ]


def validate_company(company: str, career_url: str) -> ValidationResult:
    best_result: ValidationResult | None = None

    for slug in slug_candidates(company, career_url):
        for source_type, source_url in candidate_urls(slug):
            status, http_code, jobs_found, reason = fetch_json(source_url)

            result = ValidationResult(
                company=company,
                career_url=career_url,
                source_type=source_type,
                source_url=source_url,
                status=status,
                http_code=http_code,
                jobs_found=jobs_found,
                reason=reason,
            )

            if status == "success":
                return result

            if best_result is None:
                best_result = result

            time.sleep(REQUEST_DELAY_SECONDS)

    if best_result is None:
        return ValidationResult(
            company=company,
            career_url=career_url,
            source_type="unknown",
            source_url="",
            status="not_tested",
            http_code=None,
            jobs_found=0,
            reason="No candidate source URLs generated.",
        )

    return best_result


def write_outputs(results: list[ValidationResult]) -> None:
    OUTPUT_CSV.parent.mkdir(exist_ok=True)

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "company",
                "career_url",
                "source_type",
                "source_url",
                "status",
                "http_code",
                "jobs_found",
                "reason",
            ],
        )
        writer.writeheader()

        for result in results:
            writer.writerow(result.__dict__)

    lines: list[str] = []
    lines.append("CareerEngine Source Validation")
    lines.append("==============================")
    lines.append("")

    successes = [result for result in results if result.status == "success"]
    failures = [result for result in results if result.status != "success"]

    lines.append(f"Companies tested: {len(results)}")
    lines.append(f"Working sources found: {len(successes)}")
    lines.append(f"Needs manual/custom source work: {len(failures)}")
    lines.append("")

    lines.append("Working Sources")
    lines.append("---------------")
    for result in successes:
        lines.append(
            f"- {result.company}: {result.source_type} | "
            f"Jobs: {result.jobs_found} | {result.source_url}"
        )

    lines.append("")
    lines.append("Needs Manual Review")
    lines.append("-------------------")
    for result in failures:
        lines.append(
            f"- {result.company}: {result.status} | "
            f"HTTP: {result.http_code} | Reason: {result.reason}"
        )

    OUTPUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    results: list[ValidationResult] = []

    for index, (company, career_url) in enumerate(COMPANIES, start=1):
        print(f"[{index}/{len(COMPANIES)}] Validating {company}...")
        result = validate_company(company, career_url)
        results.append(result)

        print(
            f"  -> {result.status} | {result.source_type} | "
            f"Jobs: {result.jobs_found}"
        )

    write_outputs(results)

    print()
    print(f"Saved CSV: {OUTPUT_CSV}")
    print(f"Saved TXT: {OUTPUT_TXT}")


if __name__ == "__main__":
    main()
