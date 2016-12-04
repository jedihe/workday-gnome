Workday
=======

Record a timelapse of your workday.

Requirements
============

- Ubuntu 12.04/14.04
- FFMpeg with x11grab
- Python 2.7

Usage
=====

- Make sure workday.py has the execute bit enabled.
- Run workday.py, a new indicator will appear in the Unity top bar.
- Click on the indicator and use as needed:
  - Top section relates to current session; it allows setting a name manually
    or just go with a default one (Start button). Pause currently includes a
    prompt to update internal time with actual recorded time (taken from video
    chunks). End stops recording entirely and compiles the full file by
    concatenating the video chunks.
  - Middle section is for session management: create a new one, continue with a
    paused session and shows details for the last one that was ended.
  - Quit: close indicator

Inspired by tomate.py: https://gitorious.org/tomate/tomate/source/a311f5ec3a7953258d7d6fc3f7884bc945529853:

TODO
====

- Replace tomate.py icons with new ones.
- Add sub-menu showing details of the current recording.
- Keep a counter of the total time recorded (with reset option).
