"""Lesson 7: CPU, RAM and GPU load on the screen, with the LEDs as a load meter.

GPU load is read with nvidia-smi when an NVIDIA card is present. The LEDs turn green, yellow or
red with the CPU load.

    python 07_system_usage.py [background.png]
"""
import subprocess
import sys
import time
from pathlib import Path

import psutil
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from busytag import BusyTag, text_image  # noqa: E402


def gpu_load() -> str:
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                                      text=True, timeout=5)
        return f"{int(out.split()[0])} %"
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return "n/a"


def main():
    background = Image.open(sys.argv[1]) if len(sys.argv) > 1 else None
    with BusyTag.connect() as tag:
        tag.stop_pattern()
        last_color = None
        psutil.cpu_percent()
        print("Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(5)
                cpu, ram = psutil.cpu_percent(), psutil.virtual_memory().percent
                lines = [f"CPU  {cpu:.0f} %", f"RAM  {ram:.0f} %", f"GPU  {gpu_load()}"]
                tag.show_image(text_image(lines, "101820", "FFFFFF", size=44, spacing=26, image=background),
                               "usage.png")
                color = "00C000" if cpu < 50 else "FFA000" if cpu < 80 else "FF0000"
                if color != last_color:
                    tag.command(f"AT+SC=127,{color}")
                    last_color = color
                print(f"CPU {cpu:.0f} %  RAM {ram:.0f} %")
        except KeyboardInterrupt:
            tag.leds_off()


if __name__ == "__main__":
    main()
