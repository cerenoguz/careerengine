import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.models import Job


DATA_DIR = Path("data")
DATABASE_PATH = DATA_DIR / "careerengine.sqlite"
NEW_YORK_TIMEZONE = ZoneInfo("America/New_York")


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    return sqlite3.connect(DATABASE_PATH)


def current_new_york_date() -> str:
    return datetime.now(NEW_YORK_TIMEZONE).date().isoformat()


def current_new_york_timestamp() -> str:
    return datetime.now(NEW_YORK_TIMEZONE).isoformat(timespec="seconds")


def initialize_database() -> None:
    """
    Create all persistence tables used by CareerEngine.

    seen_jobs:
        Jobs that were actually emailed to the user.

    pending_recommendations:
        Qualified jobs that were held by the email cap or by a skipped
        duplicate-same-day delivery. Pending jobs remain unseen and receive
        priority in later runs.

    daily_deliveries:
        Ensures at most one successful email delivery per New York calendar day.

    run_audit:
        Records delivery and deduplication counts for diagnostics.
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

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_recommendations (
                job_id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                url TEXT,
                score REAL NOT NULL,
                source TEXT,
                first_held_date TEXT NOT NULL,
                last_observed_date TEXT NOT NULL
            );
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_deliveries (
                delivery_date TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                environment TEXT NOT NULL,
                delivered_at TEXT NOT NULL
            );
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS run_audit (
                run_id TEXT PRIMARY KEY,
                environment TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                seen_jobs_before INTEGER NOT NULL,
                qualified_jobs INTEGER NOT NULL,
                duplicate_jobs INTEGER NOT NULL,
                pending_jobs_prioritized INTEGER NOT NULL,
                held_by_email_cap INTEGER NOT NULL,
                selected_for_email INTEGER NOT NULL,
                email_sent INTEGER NOT NULL,
                skipped_due_to_daily_delivery INTEGER NOT NULL,
                seen_jobs_after INTEGER NOT NULL,
                recorded_at TEXT NOT NULL
            );
            """
        )


def get_seen_job_count() -> int:
    with get_connection() as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM seen_jobs;"
        ).fetchone()[0]


def has_seen_job(job_id: str) -> bool:
    """
    Return True only when a job was actually emailed/shared before.
    """
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ? LIMIT 1;",
            (job_id,),
        )
        return cursor.fetchone() is not None


def save_seen_job(job: Job) -> None:
    """
    Save one successfully emailed job as seen.
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
                current_new_york_date(),
                job.source,
            ),
        )


def save_seen_jobs(jobs: list[Job]) -> None:
    """
    Save only jobs that were actually delivered by email.
    """
    for job in jobs:
        save_seen_job(job)


def filter_new_jobs(jobs: list[Job]) -> list[Job]:
    """
    Return jobs that have not actually been emailed/shared before.
    """
    return [job for job in jobs if not has_seen_job(job.id)]


def get_pending_job_ids() -> set[str]:
    """
    Return the IDs of qualified jobs that were held by the email cap.
    """
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT job_id FROM pending_recommendations;"
        ).fetchall()

    return {row[0] for row in rows}


def save_pending_jobs(jobs: list[Job]) -> None:
    """
    Upsert qualified jobs that were not delivered.

    These jobs remain unseen and should receive priority in later runs.
    """
    if not jobs:
        return

    today = current_new_york_date()

    with get_connection() as connection:
        connection.executemany(
            """
            INSERT INTO pending_recommendations (
                job_id,
                company,
                title,
                location,
                url,
                score,
                source,
                first_held_date,
                last_observed_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                company = excluded.company,
                title = excluded.title,
                location = excluded.location,
                url = excluded.url,
                score = excluded.score,
                source = excluded.source,
                last_observed_date = excluded.last_observed_date;
            """,
            [
                (
                    job.id,
                    job.company,
                    job.title,
                    job.location,
                    job.url,
                    job.score,
                    job.source,
                    today,
                    today,
                )
                for job in jobs
            ],
        )


def remove_pending_jobs(job_ids: list[str]) -> None:
    """
    Remove jobs from the pending queue after they are successfully emailed.
    """
    if not job_ids:
        return

    placeholders = ", ".join("?" for _ in job_ids)

    with get_connection() as connection:
        connection.execute(
            f"DELETE FROM pending_recommendations WHERE job_id IN ({placeholders});",
            job_ids,
        )


def has_successful_delivery_for_date(delivery_date: str) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT 1 FROM daily_deliveries WHERE delivery_date = ? LIMIT 1;",
            (delivery_date,),
        )
        return cursor.fetchone() is not None


def record_successful_delivery(
    *,
    delivery_date: str,
    run_id: str,
    environment: str,
) -> None:
    """
    Record a successful daily email delivery.

    The delivery_date primary key allows one successful report per New York day.
    """
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO daily_deliveries (
                delivery_date,
                run_id,
                environment,
                delivered_at
            )
            VALUES (?, ?, ?, ?);
            """,
            (
                delivery_date,
                run_id,
                environment,
                current_new_york_timestamp(),
            ),
        )


def record_run_audit(
    *,
    run_id: str,
    environment: str,
    delivery_date: str,
    seen_jobs_before: int,
    qualified_jobs: int,
    duplicate_jobs: int,
    pending_jobs_prioritized: int,
    held_by_email_cap: int,
    selected_for_email: int,
    email_sent: bool,
    skipped_due_to_daily_delivery: bool,
    seen_jobs_after: int,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO run_audit (
                run_id,
                environment,
                delivery_date,
                seen_jobs_before,
                qualified_jobs,
                duplicate_jobs,
                pending_jobs_prioritized,
                held_by_email_cap,
                selected_for_email,
                email_sent,
                skipped_due_to_daily_delivery,
                seen_jobs_after,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                run_id,
                environment,
                delivery_date,
                seen_jobs_before,
                qualified_jobs,
                duplicate_jobs,
                pending_jobs_prioritized,
                held_by_email_cap,
                selected_for_email,
                int(email_sent),
                int(skipped_due_to_daily_delivery),
                seen_jobs_after,
                current_new_york_timestamp(),
            ),
        )
