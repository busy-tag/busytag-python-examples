"""Pomodoro timer: work and break countdowns on Busy Tag.

Work sessions show red LEDs and a red countdown, breaks green ones. The screen is updated every
minute, and every 10 seconds in the last minute, so the device is not flooded with uploads.
After the set number of work sessions comes a long break.

    python pomodoro_timer.py [--work 25] [--short 5] [--long 15] [--sessions 4]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, text_image  # noqa: E402

WHITE_FLASHES = 9  # built-in pattern ID played when a phase ends


def countdown(tag: BusyTag, title: str, minutes: int, color: str, background: str):
    tag.set_color(color)
    end = time.time() + minutes * 60
    while (left := end - time.time()) > 0:
        m, s = divmod(int(left + 0.999), 60)
        shown = f"{m}:{s:02d}" if m == 0 else f"{m + (s > 0)} min"
        tag.show_image(text_image([(title, 34, "DDDDDD"), (shown, 72, color)], background), "pomodoro.png")
        print(f"\r{title}: {m:02d}:{s:02d} left ", end="", flush=True)
        step = 10 if left <= 60 else (left - 60) % 60 or 60
        time.sleep(min(step, left))
    print()
    tag.play_builtin_pattern(WHITE_FLASHES)
    time.sleep(3)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--work", type=int, default=25, help="work minutes")
    p.add_argument("--short", type=int, default=5, help="short break minutes")
    p.add_argument("--long", type=int, default=15, help="long break minutes")
    p.add_argument("--sessions", type=int, default=4, help="work sessions before a long break")
    a = p.parse_args()
    with BusyTag.connect() as tag:
        print("Press Ctrl+C to stop.")
        try:
            session = 0
            while True:
                session += 1
                countdown(tag, f"Focus {session}", a.work, "FF3030", "200808")
                if session % a.sessions == 0:
                    countdown(tag, "Long break", a.long, "30D060", "08200F")
                else:
                    countdown(tag, "Break", a.short, "30D060", "08200F")
        except KeyboardInterrupt:
            tag.stop_pattern()
            tag.leds_off()
            tag.show_image(text_image("Stopped", "202020"), "pomodoro.png")


if __name__ == "__main__":
    main()
