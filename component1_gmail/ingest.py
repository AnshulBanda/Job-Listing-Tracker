from auth import get_gmail_service
import base64
from email.message import Message
from bs4 import BeautifulSoup
import json
from pathlib import Path

# Include read emails too, so opening an alert doesn't exclude it.
PES_QUERY = (
    "{from:placementsupport@pes.edu from:pesuplacements@pes.edu} "
    "newer_than:30d"
)

# Store downloaded email records beside this script.
DATA_DIR = Path(__file__).resolve().parent / "data"

def decode_body_part(service, message_id, part):
    """Retrieve a body part and decode its bytes into text."""
    body = part.get("body", {})

    # Some body parts are stored separately by Gmail.
    if body.get("attachmentId"):
        body = service.users().messages().attachments().get(
            userId="me",
            messageId=message_id,
            id=body["attachmentId"],
        ).execute(num_retries=7)

    data = body.get("data", "")
    if not data:
        return ""

    # Restore any missing base64 padding before decoding.
    data += "=" * (-len(data) % 4)
    raw_bytes = base64.urlsafe_b64decode(data)

    # Read the character encoding declared by this email part.
    mime_headers = Message()
    for header in part.get("headers", []):
        if header["name"].lower() == "content-type":
            mime_headers["Content-Type"] = header["value"]
            break

    charset = mime_headers.get_content_charset() or "utf-8"

    try:
        return raw_bytes.decode(charset, errors="replace")
    except LookupError:
        # Fall back when an email declares an unknown encoding.
        return raw_bytes.decode("utf-8", errors="replace")

def html_to_text(html):
    """Convert HTML into readable text while preserving link URLs."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove content that isn't part of the readable message.
    for element in soup(["script", "style", "head"]):
        element.decompose()

    # Keep link destinations, including links labelled "Apply here".
    for link in soup.find_all("a"):
        label = link.get_text(" ", strip=True)
        url = (link.get("href") or "").strip()

        if url and url != label:
            link.replace_with(f"{label} ({url})" if label else url)

    # Preserve useful image descriptions when available.
    for image in soup.find_all("img"):
        image.replace_with(image.get("alt") or "")

    text = soup.get_text(separator="\n")

    # Remove empty lines and surrounding whitespace.
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)

def extract_body(service, message_id, payload):
    """Choose alternative versions while preserving separate body sections."""
    # Exclude attachments at every level of the message.
    headers = {
        header["name"].lower(): header["value"]
        for header in payload.get("headers", [])
    }
    disposition = headers.get("content-disposition", "")
    is_attachment = (
        disposition.split(";", 1)[0].strip().lower() == "attachment"
    )

    if payload.get("filename") or is_attachment:
        return "", "missing"

    mime_type = payload.get("mimeType", "").lower()

    # Decode individual text parts.
    if mime_type in {"text/plain", "text/html"}:
        text = decode_body_part(service, message_id, payload)

        if mime_type == "text/html":
            text = html_to_text(text)

        text = text.strip()
        if not text:
            return "", "missing"

        source = "plain" if mime_type == "text/plain" else "html"
        return text, source

    if not mime_type.startswith("multipart/"):
        return "", "missing"

    # Process each child, which may itself contain nested sections.
    sections = []
    for child in payload.get("parts", []):
        text, source = extract_body(service, message_id, child)
        if text:
            sections.append((text, source))

    if not sections:
        return "", "missing"

    if mime_type == "multipart/alternative":
        # These are versions of the same content: select just one.
        for text, source in sections:
            if source == "plain":
                return text, source

        return sections[-1]

    # Other multipart containers can hold separate body sections.
    combined = "\n\n".join(text for text, _ in sections)
    sources = {source for _, source in sections}
    source = sources.pop() if len(sources) == 1 else "mixed"

    return combined, source

def save_email_record(email, headers, body_text, body_source):
    """Save one email as a local JSON record."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "message_id": email["id"],
        "thread_id": email["threadId"],
        "source": "PES Placements",
        "from": headers.get("from", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "internal_date_ms": email.get("internalDate"),
        "body_text": body_text,
        "body_source": body_source,
    }

    output_path = DATA_DIR / f"{email['id']}.json"
    output_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path

def iter_message_ids(service, query):
    """Yield matching message IDs across every results page."""
    page_token = None

    while True:
        response = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=100,
            pageToken=page_token,
        ).execute(num_retries=7)

        for message in response.get("messages", []):
            yield message["id"]

        page_token = response.get("nextPageToken")
        if not page_token:
            break

def main():
    service = get_gmail_service()

    saved_count = 0
    skipped_count = 0

    for message_id in iter_message_ids(service, PES_QUERY):
        output_path = DATA_DIR / f"{message_id}.json"

        # A saved record means this email was already downloaded.
        if output_path.exists():
            skipped_count += 1
            continue

        # Fetch the full message, including headers and body parts.
        email = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute(num_retries=7)

        # Normalize header names so lookups are case-insensitive.
        headers = {
            header["name"].lower(): header["value"]
            for header in email.get("payload", {}).get("headers", [])
        }

        print()
        print(f"Message ID: {message_id}")
        print(f"From: {headers.get('from', '(missing)')}")
        print(f"Subject: {headers.get('subject', '(missing)')}")
        print(f"Date: {headers.get('date', '(missing)')}")
        body_text, body_source = extract_body(
            service,
            message_id,
            email.get("payload", {}),
        )
        saved_path = save_email_record(
            email, headers, body_text, body_source
        )
        saved_count += 1
        print(f"Saved: {saved_path.name}")
        print(f"Body source: {body_source}")
        print(f"Body characters: {len(body_text)}")
        print("Preview:")
        print(body_text[:400])
        print(f"Body MIME type: {email.get('payload', {}).get('mimeType', '(missing)')}")

    print(f"\nFinished: {saved_count} saved, {skipped_count} already downloaded.")


if __name__ == "__main__":
    main()