"""Moon phase: the moon as it looks on a given date (today by default).

The phase is calculated locally from the length of the lunar month, so no internet connection
is needed.

    python moon_phase.py [2026-12-24]
"""
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, font  # noqa: E402

SYNODIC_MONTH = 29.530588853
NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)  # a known new moon
NAMES = ["New moon", "Waxing crescent", "First quarter", "Waxing gibbous",
         "Full moon", "Waning gibbous", "Last quarter", "Waning crescent"]


def phase(day: datetime) -> float:
    """0 = new moon, 0.5 = full moon."""
    return ((day - NEW_MOON).total_seconds() / 86400 / SYNODIC_MONTH) % 1


def draw_moon(p: float, day: datetime) -> Image.Image:
    img = Image.new("RGB", (240, 280), "#05070F")
    d = ImageDraw.Draw(img)
    cx, cy, r = 120, 115, 80
    lit = (1 - math.cos(2 * math.pi * p)) / 2          # lit fraction of the disc
    for y in range(-r, r + 1):                         # draw the lit part row by row
        half = math.sqrt(r * r - y * y)
        edge = half * math.cos(2 * math.pi * p)        # where the shadow line crosses this row
        # Waxing: lit on the right of the shadow line; waning: lit on the left.
        x0, x1 = (cx + edge, cx + half) if p < 0.5 else (cx - half, cx - edge)
        d.line((cx - half, cy + y, cx + half, cy + y), fill="#22252E")
        if x1 > x0:
            d.line((x0, cy + y, x1, cy + y), fill="#F2EBD3")
    name = NAMES[int((p * 8) + 0.5) % 8]
    d.text((120, 225), name, font=font(26), fill="white", anchor="mm")
    d.text((120, 255), f"{day:%d.%m.%Y} · {lit * 100:.0f} %", font=font(18), fill="#9AA0B0", anchor="mm")
    return img


def main():
    day = datetime.strptime(sys.argv[1], "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc) \
        if len(sys.argv) > 1 else datetime.now(timezone.utc)
    p = phase(day)
    with BusyTag.connect() as tag:
        tag.show_image(draw_moon(p, day), "moon.png")
        tag.set_color("40408A")
    print(f"{day:%Y-%m-%d}: {NAMES[int((p * 8) + 0.5) % 8]}")


if __name__ == "__main__":
    main()
