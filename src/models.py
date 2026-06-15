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
    score: float = 0.0
    why_matched: list[str] = field(default_factory=list)


@dataclass
class SourceHealth:
    company: str
    source: str
    status: str
    http_code: Optional[int]
    jobs_found: int
    reason: Optional[str] = None
