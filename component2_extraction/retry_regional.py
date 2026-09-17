import sqlite3
import time

from descriptions import fetch_linkedin_description
from storage import DB_PATH, save_retrieval_result


def main():
    connection = sqlite3.connect(DB_PATH)
    try:
        # Retry descriptions rejected by our earlier hostname check.
        rows = connection.execute(
            """
            SELECT job_id
            FROM jobs
            WHERE retrieval_status = 'redirected'
              AND final_url LIKE 'https://in.linkedin.com/jobs/view/%'
              AND description IS NULL
            ORDER BY job_id DESC
            LIMIT ?
            """,
            (8,),
        ).fetchall()
    finally:
        connection.close()

    print(f"Regional redirects selected for retry: {len(rows)}")

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