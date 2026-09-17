import re

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def fetch_linkedin_description(job_id):
    """Fetch one public job description without saving files."""
    job_id = str(job_id)
    if not job_id.isdigit():
        raise ValueError("LinkedIn job ID must contain only digits.")

    url = f"https://www.linkedin.com/jobs/view/{job_id}/"
    result = {
        "job_id": job_id,
        "url": url,
        "status": None,
        "description": None,
    }

    try:
        response = requests.get(url, timeout=20)
    except requests.RequestException as error:
        return {**result, "status": "request_failed", "error": str(error)}

    result["http_status"] = response.status_code
    result["final_url"] = response.url

    if response.status_code != 200:
        return {**result, "status": "http_error"}

    # A search or sign-in page must not become this job's description.
    final = urlparse(response.url)
    same_job = (
        final.hostname in {
            "linkedin.com",
            "www.linkedin.com",
            "in.linkedin.com",
        }
        and re.search(
            rf"/jobs/view/(?:[^/]*-)?{job_id}/?$",
            final.path,
        )
    )
    if not same_job:
        return {**result, "status": "redirected"}

    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.select_one(".show-more-less-html__markup")
    description = (
        container.get_text(separator="\n", strip=True)
        if container else ""
    )

    if not description:
        return {**result, "status": "description_missing"}

    return {
        **result,
        "status": "retrieved",
        "description": description,
    }

if __name__ == "__main__":
    import time

    for index, job_id in enumerate(["4464897809", "4452931075"]):
        if index:
            time.sleep(3)

        result = fetch_linkedin_description(job_id)

        print(f"\nJob: {job_id}")
        print("Status:", result["status"])
        print("HTTP status:", result.get("http_status"))
        print("Final URL:", result.get("final_url"))
        print("Description characters:", len(result["description"] or ""))

        if result.get("error"):
            print("Error:", result["error"])