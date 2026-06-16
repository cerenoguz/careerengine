from typing import Any
from src.collectors.ashby import collect_ashby_jobs
from src.collectors.greenhouse import collect_greenhouse_jobs
from src.collectors.lever import collect_lever_jobs
from src.collectors.workable import collect_workable_jobs
from src.models import Job, SourceHealth


DISALLOWED_COMPLIANCE_STATUSES = {
    "robots_disallowed",
    "terms_disallowed",
    "disabled",
}


def collect_jobs_for_company(company_config: dict[str, Any]) -> tuple[list[Job], SourceHealth]:
    company = company_config.get("name", "Unknown")
    source_type = company_config.get("source_type", "")
    source_url = company_config.get("source_url", "")
    collection_status = company_config.get("collection_status", "disabled")
    compliance_status = company_config.get("compliance_status", "manual_review_required")

    if collection_status != "enabled":
        return [], SourceHealth(
            company=company,
            source=source_type,
            status="disabled",
            http_code=None,
            jobs_found=0,
            reason=company_config.get("disabled_reason", "Collection disabled."),
        )

    if compliance_status in DISALLOWED_COMPLIANCE_STATUSES:
        return [], SourceHealth(
            company=company,
            source=source_type,
            status=compliance_status,
            http_code=None,
            jobs_found=0,
            reason=f"Source skipped due to compliance status: {compliance_status}",
        )

    if source_type == "greenhouse":
        return collect_greenhouse_jobs(company=company, source_url=source_url)
    if source_type == "ashby":
        return collect_ashby_jobs(company=company, source_url=source_url)
    if source_type == "lever":
        return collect_lever_jobs(company=company, source_url=source_url)
    if source_type == "workable":
        return collect_workable_jobs(company=company, source_url=source_url)

    return [], SourceHealth(
        company=company,
        source=source_type,
        status="unsupported_source",
        http_code=None,
        jobs_found=0,
        reason=f"Unsupported source type: {source_type}",
    )