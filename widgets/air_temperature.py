"""Air temperature: the current temperature where you are, updated every 10 minutes.

Your location comes from your IP address (ipinfo.io) or from --lat/--lon, the weather from the
free Open-Meteo API. No account or key is needed. The LEDs show the temperature as a colour.

    python air_temperature.py [--lat 56.95 --lon 24.11 --city Riga]
"""
import argparse
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, text_image  # noqa: E402


def locate() -> tuple[float, float, str]:
    info = requests.get("https://ipinfo.io/json", timeout=10).json()
    lat, lon = info["loc"].split(",")
    return float(lat), float(lon), info.get("city", "")


def temperature(lat: float, lon: float) -> float:
    r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=10,
                     params={"latitude": lat, "longitude": lon, "current": "temperature_2m"})
    r.raise_for_status()
    return r.json()["current"]["temperature_2m"]


def led_color(t: float) -> str:
    for limit, color in [(0, "4060FF"), (10, "00C0FF"), (20, "00D040"), (28, "FFA000")]:
        if t < limit:
            return color
    return "FF2000"


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--city", default="")
    p.add_argument("--minutes", type=int, default=10, help="update interval")
    a = p.parse_args()
    lat, lon, city = (a.lat, a.lon, a.city) if a.lat is not None and a.lon is not None else locate()
    with BusyTag.connect() as tag:
        print(f"Weather for {city or f'{lat}, {lon}'}. Press Ctrl+C to stop.")
        try:
            while True:
                try:
                    t = temperature(lat, lon)
                    lines = [(city or "Temperature", 30, "BBBBBB"), (f"{t:.0f}°C", 84)]
                    tag.show_image(text_image(lines, "102030", "FFFFFF"), "air_temp.png")
                    tag.set_color(led_color(t))
                    print(f"{time.strftime('%H:%M')}  {t:.1f} °C")
                except requests.RequestException as e:
                    print("Weather request failed:", e)
                time.sleep(a.minutes * 60)
        except KeyboardInterrupt:
            tag.leds_off()


if __name__ == "__main__":
    main()
