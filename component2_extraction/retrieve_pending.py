import sqlite3
import time

from descriptions import fetch_linkedin_description
from storage import DB_PATH, save_retrieval_result


def main():
    connection = sqlite3.connect(DB_PATH)
    try:
        # Select a bounded batch, excluding all previously attempted jobs.
        rows = connection.execute(
            """
            SELECT job_id
            FROM jobs
            WHERE retrieval_status = 'pending'
              AND last_attempt_at IS NULL
              AND description IS NULL
            ORDER BY job_id DESC
            LIMIT ?
            """,
            (5,),
        ).fetchall()
    finally:
        connection.close()

    print(f"Pending jobs selected: {len(rows)}")

    for index, (job_id,) in enumerate(rows):
        if index:
            time.sleep(3)

        result = fetch_linkedin_description(job_id)
        save_retrieval_result(result)

        print(
            f"{job_id}: {result['status']} | "
            f"{len(result['description'] or '')} description characters"
        )

        # Stop this batch if access or connectivity fails.
        if (
            result["status"] == "request_failed"
            or result.get("http_status") in {403, 429, 999}
        ):
            print("Stopping batch after an access or connection failure.")
            break


if __name__ == "__main__":
    main()