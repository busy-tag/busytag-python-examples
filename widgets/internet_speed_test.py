"""Internet speed test: download and upload speed on the screen.

Uses speedtest-cli (Speedtest.net servers). The LEDs pulse blue while the test runs, then turn
green, yellow or red depending on the download speed.

    python internet_speed_test.py
"""
import sys
from pathlib import Path

import speedtest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, text_image  # noqa: E402

BLUE_PULSES = 19  # built-in pattern ID (AT+GDPL lists them)


def main():
    with BusyTag.connect() as tag:
        while True:
            tag.show_image(text_image([("Testing", 44), ("speed…", 44)], "101828"), "speed.png")
            tag.play_builtin_pattern(BLUE_PULSES)
            st = speedtest.Speedtest(secure=True)
            st.get_best_server()
            down, up = st.download() / 1e6, st.upload() / 1e6
            ping = st.results.ping
            lines = [("Download", 26, "9AA0B0"), (f"{down:.0f} Mbit/s", 44), ("Upload", 26, "9AA0B0"),
                     (f"{up:.0f} Mbit/s", 44), (f"Ping {ping:.0f} ms", 24, "9AA0B0")]
            tag.show_image(text_image(lines, "101828", spacing=6), "speed.png")
            tag.set_color("00D040" if down >= 100 else "FFA000" if down >= 25 else "FF2000")
            print(f"Download {down:.1f} Mbit/s, upload {up:.1f} Mbit/s, ping {ping:.0f} ms")
            if input("Run again? [y/N] ").strip().lower() != "y":
                break


if __name__ == "__main__":
    main()
