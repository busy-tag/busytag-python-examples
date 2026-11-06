"""Small helper for driving a Busy Tag from Python.

Works with firmware 2.x (Busy Tag, hardware 1.0) and firmware 3.x (Busy Tag 2, hardware 2.0)
over USB, and with firmware 3.x over Wi-Fi through the local HTTP API.

    from busytag import BusyTag

    with BusyTag.connect() as tag:          # finds the USB port by itself
        tag.set_color("FF0000")             # all LEDs red
        tag.show_image(image)               # a PIL image, scaled to 240 x 280

    with BusyTag.connect_wifi("192.168.1.42", port=8080, token="...") as tag:
        tag.show("busy.png")

The commands are documented in the AT Command Manuals at https://busy-tag.github.io/hardware.
"""
from __future__ import annotations

import io
import time
from dataclasses import dataclass

import serial
import serial.tools.list_ports

SCREEN_SIZE = (240, 280)
ALL_LEDS = 127

# LED positions as bits of the 7-bit LED mask (front view of the device).
LEDS = {
    "left bottom": 1,
    "left middle": 2,
    "left top": 4,
    "top": 8,
    "right top": 16,
    "right middle": 32,
    "right bottom": 64,
}

USB_VID = 0x303A
USB_PID = 0x81DF


class BusyTagError(RuntimeError):
    """The device answered ERROR, or did not answer."""


@dataclass
class PatternStep:
    """One step of a custom LED pattern (see AT+CP in the AT Command Manual)."""
    color: str                 # RRGGBB
    leds: int = ALL_LEDS       # LED mask; add 128 to switch off the LEDs lit by the previous step
    speed: int = 5             # fade time in ms
    delay: int = 100           # hold time in ms

    def line(self) -> str:
        return f"+CP:{self.leds},{_hex(self.color)},{self.speed},{self.delay}"


def _hex(color: str) -> str:
    color = color.strip().lstrip("#").upper()
    if len(color) != 6 or any(c not in "0123456789ABCDEF" for c in color):
        raise ValueError(f"colour must be RRGGBB, got {color!r}")
    return color


def find_ports() -> list[str]:
    """Serial ports that belong to a Busy Tag in normal mode."""
    found = [p.device for p in serial.tools.list_ports.comports()
             if p.vid == USB_VID and p.pid == USB_PID]
    if found:
        return found
    # Fallback: ask every port for its name (slower, but works when the driver hides the IDs).
    for p in serial.tools.list_ports.comports():
        try:
            with serial.Serial(p.device, 460800, timeout=0.5, write_timeout=0.5) as s:
                s.reset_input_buffer()
                s.write(b"AT+GDN\r\n")
                if b"+DN:" in s.read(64):
                    found.append(p.device)
        except (serial.SerialException, OSError):
            continue
    return found


class BusyTag:
    """A connected Busy Tag. Create it with BusyTag.connect() or BusyTag.connect_wifi()."""

    def __init__(self, transport):
        self._t = transport
        self._last_image = None

    # ---- connecting ---------------------------------------------------------------------
    @classmethod
    def connect(cls, port: str | None = None) -> "BusyTag":
        """Open the USB serial port. Without a port name the first Busy Tag found is used."""
        if port is None:
            ports = find_ports()
            if not ports:
                raise BusyTagError("No Busy Tag found. Plug it in and close the Busy Tag app, "
                                   "which keeps the serial port open.")
            port = ports[0]
        return cls(_SerialTransport(port))

    @classmethod
    def connect_wifi(cls, host: str, port: int = 80, token: str | None = None) -> "BusyTag":
        """Use the local HTTP API of firmware 3.x (see the Local Network Guide)."""
        return cls(_HttpTransport(host, port, token))

    def close(self) -> None:
        self._t.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- raw commands -------------------------------------------------------------------
    def command(self, cmd: str, timeout: float = 3.0) -> list[str]:
        """Send one AT command and return its reply lines (without the final OK)."""
        return self._t.command(cmd, timeout)

    def query(self, cmd: str) -> str:
        """Send a get command such as AT+GFV and return the value after the colon."""
        for line in self.command(cmd):
            if line.startswith("+") and ":" in line:
                return line.split(":", 1)[1]
        raise BusyTagError(f"{cmd}: no value in reply")

    # ---- device information -------------------------------------------------------------
    @property
    def name(self) -> str:
        return self.query("AT+GDN")

    @property
    def firmware_version(self) -> str:
        return self.query("AT+GFV")

    @property
    def has_wifi(self) -> bool:
        """True for firmware 3.x (Busy Tag 2)."""
        return float(self.firmware_version) >= 3.0

    # ---- LEDs ---------------------------------------------------------------------------
    def set_color(self, color: str, leds: int = ALL_LEDS) -> None:
        """Solid colour on the LEDs in the mask. The other LEDs are switched off."""
        self.stop_pattern()
        if leds != ALL_LEDS:
            self.command(f"AT+SC={ALL_LEDS},000000")
        self.command(f"AT+SC={leds},{_hex(color)}")

    def leds_off(self) -> None:
        self.set_color("000000")

    def builtin_patterns(self) -> dict[int, str]:
        """The patterns stored in the firmware, by ID."""
        out = {}
        for line in self.command("AT+GDPL"):
            if line.startswith("+DPL:"):
                pid, name = line[5:].split(",", 1)
                out[int(pid)] = name
        return out

    def play_builtin_pattern(self, pattern_id: int) -> None:
        self.command(f"AT+DP={pattern_id}")

    def set_pattern(self, steps: list[PatternStep]) -> None:
        """Store a custom pattern. Play it with play_pattern()."""
        if not steps:
            raise ValueError("a pattern needs at least one step")
        self._t.set_pattern([s.line() for s in steps])

    def play_pattern(self, repeat: int = 255) -> None:
        """Play the custom pattern `repeat` times; 255 plays it until stopped."""
        self.command(f"AT+PP=1,{repeat}")

    def stop_pattern(self) -> None:
        self.command("AT+PP=0,0")

    # ---- screen -------------------------------------------------------------------------
    def set_display_brightness(self, percent: int) -> None:
        self.command(f"AT+DB={max(0, min(100, percent))}")

    def files(self) -> dict[str, int]:
        """Files on the device with their size in bytes."""
        out = {}
        for line in self.command("AT+GFL", timeout=5):
            if line.startswith("+FL:"):
                name, _type, size = line[4:].rsplit(",", 2)
                out[name] = int(size)
        return out

    def current_image(self) -> str:
        return self.query("AT+SP?")

    def upload(self, name: str, data: bytes, check_on_screen: bool = True) -> None:
        """Store a file on the device (PNG or GIF for pictures, at most 1 MB for a GIF)."""
        if "/" in name or "\\" in name or " " in name:
            raise ValueError("use a plain file name without spaces or folders")
        # A file that is on screen is held open by the decoder and cannot be overwritten.
        try:
            if check_on_screen and self.current_image() == name:
                others = [f for f in self.files() if f != name and f.lower().endswith((".png", ".gif"))]
                if others:
                    self.show(others[0])
                    time.sleep(0.2)
        except BusyTagError:
            pass
        self._t.upload(name, data)

    def show(self, name: str) -> None:
        """Show a picture that is already on the device."""
        self.command(f"AT+SP={name}")

    def delete(self, name: str) -> None:
        self.command(f"AT+DF={name}")

    def show_image(self, image, name: str = "py_image.png") -> None:
        """Upload a PIL image as PNG and show it.

        The image is scaled to the 240 x 280 screen. Two file names are used in turn
        (py_image_a.png / py_image_b.png), so the picture on screen is never overwritten
        while it is shown and the switch is instant.
        """
        stem, ext = name.rsplit(".", 1) if "." in name else (name, "png")
        target = f"{stem}_b.{ext}" if self._last_image == f"{stem}_a.{ext}" else f"{stem}_a.{ext}"
        if image.size != SCREEN_SIZE:
            image = image.resize(SCREEN_SIZE)
        buf = io.BytesIO()
        image.convert("RGB").save(buf, "PNG", optimize=True)
        self.upload(target, buf.getvalue(), check_on_screen=self._last_image is None)
        self.show(target)
        self._last_image = target

    def show_file(self, path: str, name: str | None = None) -> None:
        """Upload a PNG or GIF from disk and show it."""
        with open(path, "rb") as f:
            data = f.read()
        name = name or path.replace("\\", "/").rsplit("/", 1)[-1].replace(" ", "_")
        self.upload(name, data)
        self.show(name)


# ---- drawing helpers --------------------------------------------------------------------
_FONT_FILES = ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
               "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "arial.ttf", "DejaVuSans.ttf"]


def font(size: int, path: str | None = None):
    """A bold TrueType font at `size` px: `path` if given, else a common system font."""
    from PIL import ImageFont
    for f in ([path] if path else []) + _FONT_FILES:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def text_image(lines, background="000000", color="FFFFFF", size: int = 40, font_path: str | None = None,
               spacing: int = 8, image=None):
    """A 240 x 280 image with the lines centred. Long lines shrink to fit the width.

    `lines` is a string (split at newlines) or a list of strings, or of (text, size, color) tuples.
    `image` draws on a copy of an existing background image instead of a solid colour.
    """
    from PIL import Image, ImageDraw
    img = image.convert("RGB").resize(SCREEN_SIZE) if image is not None else \
        Image.new("RGB", SCREEN_SIZE, "#" + _hex(background))
    draw = ImageDraw.Draw(img)
    if isinstance(lines, str):
        lines = lines.split("\n")
    rows = []
    for item in lines:
        item = [item] if isinstance(item, str) else list(item)
        text = item[0]
        s = item[1] if len(item) > 1 else size
        c = item[2] if len(item) > 2 else color
        f = font(s, font_path)
        while draw.textlength(text, font=f) > SCREEN_SIZE[0] - 16 and s > 10:
            s -= 2
            f = font(s, font_path)
        box = draw.textbbox((0, 0), text or " ", font=f)
        rows.append((text, f, c, box[3] - box[1], box[1]))
    y = (SCREEN_SIZE[1] - sum(r[3] for r in rows) - spacing * (len(rows) - 1)) // 2
    for text, f, c, h, top in rows:
        w = draw.textlength(text, font=f)
        draw.text(((SCREEN_SIZE[0] - w) / 2, y - top), text, font=f, fill="#" + _hex(c))
        y += h + spacing
    return img


# ---- transports -------------------------------------------------------------------------
class _SerialTransport:
    """USB CDC serial. The baud rate is ignored by USB but must be a valid value."""

    def __init__(self, port: str):
        try:
            self.s = serial.Serial(port, 460800, timeout=0.05, write_timeout=5)
        except serial.SerialException as e:
            raise BusyTagError(f"Cannot open {port}: {e}. Close the Busy Tag app and try again.") from e
        self.buf = b""
        self._drain()

    def close(self):
        self.s.close()

    def _drain(self, quiet: float = 0.15, limit: float = 1.5):
        """Throw away leftovers (event lines, late replies) until the line is quiet."""
        end, last = time.time() + limit, time.time()
        while time.time() < end and time.time() - last < quiet:
            if self.s.read(4096):
                last = time.time()
        self.buf = b""

    def _line(self, deadline: float) -> str | None:
        while b"\n" not in self.buf:
            if time.time() > deadline:
                return None
            self.buf += self.s.read(4096)
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode("utf-8", "replace").strip()

    def _read_reply(self, cmd: str, timeout: float) -> list[str]:
        # Set commands and lists end with OK, errors with ERROR:<code>. Single-value queries
        # (AT+GDN, AT+SC?, ...) send only their "+XX:value" line, so a reply is also complete
        # when the line goes quiet after a value line.
        deadline, lines = time.time() + timeout, []
        while True:
            line = self._line(min(deadline, time.time() + 0.3) if lines else deadline)
            if line is None:
                if lines:
                    return lines
                raise BusyTagError(f"{cmd}: no reply")
            if not line or line.startswith(("+evn:", "+log:")) or line == cmd:
                continue
            if line == "OK":
                return lines
            if line.startswith("ERROR"):
                raise BusyTagError(f"{cmd}: {line}")
            lines.append(line)

    def command(self, cmd: str, timeout: float) -> list[str]:
        self.s.write((cmd + "\r\n").encode())
        return self._read_reply(cmd, timeout)

    def _wait_prompt(self, cmd: str, timeout: float = 5.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if b">" in self.buf:
                self.buf = self.buf.split(b">", 1)[1].lstrip(b"\r\n")
                return
            if b"ERROR" in self.buf:
                raise BusyTagError(f"{cmd}: {self.buf.decode(errors='replace').strip()}")
            self.buf += self.s.read(4096)
        raise BusyTagError(f"{cmd}: no '>' prompt")

    def upload(self, name: str, data: bytes) -> None:
        self._drain()
        cmd = f"AT+UF={name},{len(data)}"
        self.s.write((cmd + "\r\n").encode())
        self._wait_prompt(cmd)
        # USB sends data in 64-byte packets. When a transfer ends exactly on a packet boundary
        # the device keeps waiting for more and the upload times out (ERROR:13), so the last
        # byte goes in a separate, short transfer.
        body, tail = (data[:-1], data[-1:]) if len(data) % 64 == 0 else (data, b"")
        for i in range(0, len(body), 32 * 1024):
            self.s.write(body[i:i + 32 * 1024])
        self.s.flush()
        if tail:
            time.sleep(0.02)
            self.s.write(tail)
            self.s.flush()
        self._read_reply(cmd, timeout=10)

    def set_pattern(self, lines: list[str]) -> None:
        cmd = f"AT+CP={len(lines)}"
        self._drain()
        self.s.write((cmd + "\r\n").encode())
        self._wait_prompt(cmd)
        for line in lines:
            self.s.write((line + "\r\n").encode())
        self._read_reply(cmd, timeout=5)


class _HttpTransport:
    """The local HTTP API of firmware 3.x (POST /at, POST /file, POST /pattern)."""

    def __init__(self, host: str, port: int, token: str | None):
        import requests  # only needed for Wi-Fi
        self.http = requests.Session()
        if token:
            self.http.headers["Authorization"] = f"Bearer {token}"
        self.base = f"http://{host}:{port}"

    def close(self):
        self.http.close()

    def _ok(self, r, what: str) -> dict:
        try:
            body = r.json()
        except ValueError:
            body = {}
        if r.status_code != 200 or body.get("status") == "error":
            raise BusyTagError(f"{what}: HTTP {r.status_code} {body.get('message', r.text[:200])}")
        return body

    def command(self, cmd: str, timeout: float) -> list[str]:
        r = self.http.post(f"{self.base}/at", json={"command": cmd}, timeout=timeout + 7)
        lines = [l.strip() for l in self._ok(r, cmd).get("data", "").splitlines() if l.strip()]
        for l in lines:
            if l.startswith("ERROR"):
                raise BusyTagError(f"{cmd}: {l}")
        return [l for l in lines if l != "OK" and not l.startswith(("+evn:", "+log:"))]

    def upload(self, name: str, data: bytes) -> None:
        self._ok(self.http.post(f"{self.base}/file", params={"name": name}, data=data, timeout=60), name)

    def set_pattern(self, lines: list[str]) -> None:
        self._ok(self.http.post(f"{self.base}/pattern", data="\n".join(lines) + "\n", timeout=10), "pattern")
