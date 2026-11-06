"""Lesson 2: LED colours picked from a picture.

Every few moments the script takes the colour of a random pixel of an image and sends it to the
LEDs with AT+SC. Pass your own picture as an argument, or use the built-in rainbow.

    python 02_led_color_control.py [picture.png]
"""
import random
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag  # noqa: E402


def rainbow() -> Image.Image:
    img = Image.new("HSV", (360, 1))
    img.putdata([(int(h / 360 * 255), 255, 255) for h in range(360)])
    return img.convert("RGB")


def main():
    img = Image.open(sys.argv[1]).convert("RGB") if len(sys.argv) > 1 else rainbow()
    delay_ms = int(input("Delay between colours in milliseconds (e.g. 500): ") or 500)
    with BusyTag.connect() as tag:
        tag.stop_pattern()
        print("Press Ctrl+C to stop.")
        try:
            while True:
                r, g, b = img.getpixel((random.randrange(img.width), random.randrange(img.height)))
                color = f"{r:02X}{g:02X}{b:02X}"
                tag.command(f"AT+SC=127,{color}")
                print(f"AT+SC=127,{color}")
                time.sleep(delay_ms / 1000)
        except KeyboardInterrupt:
            tag.leds_off()


if __name__ == "__main__":
    main()
