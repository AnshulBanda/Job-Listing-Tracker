from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Read-only access to Gmail.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Resolve paths relative to this file, regardless of where we run Python.
BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"

def get_gmail_service():
    """Authorize Gmail access and return a reusable API client."""
    creds = None

    # Reuse authorization saved by an earlier run.
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(
            str(TOKEN_PATH), SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Renew access without asking you to sign in again.
            creds.refresh(Request())
        else:
            # Start browser sign-in when no usable authorization exists.
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save authorization for subsequent runs.
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)

if __name__ == "__main__":
    service = get_gmail_service()

    # Confirm which mailbox we authorized.
    profile = service.users().getProfile(userId="me").execute()
    print(f"Connected to Gmail: {profile['emailAddress']}")