import os

from src.storage.database import get_connection, initialize_database


TRUSTED_DELIVERED_JOBS = [
    (
        "3f54676abcc512e5e9fa49d895036304ff9de57f5d260534805b80c45860c284",
        "Cohere",
        "Software Engineer, Data Infrastructure",
        "New York",
        "https://jobs.ashbyhq.com/cohere/6aa3cb2b-ee8b-4c92-b505-3a7509f80d7f",
        "2026-06-15",
        "ashby",
    ),
    (
        "b7558aeaac998445d2be33a84b797c36f88213e5657a18f7287d168828415120",
        "Twilio",
        "Software Engineer (L1)",
        "Remote - US",
        "https://job-boards.greenhouse.io/twilio/jobs/7681338",
        "2026-06-17",
        "greenhouse",
    ),
    (
        "d64d34b26333c0af12ca3e07316e3234b15d5c765260f2de7083daec62e9d736",
        "OpenAI",
        "Full Stack Software Engineer, Agent Enablement",
        "San Francisco",
        "https://jobs.ashbyhq.com/openai/2d7f1028-ce9b-49c7-acc8-782714ca1cf4",
        "2026-06-18",
        "ashby",
    ),
]


def main() -> None:
    if os.getenv("GITHUB_ACTIONS", "").lower() != "true":
        print("Trusted production seed skipped outside GitHub Actions.")
        return

    initialize_database()

    with get_connection() as connection:
        before_count = connection.execute(
            "SELECT COUNT(*) FROM seen_jobs;"
        ).fetchone()[0]

        connection.executemany(
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
            TRUSTED_DELIVERED_JOBS,
        )

        after_count = connection.execute(
            "SELECT COUNT(*) FROM seen_jobs;"
        ).fetchone()[0]

    print(
        "Trusted production delivery seed complete: "
        f"{after_count - before_count} inserted, "
        f"{after_count} total seen jobs."
    )


if __name__ == "__main__":
    main()
