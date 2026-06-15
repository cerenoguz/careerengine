import sqlite3
from datetime import date
from pathlib import Path

from src.models import Job


DATA_DIR = Path("data")
DATABASE_PATH = DATA_DIR / "careerengine.sqlite"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    return sqlite3.connect(DATABASE_PATH)


def initialize_database() -> None:
    """
    Create the seen_jobs table.

    A job is saved here only after CareerEngine recommends/shares it with the user.
    This prevents duplicate recommendations in future runs.
    """
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                url TEXT,
                date_seen TEXT NOT NULL,
                source TEXT
            );
            """
        )


def has_seen_job(job_id: str) -> bool:
    """
    Return True if this job has already been recommended/shared before.
    """
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ? LIMIT 1;",
            (job_id,),
        )

        return cursor.fetchone() is not None


def save_seen_job(job: Job) -> None:
    """
    Save one recommended job as seen.
    """
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO seen_jobs (
                job_id,
                company,
                title,
                location,
                url,
                date_seen,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                job.id,
                job.company,
                job.title,
                job.location,
                job.url,
                date.today().isoformat(),
                job.source,
            ),
        )


def save_seen_jobs(jobs: list[Job]) -> None:
    """
    Save all jobs that were recommended in the current run.
    """
    for job in jobs:
        save_seen_job(job)


def filter_new_jobs(jobs: list[Job]) -> list[Job]:
    """
    Return only jobs that have not already been recommended/shared.
    """
    return [job for job in jobs if not has_seen_job(job.id)]