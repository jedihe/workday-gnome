#!/usr/bin/env python
from __future__ import division

import pygtk
pygtk.require('2.0')
import gtk
import os
from datetime import timedelta
from time import time
from math import floor
gtk.gdk.threads_init()
import gobject
import appindicator
import subprocess

#Parameters
INPUT_FPS="0.5"
SIZE="1920x1080"
VIDEO_CHUNK_LENGTH=600 # Seconds
TICK_INTERVAL=5000 # Milliseconds

class Workday:
  def __init__(self):
    # Internal initialization
    self.cur_proc = None

    # Indicator setup
    self.ind = appindicator.Indicator("workday","workday", appindicator.CATEGORY_APPLICATION_STATUS)
    self.ind.set_status (appindicator.STATUS_ACTIVE)
    self.ind.set_icon(self.icon_directory()+"idle.png")

    self.menu = gtk.Menu()
    # Tooltip item
    self.item = gtk.MenuItem('Record')
    self.item.connect("activate", self.start_recording)
    self.item.show()
    self.menu.append(self.item)
    # Tooltip item
    self.item = gtk.MenuItem('Stop')
    self.item.connect("activate", self.stop_recording, None)
    self.item.show()
    self.menu.append(self.item)
    # Tooltip item
    self.item_compile = gtk.MenuItem('Compile')
    self.item_compile.connect("activate", self.compile_full_video, None)
    self.item_compile.show()
    self.menu.append(self.item_compile)
    # A separator
    separator = gtk.SeparatorMenuItem()
    separator.show()
    self.menu.append(separator)
    # A quit item
    item = gtk.MenuItem('Quit')
    item.connect("activate", self.quit, None)
    item.show()
    self.menu.append(item)
    self.menu.show_all()
    self.ind.set_menu(self.menu)
    pass

  def start_recording(self, *args):
    if not self.cur_proc:
      cmd_args = "-an -f x11grab -r {} -s {} -i $DISPLAY+0,0 -vcodec libx264 -b 150k -threads 2 -y ~/Videos/workday/$(date +%Y-%m-%d)/workday-$(date +%H-%M-%S).mp4".format(INPUT_FPS, SIZE)
      self.cur_record_start_time = time()
      self.ind.set_icon(self.icon_directory()+"working.png")
      subprocess.call("mkdir -p ~/Videos/workday/$(date +%Y-%m-%d)", shell=True)
      self.cur_proc = subprocess.Popen(["ffmpeg {}".format(cmd_args)], shell=True, stdin=subprocess.PIPE)
      source_id = gobject.timeout_add(TICK_INTERVAL, self.update)
    pass

  def stop_recording(self, *args):
    if self.cur_proc:
      self.cur_proc.communicate('q\n')
      self.cur_proc = None
      self.cur_record_start_time = None
      self.ind.set_icon(self.icon_directory()+"idle.png")
    pass

  def compile_full_video(self, *args):
    if not self.cur_proc:
      #TODO: Use an instance variable to hold $(date +%Y-%m-%d)
      subprocess.call("cd ~/Videos/workday/$(date +%Y-%m-%d) && MP4Box $(for file in workday-*.mp4; do echo -n \" -cat \"$file; done) full-$(date +%Y-%m-%d).mp4", shell=True)
    else:
      #TODO: Show error message dialog
      pass
    pass

  def icon_directory(self):
    return os.path.dirname(os.path.realpath(__file__)) + os.path.sep

  def update(self):
    print "Tick interval triggered"
    if self.cur_proc:
      age = time() - self.cur_record_start_time
      print "age: ", age
      if age >= VIDEO_CHUNK_LENGTH:
        self.stop_recording()
        self.start_recording()
      else:
        source_id = gobject.timeout_add(TICK_INTERVAL, self.update)

  def main(self):
    gtk.main()

  def quit(self, *args):
    self.stop_recording()
    gtk.main_quit()

# If the program is run directly or passed as an argument to the python
# interpreter then create a Pomodoro instance and show it
if __name__ == "__main__":
    app = Workday()
    app.main()
