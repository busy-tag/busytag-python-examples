"""Lesson 4: show your text on the screen.

The text is drawn on a 240 x 280 picture with Pillow, uploaded with AT+UF and shown with AT+SP.

    python 04_text_to_image.py [font.ttf]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, text_image  # noqa: E402


def main():
    font_path = sys.argv[1] if len(sys.argv) > 1 else None
    with BusyTag.connect() as tag:
        while True:
            text = input("Text (use \\n for a new line, Enter = quit): ").strip()
            if not text:
                break
            color = input("Text colour RRGGBB [FFFFFF]: ").strip() or "FFFFFF"
            background = input("Background colour RRGGBB [000000]: ").strip() or "000000"
            size = max(10, min(150, int(input("Font size 10-150 [48]: ") or 48)))
            img = text_image(text.replace("\\n", "\n"), background, color, size, font_path)
            tag.show_image(img, "lesson4.png")
            print("Shown on Busy Tag.")


if __name__ == "__main__":
    main()
