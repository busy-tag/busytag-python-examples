"""Outlook calendar: your current and next meeting, with red / orange / green LEDs.

Reads the calendar through Microsoft Graph. You need your own app registration once:

1. In https://entra.microsoft.com go to App registrations > New registration. Choose
   "Accounts in any organizational directory and personal Microsoft accounts".
2. Under Authentication > Advanced settings set "Allow public client flows" to Yes.
3. Under API permissions add Microsoft Graph > Delegated > Calendars.Read.
4. Copy the Application (client) ID and pass it with --client-id or OUTLOOK_CLIENT_ID.

On the first run the script prints a code to enter at https://microsoft.com/devicelogin.
The sign-in is cached in outlook_token.json next to this script.

    python outlook_calendar.py --client-id <id> [--seconds 60]
"""
import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import msal
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag  # noqa: E402
from calendar_display import Event, update  # noqa: E402

SCOPES = ["Calendars.Read"]
CACHE = Path(__file__).with_name("outlook_token.json")


def token(client_id: str) -> str:
    cache = msal.SerializableTokenCache()
    if CACHE.exists():
        cache.deserialize(CACHE.read_text())
    app = msal.PublicClientApplication(client_id, authority="https://login.microsoftonline.com/common",
                                       token_cache=cache)
    accounts = app.get_accounts()
    result = app.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None
    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "sign-in failed"))
    if cache.has_state_changed:
        CACHE.write_text(cache.serialize())
    return result["access_token"]


def events(access_token: str) -> list[Event]:
    now = datetime.now(timezone.utc)
    r = requests.get("https://graph.microsoft.com/v1.0/me/calendarView", timeout=15,
                     headers={"Authorization": f"Bearer {access_token}", "Prefer": 'outlook.timezone="UTC"'},
                     params={"startDateTime": now.isoformat(), "endDateTime": (now + timedelta(days=2)).isoformat(),
                             "$select": "subject,start,end,isAllDay,showAs,isCancelled", "$orderby": "start/dateTime",
                             "$top": "50"})
    r.raise_for_status()
    out = []
    for e in r.json().get("value", []):
        if e.get("isCancelled") or e.get("showAs") == "free":
            continue
        parse = lambda v: datetime.fromisoformat(v["dateTime"][:26]).replace(tzinfo=timezone.utc)  # noqa: E731
        out.append(Event(e.get("subject") or "(no title)", parse(e["start"]), parse(e["end"]), e.get("isAllDay", False)))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--client-id", default=os.environ.get("OUTLOOK_CLIENT_ID"), help="app registration client ID")
    p.add_argument("--seconds", type=int, default=60, help="update interval")
    a = p.parse_args()
    if not a.client_id:
        p.error("a client ID is needed: --client-id or OUTLOOK_CLIENT_ID (see the instructions in this file)")
    token(a.client_id)  # sign in before taking the serial port
    with BusyTag.connect() as tag:
        state = {}
        print("Press Ctrl+C to stop.")
        try:
            while True:
                try:
                    update(tag, events(token(a.client_id)), state)
                except (requests.RequestException, RuntimeError) as e:
                    print("Calendar request failed:", e)
                time.sleep(a.seconds)
        except KeyboardInterrupt:
            tag.leds_off()


if __name__ == "__main__":
    main()
