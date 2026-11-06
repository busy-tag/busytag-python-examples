"""Mouse click counter: a live count of your left mouse clicks.

The clicks are counted with pynput. The screen is refreshed at most once a second, so fast
clicking does not queue up uploads.

    python mouse_click_counter.py
"""
import sys
import threading
import time
from pathlib import Path

from pynput import mouse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, text_image  # noqa: E402

count = 0
lock = threading.Lock()


def on_click(_x, _y, button, pressed):
    global count
    if pressed and button == mouse.Button.left:
        with lock:
            count += 1


def main():
    listener = mouse.Listener(on_click=on_click)
    listener.start()
    with BusyTag.connect() as tag:
        shown = None
        print("Counting left clicks. Press Ctrl+C to stop.")
        try:
            while True:
                with lock:
                    n = count
                if n != shown:
                    tag.show_image(text_image([("Clicks", 34, "9AA0B0"), (f"{n:,}", 80)], "1A0B2E"), "clicks.png")
                    tag.set_color("FFFFFF" if n % 2 else "7D2BC4")
                    shown = n
                time.sleep(1)
        except KeyboardInterrupt:
            listener.stop()
            tag.leds_off()


if __name__ == "__main__":
    main()
