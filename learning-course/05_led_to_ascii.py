"""Lesson 5: draw the LED state on the screen.

The script reads the current LED colour and mask with AT+SC? and draws the device outline with a
dot for every lit LED. Change the LEDs from the Busy Tag app (or lesson 1) and watch the screen
follow.
"""
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, font  # noqa: E402

# Where each LED bit is drawn on the 240 x 280 screen.
POSITIONS = {4: (40, 40), 8: (120, 30), 16: (200, 40), 2: (30, 140), 32: (210, 140), 1: (40, 240), 64: (200, 240)}


def draw(mask: int, color: str) -> Image.Image:
    img = Image.new("RGB", (240, 280), "black")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((15, 15, 225, 265), radius=28, outline="#555555", width=3)
    lit = "#" + color if color != "000000" else "#333333"
    for bit, (x, y) in POSITIONS.items():
        on = mask & bit and color != "000000"
        d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=lit if on else None, outline=lit if on else "#555555", width=3)
    d.text((120, 140), f"{mask}\n#{color}", font=font(30), fill="white", anchor="mm", align="center")
    return img


def main():
    interval = int(input("Check every how many milliseconds [1000]: ") or 1000) / 1000
    with BusyTag.connect() as tag:
        last = None
        print("Press Ctrl+C to stop.")
        try:
            while True:
                mask, color = tag.query("AT+SC?").split(",")
                if (mask, color) != last:
                    tag.show_image(draw(int(mask), color.upper()), "lesson5.png")
                    print(f"LEDs {mask} #{color}")
                    last = (mask, color)
                time.sleep(interval)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
