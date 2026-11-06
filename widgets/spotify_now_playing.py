"""Spotify now playing: album art, track and artist of what you are listening to.

You need a Spotify app once:

1. In https://developer.spotify.com/dashboard create an app and select "Web API".
2. Add the redirect URI http://127.0.0.1:8888/callback (exactly this).
3. Copy the Client ID and pass it with --client-id or SPOTIFY_CLIENT_ID.

The script signs in with PKCE, so no client secret is needed. On the first run a browser window
opens; the sign-in is cached in spotify_token.json next to this script.

    python spotify_now_playing.py --client-id <id>
"""
import argparse
import base64
import hashlib
import io
import json
import os
import secrets
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, font, text_image  # noqa: E402

REDIRECT = "http://127.0.0.1:8888/callback"
SCOPE = "user-read-currently-playing user-read-playback-state"
TOKEN = Path(__file__).with_name("spotify_token.json")


def sign_in(client_id: str) -> dict:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    result = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            q = parse_qs(urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Signed in. You can close this window.")

        def log_message(self, *_):
            pass

    server = HTTPServer(("127.0.0.1", 8888), Callback)
    webbrowser.open("https://accounts.spotify.com/authorize?" + urlencode({
        "client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT, "scope": SCOPE,
        "code_challenge_method": "S256", "code_challenge": challenge, "state": state}))
    print("Sign in to Spotify in the browser window that opened…")
    while "code" not in result and "error" not in result:
        server.handle_request()
    server.server_close()
    if result.get("state") != state or "code" not in result:
        raise RuntimeError(f"Spotify sign-in failed: {result.get('error', 'state mismatch')}")
    return _token(client_id, {"grant_type": "authorization_code", "code": result["code"],
                              "redirect_uri": REDIRECT, "code_verifier": verifier})


def _token(client_id: str, data: dict) -> dict:
    r = requests.post("https://accounts.spotify.com/api/token", data={**data, "client_id": client_id}, timeout=15)
    r.raise_for_status()
    tok = r.json()
    tok["expires_at"] = time.time() + tok["expires_in"] - 60
    if "refresh_token" not in tok and "refresh_token" in data:
        tok["refresh_token"] = data["refresh_token"]
    TOKEN.write_text(json.dumps(tok))
    return tok


def access_token(client_id: str) -> str:
    tok = json.loads(TOKEN.read_text()) if TOKEN.exists() else sign_in(client_id)
    if time.time() > tok["expires_at"]:
        tok = _token(client_id, {"grant_type": "refresh_token", "refresh_token": tok["refresh_token"]})
    return tok["access_token"]


def now_playing(token: str) -> dict | None:
    r = requests.get("https://api.spotify.com/v1/me/player/currently-playing", timeout=10,
                     headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 204 or not r.content:
        return None
    r.raise_for_status()
    data = r.json()
    item = data.get("item")
    if not item or not data.get("is_playing"):
        return None
    images = item.get("album", {}).get("images") or item.get("show", {}).get("images") or []
    artists = ", ".join(a["name"] for a in item.get("artists", [])) or item.get("show", {}).get("name", "")
    return {"id": item["id"], "title": item["name"], "artist": artists, "art": images[0]["url"] if images else None}


def render(track: dict) -> Image.Image:
    img = Image.new("RGB", (240, 280), "#121212")
    if track["art"]:
        art = Image.open(io.BytesIO(requests.get(track["art"], timeout=15).content)).convert("RGB")
        img.paste(art.resize((200, 200)), (20, 12))
    d = ImageDraw.Draw(img)
    for text, size, color, y in [(track["title"], 22, "white", 226), (track["artist"], 17, "#B3B3B3", 254)]:
        f = font(size)
        while d.textlength(text, font=f) > 224 and len(text) > 1:
            text = text[:-2] + "…"
        d.text((120, y), text, font=f, fill=color, anchor="mm")
    return img


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--client-id", default=os.environ.get("SPOTIFY_CLIENT_ID"), help="Spotify app client ID")
    p.add_argument("--seconds", type=int, default=5, help="how often to check the player")
    a = p.parse_args()
    if not a.client_id:
        p.error("a client ID is needed: --client-id or SPOTIFY_CLIENT_ID (see the instructions in this file)")
    access_token(a.client_id)  # sign in before taking the serial port
    with BusyTag.connect() as tag:
        shown = "start"
        print("Press Ctrl+C to stop.")
        try:
            while True:
                try:
                    track = now_playing(access_token(a.client_id))
                    if (track and track["id"]) != shown:
                        if track:
                            tag.show_image(render(track), "spotify.png")
                            tag.set_color("1DB954")
                            print(f"{track['title']} – {track['artist']}")
                        else:
                            tag.show_image(text_image([("Spotify", 36, "1DB954"), ("Paused", 30, "B3B3B3")], "121212"),
                                           "spotify.png")
                            tag.leds_off()
                            print("Nothing playing")
                        shown = track and track["id"]
                except requests.RequestException as e:
                    print("Spotify request failed:", e)
                time.sleep(a.seconds)
        except KeyboardInterrupt:
            tag.leds_off()


if __name__ == "__main__":
    main()
