"""Status light over Wi-Fi (Busy Tag 2, firmware 3.x).

Busy Tag 2 has a small HTTP server for the local network. This example sets it up once over USB,
then switches the device between Busy / Free / Away from any computer on the same network,
without a cable. See the Local Network Guide: https://busy-tag.github.io/hardware/local-network

1. Setup, with the device plugged in over USB (close the Busy Tag app first):

       python status_light.py setup --ssid MyNetwork --password MyPassword

   This joins the network, starts the server on port 8080 with a random token, and saves the
   address and token in wifi_device.json next to this script. Without --ssid the device keeps
   its current Wi-Fi connection.

2. From then on, over Wi-Fi:

       python status_light.py busy
       python status_light.py free
       python status_light.py away

The server setting is not stored on the device: after a restart, run setup again (it can keep the
same token with --token).
"""
import argparse
import json
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, BusyTagError, text_image  # noqa: E402

CONFIG = Path(__file__).with_name("wifi_device.json")
STATUSES = {
    "busy": ("Busy", "FF2020", "3A0505"),
    "free": ("Free", "20D040", "05300F"),
    "away": ("Away", "FFB000", "302005"),
}


def setup(a):
    token = a.token or secrets.token_urlsafe(24).replace("-", "").replace("_", "")[:32]
    with BusyTag.connect() as tag:
        if not tag.has_wifi:
            sys.exit("This needs firmware 3.x (Busy Tag 2). The original Busy Tag has no Wi-Fi.")
        if a.ssid:
            if tag.query("AT+WM?") == "0":
                tag.command("AT+WM=1")
            tag.command(f"AT+STA={a.ssid},{a.password}", timeout=10)
            print("Joining", a.ssid, "…")
        ip = "0.0.0.0"
        for _ in range(45):                      # the connection takes a few seconds
            ip = tag.query("AT+GIP")
            if ip != "0.0.0.0":
                break
            time.sleep(1)
        if ip == "0.0.0.0":
            sys.exit("The device is not on a Wi-Fi network. Use --ssid and --password.")
        tag.command(f"AT+LS=1,{a.port},{token}", timeout=5)
        time.sleep(1)
        print("Server:", tag.query("AT+LS?"))
    CONFIG.write_text(json.dumps({"host": ip, "port": a.port, "token": token}, indent=2))
    print(f"Ready: http://{ip}:{a.port}  (saved in {CONFIG.name})")


def set_status(name: str):
    if not CONFIG.exists():
        sys.exit("Run setup first.")
    cfg = json.loads(CONFIG.read_text())
    label, led, background = STATUSES[name]
    with BusyTag.connect_wifi(cfg["host"], cfg["port"], cfg["token"]) as tag:
        tag.show_image(text_image(label, background, led, size=72), "status.png")
        tag.set_color(led)
    print(f"{label} (via http://{cfg['host']}:{cfg['port']})")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="action", required=True)
    s = sub.add_parser("setup", help="join Wi-Fi and start the local server (over USB)")
    s.add_argument("--ssid")
    s.add_argument("--password", default="")
    s.add_argument("--port", type=int, default=8080, help="1024-65535")
    s.add_argument("--token", help="keep a known token instead of a new random one")
    for name in STATUSES:
        sub.add_parser(name, help=f"show {name} (over Wi-Fi)")
    a = p.parse_args()
    try:
        setup(a) if a.action == "setup" else set_status(a.action)
    except BusyTagError as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
