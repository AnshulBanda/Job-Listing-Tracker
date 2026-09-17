import sqlite3
from pathlib import Path
import json

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tracker.sqlite3"


def initialize_database():
    """Create local tracking tables if they do not already exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute("PRAGMA foreign_keys = ON")

        with connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    retrieval_status TEXT NOT NULL DEFAULT 'pending',
                    description TEXT,
                    http_status INTEGER,
                    final_url TEXT,
                    last_error TEXT,
                    last_attempt_at TEXT,
                    retrieved_at TEXT,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS job_messages (
                    job_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    PRIMARY KEY (job_id, message_id),
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                );

                CREATE TABLE IF NOT EXISTS emails (
                    message_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    internal_date_ms INTEGER,
                    processing_status TEXT NOT NULL DEFAULT 'pending',
                    first_recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
    finally:
        connection.close()

def register_jobs(jobs):
    """Register jobs and source emails without replacing saved results."""
    initialize_database()
    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        # Commit all registrations together; roll back if anything fails.
        with connection:
            for job in jobs:
                connection.execute(
                    """
                    INSERT INTO jobs (job_id, url)
                    VALUES (?, ?)
                    ON CONFLICT(job_id) DO NOTHING
                    """,
                    (job["job_id"], job["url"]),
                )

                connection.executemany(
                    """
                    INSERT INTO job_messages (job_id, message_id)
                    VALUES (?, ?)
                    ON CONFLICT(job_id, message_id) DO NOTHING
                    """,
                    [
                        (job["job_id"], message_id)
                        for message_id in job["message_ids"]
                    ],
                )

        return {
            "jobs": connection.execute(
                "SELECT COUNT(*) FROM jobs"
            ).fetchone()[0],
            "job_messages": connection.execute(
                "SELECT COUNT(*) FROM job_messages"
            ).fetchone()[0],
        }
    finally:
        connection.close()

def save_retrieval_result(result):
    """Record an attempt, preserving any previously retrieved description."""
    status = result["status"]
    description = result.get("description")

    if status == "retrieved":
        if not isinstance(description, str) or not description.strip():
            raise ValueError("A successful retrieval needs a description.")
    else:
        description = None

    connection = sqlite3.connect(DB_PATH)
    try:
        with connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET retrieval_status = ?,
                    description = COALESCE(?, description),
                    http_status = ?,
                    final_url = ?,
                    last_error = ?,
                    last_attempt_at = CURRENT_TIMESTAMP,
                    retrieved_at = CASE
                        WHEN ? = 'retrieved' THEN CURRENT_TIMESTAMP
                        ELSE retrieved_at
                    END
                WHERE job_id = ?
                """,
                (
                    status,
                    description,
                    result.get("http_status"),
                    result.get("final_url"),
                    result.get("error"),
                    status,
                    result["job_id"],
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Job must be registered first: {result['job_id']}"
                )
    finally:
        connection.close()

def register_saved_emails():
    """Register existing email files without marking them processed."""
    initialize_database()
    email_dir = (
        Path(__file__).resolve().parent.parent
        / "component1_gmail"
        / "data"
    )
    connection = sqlite3.connect(DB_PATH)

    try:
        with connection:
            for path in sorted(email_dir.glob("*.json")):
                email = json.loads(path.read_text(encoding="utf-8"))

                if email["message_id"] != path.stem:
                    raise ValueError(f"Message ID mismatch: {path.name}")

                timestamp = email.get("internal_date_ms")

                connection.execute(
                    """
                    INSERT INTO emails (
                        message_id, thread_id, source, internal_date_ms
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(message_id) DO NOTHING
                    """,
                    (
                        email["message_id"],
                        email["thread_id"],
                        email["source"],
                        int(timestamp) if timestamp is not None else None,
                    ),
                )

        return connection.execute(
            "SELECT COUNT(*) FROM emails"
        ).fetchone()[0]
    finally:
        connection.close()

def register_email(email):
    """Record one downloaded email without changing its processing status."""
    connection = sqlite3.connect(DB_PATH)
    try:
        timestamp = email.get("internal_date_ms")

        with connection:
            connection.execute(
                """
                INSERT INTO emails (
                    message_id, thread_id, source, internal_date_ms
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(message_id) DO NOTHING
                """,
                (
                    email["message_id"],
                    email["thread_id"],
                    email["source"],
                    int(timestamp) if timestamp is not None else None,
                ),
            )
    finally:
        connection.close()


def get_processed_message_ids():
    """Return emails whose downstream processing is complete."""
    connection = sqlite3.connect(DB_PATH)
    try:
        rows = connection.execute(
            """
            SELECT message_id
            FROM emails
            WHERE processing_status = 'processed'
            """
        ).fetchall()

        return {row[0] for row in rows}
    finally:
        connection.close()
        
if __name__ == "__main__":
    from linkedin import collect_linkedin_jobs

    counts = register_jobs(collect_linkedin_jobs())
    print(f"Stored jobs: {counts['jobs']}")
    print(f"Job-to-email links: {counts['job_messages']}")
    email_count = register_saved_emails()
    print(f"Registered emails: {email_count}")