"""Lesson 3: build your own LED pattern.

A custom pattern is a list of steps. Each step has an LED mask, a colour, a fade time (speed) and
a hold time (delay), both in milliseconds. The script stores the steps with AT+CP and plays them
with AT+PP. Add 128 to the LED mask to switch off the LEDs of the previous step.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, PatternStep  # noqa: E402

EXAMPLE = [  # a light that runs from left to right
    PatternStep("0000FF", leds=128 + 1 + 2 + 4, delay=150),
    PatternStep("0000FF", leds=128 + 8, delay=150),
    PatternStep("0000FF", leds=128 + 16 + 32 + 64, delay=150),
]


def ask_step(n: int) -> PatternStep | None:
    print(f"\nStep {n} (press Enter on the colour to finish)")
    color = input("  colour RRGGBB, e.g. FF0000: ").strip()
    if not color:
        return None
    leds = int(input("  LED mask 1-255 [127]: ") or 127)
    speed = int(input("  fade time in ms [5]: ") or 5)
    delay = int(input("  hold time in ms [200]: ") or 200)
    return PatternStep(color, leds, speed, delay)


def main():
    with BusyTag.connect() as tag:
        steps = []
        if input("Use the example pattern (running light)? [Y/n] ").strip().lower() != "n":
            steps = EXAMPLE
        else:
            while (step := ask_step(len(steps) + 1)) is not None:
                steps.append(step)
        if not steps:
            return
        tag.set_pattern(steps)
        print("\nStored on the device:")
        for line in tag.command("AT+CP?"):
            print(" ", line)
        repeat = int(input("How many times to play it (255 = forever) [255]: ") or 255)
        tag.play_pattern(repeat)
        input("Playing. Press Enter to stop.")
        tag.stop_pattern()
        tag.leds_off()


if __name__ == "__main__":
    main()
