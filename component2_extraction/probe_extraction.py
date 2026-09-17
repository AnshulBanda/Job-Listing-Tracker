import sqlite3

from job_parser import extract_job_details
from storage import DB_PATH


def main():
    # Open SQLite read-only for this test.
    connection = sqlite3.connect(
        DB_PATH.resolve().as_uri() + "?mode=ro",
        uri=True,
    )
    try:
        row = connection.execute(
            "SELECT description FROM jobs WHERE job_id = ?",
            ("4464897809",),
        ).fetchone()
    finally:
        connection.close()

    if not row or not row[0]:
        raise SystemExit("The sample job has no saved description.")

    print(f"Extracting from {len(row[0])} characters...")
    details = extract_job_details(row[0])
    print(details.model_dump_json(indent=2))


if __name__ == "__main__":
    main()