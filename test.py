from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
_ROOT = Path(__file__).resolve().parent
CLIENT_SECRET_FILE = _ROOT / "client_secret_20102510405-9bbtqpruq63hgiedpqu25cqv9tqrgck1.apps.googleusercontent.com.json"
TOKEN_FILE = _ROOT / "token.json"


def get_gmail_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def fetch_latest_messages(max_results: int = 20) -> list[dict]:
    service = get_gmail_service()
    listed = service.users().messages().list(userId="me", maxResults=max_results).execute()
    out: list[dict] = []
    for item in listed.get("messages", []):
        mid = item["id"]
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=mid,
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            )
            .execute()
        )
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        out.append(
            {
                "id": mid,
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            }
        )
    return out


if __name__ == "__main__":
    for row in fetch_latest_messages(15):
        print(row)
