Workday
=======

Record a timelapse of your workday.

Requirements
============

- Ubuntu 12.04
- FFMpeg with x11grab
- Python 2.7
- MP4Box

Usage
=====

- Make sure workday.py has the execute bit enabled.
- Run workday.py, a new indicator will appear in the Unity top bar.
- Click on the indicator and use as needed:
  - Record: start recording; videos are saved to ~/Videos/workday/[current-date]
  - Stop: stop current recording (if there's one ongoing)
  - Compile: Concatenate all chunks in current-date's directory into a single file (full-....mp4). Only works if recording is stopped.
  - Quit: close indicator

Inspired by tomate.py: https://gitorious.org/tomate/tomate/source/a311f5ec3a7953258d7d6fc3f7884bc945529853:

TODO
====

- Replace tomate.py icons with new ones.
- Add sub-menu showing details of the current recording.
- Keep a counter of the total time recorded (with reset option).
