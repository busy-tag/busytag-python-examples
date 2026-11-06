"""Shared drawing for the calendar widgets: what is on now and what comes next."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PIL import Image, ImageDraw

from busytag import BusyTag, font

FREE, BUSY, SOON = "00C040", "FF2020", "FFA000"


@dataclass
class Event:
    title: str
    start: datetime   # timezone-aware
    end: datetime
    all_day: bool = False


def _fit(draw, text: str, size: int, width: int):
    f = font(size)
    while draw.textlength(text, font=f) > width and len(text) > 1:
        text = text[:-2] + "…"
    return text, f


def render(now_event: Event | None, next_event: Event | None, now: datetime) -> Image.Image:
    img = Image.new("RGB", (240, 280), "#101418")
    d = ImageDraw.Draw(img)
    color = BUSY if now_event else FREE
    d.rectangle((0, 0, 240, 120), fill="#" + color)
    d.text((14, 12), "NOW", font=font(20), fill="white")
    if now_event:
        text, f = _fit(d, now_event.title, 30, 212)
        d.text((14, 42), text, font=f, fill="white")
        d.text((14, 84), f"until {now_event.end.astimezone():%H:%M}", font=font(22), fill="white")
    else:
        d.text((14, 48), "Free", font=font(44), fill="white")
    d.text((14, 140), "NEXT", font=font(20), fill="#9AA0B0")
    if next_event:
        text, f = _fit(d, next_event.title, 26, 212)
        d.text((14, 168), text, font=f, fill="white")
        start = next_event.start.astimezone()
        when = f"{start:%H:%M}" if start.date() == now.date() else f"{start:%a %d.%m %H:%M}"
        d.text((14, 206), when, font=font(22), fill="#9AA0B0")
    else:
        d.text((14, 168), "Nothing planned", font=font(24), fill="#9AA0B0")
    d.text((226, 268), f"{now:%H:%M}", font=font(14), fill="#5A6070", anchor="rb")
    return img


def update(tag: BusyTag, events: list[Event], state: dict) -> None:
    """Show the current and the next timed event, and set the LEDs: red busy, orange soon, green free."""
    now = datetime.now().astimezone()
    timed = sorted((e for e in events if not e.all_day and e.end > now), key=lambda e: e.start)
    current = next((e for e in timed if e.start <= now), None)
    upcoming = next((e for e in timed if e.start > now), None)
    led = BUSY if current else SOON if upcoming and (upcoming.start - now).total_seconds() < 600 else FREE
    key = (current and (current.title, current.end), upcoming and (upcoming.title, upcoming.start), now.strftime("%H:%M"))
    if key != state.get("key"):
        tag.show_image(render(current, upcoming, now), "calendar.png")
        state["key"] = key
    if led != state.get("led"):
        tag.set_color(led)
        state["led"] = led
