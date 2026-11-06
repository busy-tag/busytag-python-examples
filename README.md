# Busy Tag Python examples

Small Python projects that drive a [Busy Tag](https://www.busytag.com) over USB, and over Wi-Fi
on Busy Tag 2. They work with the current firmware:

| Device | Hardware | Firmware | Connection |
|:--|:--|:--|:--|
| Busy Tag | 1.0 | 2.x | USB |
| Busy Tag 2 | 2.0 | 3.x | USB, Wi-Fi (local HTTP API) |

Firmware 2.x and 3.x no longer show up as a USB drive. Pictures are uploaded with the
`AT+UF` command and settings are changed with AT commands instead of editing `config.json`.
[`busytag.py`](busytag.py) does this for you. The commands are described in the
[AT Command Manuals](https://busy-tag.github.io/hardware).

> **Old firmware:** the earlier examples in the separate `busy-tag` repositories were written
> for firmware 1.x, which used the USB drive. Update your device (see
> [Firmware updates](https://busy-tag.github.io/updates/firmware)) and use these instead.

## Getting started

1. Install Python 3.10 or newer.
2. Install the packages:

   ```bash
   python -m venv .venv
   .venv/Scripts/pip install -r requirements.txt    # macOS/Linux: .venv/bin/pip
   ```

3. Plug in Busy Tag and **close the Busy Tag app**: only one program can use the serial port.
4. Run an example, for example `python learning-course/01_led_control.py`.

The device is found automatically by its USB ID (303A:81DF). On Linux, add yourself to the
`dialout` group (or `uucp` on Arch) to use the serial port.

## The helper

```python
from busytag import BusyTag, PatternStep, text_image

with BusyTag.connect() as tag:                  # or BusyTag.connect("COM5")
    print(tag.name, tag.firmware_version)
    tag.set_color("FF0000")                     # all LEDs red
    tag.set_color("00FF00", leds=8)             # only the top LED green
    tag.play_builtin_pattern(24)                # Rainbow (tag.builtin_patterns() lists them)
    tag.set_pattern([PatternStep("FF0000", delay=200), PatternStep("000000", delay=200)])
    tag.play_pattern(repeat=5)
    tag.show_image(text_image("Hello"))         # any PIL image, scaled to 240 x 280
    tag.show_file("animation.gif")              # upload a PNG/GIF file and show it
    tag.command("AT+DB=80")                     # any AT command; returns the reply lines
```

On Busy Tag 2 the same calls work over the network with
`BusyTag.connect_wifi(host, port, token)`; see [`wifi/status_light.py`](wifi/status_light.py).

## Learning course

Step by step, from one LED to live system data.

| Script | What it does |
|:--|:--|
| [01_led_control.py](learning-course/01_led_control.py) | Switch on single LEDs with the LED mask |
| [02_led_color_control.py](learning-course/02_led_color_control.py) | LED colours picked from a picture |
| [03_led_pattern_control.py](learning-course/03_led_pattern_control.py) | Build and play a custom LED pattern |
| [04_text_to_image.py](learning-course/04_text_to_image.py) | Show your text on the screen |
| [05_led_to_ascii.py](learning-course/05_led_to_ascii.py) | Draw the current LED state on the screen |
| [06_system_uptime.py](learning-course/06_system_uptime.py) | How long the computer has been running |
| [07_system_usage.py](learning-course/07_system_usage.py) | CPU, RAM and GPU load, LEDs as a load meter |

## Widgets

| Script | What it shows | Needs |
|:--|:--|:--|
| [air_temperature.py](widgets/air_temperature.py) | Current temperature where you are | – |
| [crypto_tracker.py](widgets/crypto_tracker.py) | Price of a crypto pair, LEDs show the trend | – |
| [moon_phase.py](widgets/moon_phase.py) | The moon phase for a date | – |
| [internet_speed_test.py](widgets/internet_speed_test.py) | Download and upload speed | – |
| [mouse_click_counter.py](widgets/mouse_click_counter.py) | A live count of mouse clicks | – |
| [dice_roller.py](widgets/dice_roller.py) | A die you roll from a small window | – |
| [pomodoro_timer.py](widgets/pomodoro_timer.py) | Work and break countdowns | – |
| [youtube_subscribers.py](widgets/youtube_subscribers.py) | A channel's subscriber count | YouTube Data API key |
| [google_calendar.py](widgets/google_calendar.py) | Current and next Google Calendar event | Google OAuth client |
| [outlook_calendar.py](widgets/outlook_calendar.py) | Current and next Outlook event | Microsoft Entra app registration |
| [spotify_now_playing.py](widgets/spotify_now_playing.py) | Album art and track playing on Spotify | Spotify app client ID |

Each script explains its options at the top and with `--help`. Sign-ins are cached in
`*_token.json` files next to the script; they are listed in `.gitignore`.

## Wi-Fi (Busy Tag 2)

| Script | What it does |
|:--|:--|
| [wifi/status_light.py](wifi/status_light.py) | Sets up the local HTTP server over USB, then switches Busy / Free / Away over Wi-Fi |

## Tips

- **Flash wear:** every picture upload writes to the device's flash memory. The examples only
  upload when something changed, at most about once a minute for clocks and timers. Keep it
  that way in your own projects; for animation, upload one GIF instead of many pictures.
- **Pictures:** the screen is 240 × 280 pixels. GIFs can be at most 1 MB.
- **Licence:** MIT, see [LICENSE](LICENSE). Copy the code into your own projects.
- **Busy Tag app:** many of these ideas are also built into the app as integrations, and you can
  write your own as a [plugin](https://busy-tag.github.io/developers/plugin-development).
