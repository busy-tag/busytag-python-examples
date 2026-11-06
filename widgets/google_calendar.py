"""Google Calendar: your current and next event, with red / orange / green LEDs.

You need an OAuth client once:

1. In https://console.cloud.google.com create a project and enable the Google Calendar API.
2. Configure the OAuth consent screen (External, add yourself as a test user).
3. Under Credentials create an OAuth client ID of type "Desktop app" and download the JSON.
4. Save it as credentials.json next to this script (or pass --credentials).

On the first run a browser window asks you to allow read access to your calendar. The sign-in
is cached in google_token.json next to this script.

    python google_calendar.py [--calendar primary] [--seconds 60]
"""
import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag  # noqa: E402
from calendar_display import Event, update  # noqa: E402

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN = Path(__file__).with_name("google_token.json")


def credentials(client_file: str) -> Credentials:
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        creds = InstalledAppFlow.from_client_secrets_file(client_file, SCOPES).run_local_server(port=0)
    TOKEN.write_text(creds.to_json())
    return creds


def parse(v: dict) -> tuple[datetime, bool]:
    if "dateTime" in v:
        return datetime.fromisoformat(v["dateTime"].replace("Z", "+00:00")), False
    return datetime.fromisoformat(v["date"]).replace(tzinfo=datetime.now().astimezone().tzinfo), True


def events(creds: Credentials, calendar: str) -> list[Event]:
    now = datetime.now(timezone.utc)
    r = requests.get(f"https://www.googleapis.com/calendar/v3/calendars/{calendar}/events", timeout=15,
                     headers={"Authorization": f"Bearer {creds.token}"},
                     params={"timeMin": now.isoformat(), "timeMax": (now + timedelta(days=2)).isoformat(),
                             "singleEvents": "true", "orderBy": "startTime", "maxResults": 50})
    r.raise_for_status()
    out = []
    for e in r.json().get("items", []):
        if e.get("transparency") == "transparent":  # marked as "free"
            continue
        start, all_day = parse(e["start"])
        end, _ = parse(e["end"])
        out.append(Event(e.get("summary") or "(no title)", start, end, all_day))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--credentials", default=str(Path(__file__).with_name("credentials.json")))
    p.add_argument("--calendar", default="primary", help="calendar ID, e.g. an e-mail address")
    p.add_argument("--seconds", type=int, default=60, help="update interval")
    a = p.parse_args()
    creds = credentials(a.credentials)  # sign in before taking the serial port
    with BusyTag.connect() as tag:
        state = {}
        print("Press Ctrl+C to stop.")
        try:
            while True:
                try:
                    if not creds.valid:
                        creds = credentials(a.credentials)
                    update(tag, events(creds, a.calendar), state)
                except requests.RequestException as e:
                    print("Calendar request failed:", e)
                time.sleep(a.seconds)
        except KeyboardInterrupt:
            tag.leds_off()


if __name__ == "__main__":
    main()
