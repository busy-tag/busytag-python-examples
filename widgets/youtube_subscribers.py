"""YouTube subscriber tracker: a channel's subscriber count, with LED effects when it changes.

Needs a YouTube Data API v3 key: in the Google Cloud console create a project, enable
"YouTube Data API v3" and create an API key under Credentials. Pass it with --key or set the
YOUTUBE_API_KEY environment variable.

    python youtube_subscribers.py @channelhandle [--minutes 5]

YouTube rounds public subscriber counts to three significant digits, so small changes on large
channels are not visible.
"""
import argparse
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, PatternStep, text_image  # noqa: E402


def channel(key: str, handle: str) -> tuple[str, int]:
    params = {"part": "snippet,statistics", "key": key}
    params["forHandle" if handle.startswith("@") else "id"] = handle
    r = requests.get("https://www.googleapis.com/youtube/v3/channels", params=params, timeout=10)
    r.raise_for_status()
    items = r.json().get("items") or []
    if not items:
        raise ValueError(f"channel {handle} not found")
    return items[0]["snippet"]["title"], int(items[0]["statistics"].get("subscriberCount", 0))


def flash(tag: BusyTag, color: str):
    tag.set_pattern([PatternStep(color, delay=150), PatternStep("000000", delay=150)])
    tag.play_pattern(5)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("channel", help="@handle or channel ID (UC...)")
    p.add_argument("--key", default=os.environ.get("YOUTUBE_API_KEY"), help="YouTube Data API key")
    p.add_argument("--minutes", type=int, default=5, help="update interval")
    a = p.parse_args()
    if not a.key:
        p.error("an API key is needed: --key or the YOUTUBE_API_KEY environment variable")
    with BusyTag.connect() as tag:
        last = None
        print("Press Ctrl+C to stop.")
        try:
            while True:
                try:
                    title, subs = channel(a.key, a.channel)
                    if subs != last:
                        lines = [("YouTube", 30, "FF3030"), (title, 26, "DDDDDD"), (f"{subs:,}", 60), ("subscribers", 24, "999999")]
                        tag.show_image(text_image(lines, "0F0F0F"), "youtube.png")
                        if last is not None:
                            flash(tag, "00FF00" if subs > last else "FF0000")
                        else:
                            tag.set_color("FF0000")
                        last = subs
                    print(f"{time.strftime('%H:%M')}  {title}: {subs:,}")
                except (requests.RequestException, ValueError) as e:
                    print("YouTube request failed:", e)
                time.sleep(a.minutes * 60)
        except KeyboardInterrupt:
            tag.leds_off()


if __name__ == "__main__":
    main()
