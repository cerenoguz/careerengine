import csv

from src.models import Job
from src.reporting.semantic_review_queue import save_semantic_review_queue


def make_job(
    *,
    job_id: str,
    title: str,
    score: float,
    semantic_similarity: float,
    is_internship: bool = False,
    is_new_grad: bool = False,
) -> Job:
    return Job(
        id=job_id,
        company="Example Company",
        title=title,
        location="Boston, MA",
        description="Build reliable backend services using Python and APIs.",
        url=f"https://example.com/jobs/{job_id}",
        date_posted=None,
        source="example",
        score=score,
        description_similarity=0.080,
        semantic_similarity=semantic_similarity,
        is_internship=is_internship,
        is_new_grad=is_new_grad,
    )


def test_semantic_review_queue_writes_labelable_rows(tmp_path):
    jobs = [
        make_job(
            job_id="intern",
            title="Software Engineering Intern",
            score=72,
            semantic_similarity=0.48,
            is_internship=True,
        ),
        make_job(
            job_id="new-grad",
            title="New Grad Software Engineer",
            score=70,
            semantic_similarity=0.41,
            is_new_grad=True,
        ),
        make_job(
            job_id="general",
            title="Software Engineer",
            score=63,
            semantic_similarity=0.44,
        ),
        make_job(
            job_id="disagreement",
            title="Applied AI Engineer",
            score=35,
            semantic_similarity=0.49,
        ),
    ]

    path = tmp_path / "semantic_review_queue.csv"

    save_semantic_review_queue(
        path=path,
        jobs=jobs,
        status="available",
        limit=4,
    )

    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 4
    assert {row["job_id"] for row in rows} == {
        "intern",
        "new-grad",
        "general",
        "disagreement",
    }
    assert all(row["technical_fit"] == "" for row in rows)
    assert all(row["application_priority"] == "" for row in rows)
    assert all(row["url"].startswith("https://example.com/jobs/") for row in rows)
