"""Lesson 6: show how long the computer has been running.

Uses psutil for the boot time and refreshes the picture once a minute.
"""
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, text_image  # noqa: E402


def main():
    with BusyTag.connect() as tag:
        print("Press Ctrl+C to stop.")
        try:
            while True:
                up = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
                hours, rest = divmod(up.seconds, 3600)
                lines = [("Uptime", 34, "AAAAAA"), (f"{up.days} days", 44), (f"{hours} hours", 44),
                         (f"{rest // 60} minutes", 44)]
                tag.show_image(text_image(lines, "FFFFFF", "000000"), "uptime.png")
                print(f"Uptime {up.days} d {hours} h {rest // 60} min")
                time.sleep(60 - datetime.now().second)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
