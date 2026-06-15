import hashlib


def create_job_id(company: str, title: str, location: str, url: str) -> str:
    raw = f"{company}|{title}|{location}|{url}".lower().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
