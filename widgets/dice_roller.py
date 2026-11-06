"""Dice roller: roll a die in a small window and see the result on Busy Tag.

At start the script uploads the six faces and a rolling animation (a GIF it draws itself) to the
device once. A roll then only switches pictures with AT+SP, which is instant.

    python dice_roller.py
"""
import io
import random
import sys
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag  # noqa: E402

PIPS = {1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)], 4: [(0, 0), (0, 2), (2, 0), (2, 2)],
        5: [(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)], 6: [(0, 0), (0, 1), (0, 2), (2, 0), (2, 1), (2, 2)]}


def face(n: int, angle: float = 0) -> Image.Image:
    die = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    d = ImageDraw.Draw(die)
    d.rounded_rectangle((5, 5, 175, 175), radius=30, fill="white")
    for col, row in PIPS[n]:
        x, y = 40 + col * 50, 40 + row * 50
        d.ellipse((x - 16, y - 16, x + 16, y + 16), fill="#C0102A" if n == 1 else "#111111")
    img = Image.new("RGB", (240, 280), "#1E7A3C")
    die = die.rotate(angle, resample=Image.BICUBIC, expand=True)
    img.paste(die, ((240 - die.width) // 2, (280 - die.height) // 2), die)
    return img


def png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def rolling_gif() -> bytes:
    frames = [face(random.randint(1, 6), random.uniform(-40, 40)) for _ in range(12)]
    buf = io.BytesIO()
    frames[0].save(buf, "GIF", save_all=True, append_images=frames[1:], duration=80, loop=0)
    return buf.getvalue()


class App:
    def __init__(self, tag: BusyTag):
        self.tag = tag
        self.root = tk.Tk()
        self.root.title("Busy Tag dice")
        self.label = tk.Label(self.root, text="Ready", font=("Segoe UI", 32), width=8)
        self.label.pack(padx=30, pady=(25, 10))
        self.button = tk.Button(self.root, text="Roll", font=("Segoe UI", 16), width=10, command=self.roll)
        self.button.pack(pady=(0, 25))
        self.root.bind("<space>", lambda _e: self.roll())

    def roll(self):
        self.button.config(state="disabled")
        self.label.config(text="…")
        self.tag.show("dice_roll.gif")
        self.tag.play_builtin_pattern(24)  # Rainbow
        self.root.after(1500, self.result)

    def result(self):
        n = random.randint(1, 6)
        self.tag.stop_pattern()
        self.tag.show(f"dice_{n}.png")
        self.tag.set_color("FFFFFF" if n < 6 else "FFD000")
        self.label.config(text=str(n))
        self.button.config(state="normal")


def main():
    with BusyTag.connect() as tag:
        print("Uploading the dice pictures…")
        for n in range(1, 7):
            tag.upload(f"dice_{n}.png", png(face(n)))
        tag.upload("dice_roll.gif", rolling_gif())
        tag.show("dice_1.png")
        App(tag).root.mainloop()
        tag.leds_off()


if __name__ == "__main__":
    main()
