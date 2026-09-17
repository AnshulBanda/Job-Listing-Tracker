import requests
from bs4 import BeautifulSoup

import json
from pathlib import Path
from linkedin import extract_linkedin_jobs

email_dir = (
    Path(__file__).resolve().parent.parent
    / "component1_gmail"
    / "data"
)

emails = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in email_dir.glob("*.json")
]
emails = [
    email for email in emails
    if email.get("source") == "LinkedIn Jobs"
]
emails.sort(
    key=lambda email: int(email.get("internal_date_ms") or 0),
    reverse=True,
)

# Pick the first job from the newest email containing job links.
url = None
for email in emails:
    jobs = extract_linkedin_jobs(email["body_text"])
    if jobs:
        url = jobs[0]["url"]
        print("Email date:", email["date"])
        print("Requested URL:", url)
        break

if url is None:
    raise SystemExit("No LinkedIn job links found.")

try:
    # Test one public page with a bounded waiting time.
    response = requests.get(url, timeout=20)

    print("HTTP status:", response.status_code)
    print("Final URL:", response.url)

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else "(none)"
    print("Page title:", title)

    # Check for structured job data without saving the page.
    scripts = soup.find_all("script", type="application/ld+json")
    has_job_data = any("JobPosting" in script.get_text() for script in scripts)
    print("Contains JobPosting structured data:", has_job_data)

    # Look for the description in LinkedIn's public job-page HTML.
    description = soup.select_one(
        ".show-more-less-html__markup"
    )

    if description:
        text = description.get_text(separator="\n", strip=True)
        print("\nDescription characters:", len(text))
        print("\nDescription preview:")
        print(text[:2000])
    else:
        print("\nDescription container not found.")

except requests.RequestException as error:
    print("Request failed:", error)