import os
from dotenv import load_dotenv
from notion_client import Client


load_dotenv()

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PARENT_PAGE_ID = os.environ["NOTION_PARENT_PAGE_ID"]

notion = Client(auth=NOTION_TOKEN)

def find_database_id(title: str) -> str | None:
    """Find a database directly inside our configured parent page."""
    cursor = None

    while True:
        # Check every batch and return children in batches
        response = notion.blocks.children.list(
            block_id=PARENT_PAGE_ID,
            start_cursor=cursor,
            page_size=100,
        )

        for block in response["results"]:
            # ignore ordinary page contents, such as paragraphs
            if block["type"] != "child_database":
                continue

            if block["child_database"]["title"] == title:
                return block["id"]

        if not response["has_more"]:
            return None

        cursor = response["next_cursor"]

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

job_opportunities_id = find_database_id("Job Opportunities")

if job_opportunities_id is None:
    job_opportunities_db = notion.databases.create(
        parent={"type": "page_id", "page_id": PARENT_PAGE_ID},
        title=[{"type": "text", "text": {"content": "Job Opportunities"}}],
        # The data source holds the database's property schema.
        initial_data_source={
            "properties": job_opportunities_schema,
        },
    )

    job_opportunities_id = job_opportunities_db["id"]
    print(f"Created Job Opportunities database: {job_opportunities_id}")
else:
    print(f"Using existing Job Opportunities database: {job_opportunities_id}")


# Retrieve the database whether it was just created or reused.
job_opportunities_db = notion.databases.retrieve(job_opportunities_id)

# A database contains data sources; our setup creates exactly one.
job_data_sources = job_opportunities_db["data_sources"]

if len(job_data_sources) != 1:
    raise ValueError("Expected exactly one Job Opportunities data source.")

job_opportunities_data_source_id = job_data_sources[0]["id"]

placement_calendar_schema = {
    "Event": {"title": {}},
    "Company": {"rich_text": {}},
    "Date": {"date": {}},
    "Type": {
        "select": {
            "options": [
                {"name": "Test"},
                {"name": "Interview"},
                {"name": "Application Deadline"},
            ]
        }
    },
    "Shortlisted": {
        "select": {
            "options": [
                {"name": "Pending"},
                {"name": "Yes"},
                {"name": "No"},
            ]
        }
    },
    "Linked Opportunity": {
        "relation": {
            # Point to the table inside Job Opportunities.
            "data_source_id": job_opportunities_data_source_id,
            "type": "single_property",
            # One-way relation: the link appears on calendar events.
            "single_property": {},
        }
    },
    "Notes": {"rich_text": {}},
}

placement_calendar_id = find_database_id("Placement Calendar")

if placement_calendar_id is None:
    placement_calendar_db = notion.databases.create(
        parent={"type": "page_id", "page_id": PARENT_PAGE_ID},
        title=[{"type": "text", "text": {"content": "Placement Calendar"}}],
        initial_data_source={
            "properties": placement_calendar_schema,
        },
    )

    placement_calendar_id = placement_calendar_db["id"]
    print(f"Created Placement Calendar database: {placement_calendar_id}")
else:
    print(f"Using existing Placement Calendar database: {placement_calendar_id}")