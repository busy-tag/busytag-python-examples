"""Lesson 1: switch on one LED.

The LED bar has 7 LEDs. Each one is a bit in a 7-bit mask: add the numbers of the LEDs you want
and send the sum with AT+SC=<mask>,<RRGGBB>. 127 (all bits) means all LEDs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag  # noqa: E402

MAP = """
         ____________
        | 4    8   16 |       left top = 4     top = 8     right top = 16
        |             |
        | 2        32 |       left middle = 2              right middle = 32
        |             |
        | 1        64 |       left bottom = 1              right bottom = 64
        |_____________|
              ||
"""


def main():
    with BusyTag.connect() as tag:
        print(f"Connected to {tag.name} (firmware {tag.firmware_version})")
        while True:
            print(MAP)
            answer = input("LED number (several: add them up, 127 = all, Enter = quit): ").strip()
            if not answer:
                break
            try:
                mask = int(answer)
                if not 1 <= mask <= 127:
                    raise ValueError
            except ValueError:
                print("Enter a number from 1 to 127.")
                continue
            tag.set_color("FFFFFF", leds=mask)
            print(f"Sent AT+SC={mask},FFFFFF")
        tag.leds_off()


if __name__ == "__main__":
    main()
