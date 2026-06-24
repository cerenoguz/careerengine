from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Job:
    id: str
    company: str
    title: str
    location: str
    description: str
    url: str
    date_posted: Optional[str]
    source: str
    employment_type: Optional[str] = None
    seniority: Optional[str] = None
    is_internship: bool = False
    is_new_grad: bool = False
    eligibility_status: str = "unclear"
    description_similarity: float = 0.0
    semantic_similarity: float = 0.0
    score: float = 0.0
    why_matched: list[str] = field(default_factory=list)
    first_found_date: Optional[str] = None
    is_new_discovery: bool = False

    hard_no: bool = False
    required_years_min: Optional[int] = None
    required_years_max: Optional[int] = None
    years_requirement_type: str = "unclear"
    new_grad_signal: str = "no"
    internship_signal: str = "no"
    citizenship_required: str = "no"
    permanent_resident_required: str = "no"
    clearance_required: str = "no"
    export_control_restriction: str = "no"
    sponsorship_language: str = "unclear"
    experience_fit: str = "unclear"
    evaluation_reason: str = ""
    evaluation_evidence: list[str] = field(default_factory=list)
    evaluation_confidence: float = 0.0
    profile_fit_score: float = 0.0
    profile_fit_band: str = "unavailable"
    profile_fit_reasons: list[str] = field(default_factory=list)


@dataclass
class SourceHealth:
    company: str
    source: str
    status: str
    http_code: Optional[int]
    jobs_found: int
    reason: Optional[str] = None
