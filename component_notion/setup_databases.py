import os
from dotenv import load_dotenv
from notion_client import Client


load_dotenv()

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PARENT_PAGE_ID = os.environ["NOTION_PARENT_PAGE_ID"]

notion = Client(auth=NOTION_TOKEN)


job_opportunities_schema = {
    "Company": {"title": {}},
    "Role": {"rich_text": {}},
    "Source": {"rich_text": {}},
    "Fit Score": {"number": {"format": "number"}},
    "Why it matched": {"rich_text": {}},
    "Flagged Gaps": {"rich_text": {}},
    "Deadline": {"date": {}},
    "Status": {
        "select": {
            "options": [
                {"name": "New"},
                {"name": "Applied"},
                {"name": "Rejected"},
                {"name": "Interviewing"},
                {"name": "Offer"},
            ]
        }
    },
    "Resume Used": {"rich_text": {}},
    "Apply Link": {"url": {}},
    "Date Added": {"date": {}},
}

job_opportunities_db = notion.databases.create(
    parent={"type": "page_id", "page_id": PARENT_PAGE_ID},
    title=[{"type": "text", "text": {"content": "Job Opportunities"}}],
    properties=job_opportunities_schema,
)

job_opportunities_id = job_opportunities_db["id"]
print(f"Created Job Opportunities database: {job_opportunities_id}")