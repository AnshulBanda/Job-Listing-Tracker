import re
import json
from pathlib import Path


# Match both email links (/comm/jobs/view/) and regular job links.
JOB_LINK_PATTERN = re.compile(
    r"https?://(?:www\.)?linkedin\.com/"
    r"(?:comm/)?jobs/view/(\d+)(?=[/?#\s<>)]|$)",
    re.IGNORECASE,
)


def extract_linkedin_jobs(body_text):
    """Return unique job IDs and clean URLs from one email."""
    jobs = {}

    for match in JOB_LINK_PATTERN.finditer(body_text):
        job_id = match.group(1)

        # Using the ID as the key removes repeated links.
        jobs[job_id] = {
            "job_id": job_id,
            "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
        }

    return list(jobs.values())

def collect_linkedin_jobs():
    """Deduplicate jobs across saved emails, preserving their message IDs."""
    email_dir = (
        Path(__file__).resolve().parent.parent
        / "component1_gmail"
        / "data"
    )
    jobs = {}

    for email_path in sorted(email_dir.glob("*.json")):
        email = json.loads(email_path.read_text(encoding="utf-8"))

        if email.get("source") != "LinkedIn Jobs":
            continue

        for job in extract_linkedin_jobs(email["body_text"]):
            job_id = job["job_id"]

            if job_id not in jobs:
                jobs[job_id] = {
                    **job,
                    "message_ids": [],
                }

            # Retain which emails mentioned this opportunity.
            jobs[job_id]["message_ids"].append(email["message_id"])

    return list(jobs.values())


if __name__ == "__main__":
    jobs = collect_linkedin_jobs()
    print(f"Unique LinkedIn jobs: {len(jobs)}")

    for job in jobs[:5]:
        print(
            f"{job['job_id']} | "
            f"{len(job['message_ids'])} email(s) | "
            f"{job['url']}"
        )