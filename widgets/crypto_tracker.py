"""Crypto tracker: the price of a trading pair, with green or red LEDs when it moves.

Prices come from the public OKX market API; no account is needed.

    python crypto_tracker.py [BTC-USDT] [--seconds 30]
"""
import argparse
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, text_image  # noqa: E402


def price(pair: str) -> tuple[float, float]:
    """Last price and the price 24 hours ago."""
    r = requests.get("https://www.okx.com/api/v5/market/ticker", params={"instId": pair}, timeout=10)
    r.raise_for_status()
    data = r.json().get("data") or []
    if not data:
        raise ValueError(f"unknown pair {pair}")
    return float(data[0]["last"]), float(data[0]["open24h"])


def fmt(v: float) -> str:
    return f"{v:,.2f}" if v >= 1 else f"{v:.6f}"


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("pair", nargs="?", default="BTC-USDT", help="OKX instrument, e.g. ETH-USDT")
    p.add_argument("--seconds", type=int, default=30, help="update interval")
    a = p.parse_args()
    pair = a.pair.upper()
    with BusyTag.connect() as tag:
        last = None
        print(f"Tracking {pair}. Press Ctrl+C to stop.")
        try:
            while True:
                try:
                    now, open24 = price(pair)
                    change = (now - open24) / open24 * 100
                    color = "00D060" if change >= 0 else "FF4040"
                    lines = [(pair, 30, "BBBBBB"), (fmt(now), 56), (f"{change:+.2f} % 24h", 28, color)]
                    if now != last:
                        tag.show_image(text_image(lines, "0B0F1A", "FFFFFF"), "crypto.png")
                        if last is not None:
                            tag.set_color("00FF00" if now > last else "FF0000")
                        last = now
                    print(f"{time.strftime('%H:%M:%S')}  {pair} {fmt(now)} ({change:+.2f} %)")
                except (requests.RequestException, ValueError) as e:
                    print("Price request failed:", e)
                time.sleep(a.seconds)
        except KeyboardInterrupt:
            tag.leds_off()


if __name__ == "__main__":
    main()
