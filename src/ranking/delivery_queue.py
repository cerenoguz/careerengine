from src.models import Job


def prioritize_pending_jobs(
    jobs: list[Job],
    pending_job_ids: set[str],
) -> list[Job]:
    """
    Put previously cap-held jobs ahead of fresh jobs while preserving the
    existing score order inside each group.
    """
    pending_jobs = [job for job in jobs if job.id in pending_job_ids]
    fresh_jobs = [job for job in jobs if job.id not in pending_job_ids]

    return pending_jobs + fresh_jobs
