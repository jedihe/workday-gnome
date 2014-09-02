#!/usr/bin/env python
from __future__ import division

import pygtk
pygtk.require('2.0')
import gtk
import os
from datetime import timedelta
import time
from time import *
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
  SESSION_NOT_STARTED = 1000
  SESSION_STARTED = 1001
  SESSION_PAUSED = 1002
  SESSION_ENDED = 1003

  def __init__(self):
    # Internal initialization
    self.cur_proc = None

    # Indicator setup
    self.ind = appindicator.Indicator("workday","workday", appindicator.CATEGORY_APPLICATION_STATUS)
    self.ind.set_status (appindicator.STATUS_ACTIVE)
    self.ind.set_icon(self.icon_directory()+"idle.png")

    self.menu = gtk.Menu()

    # Session item
    self.session = gtk.MenuItem('Session:')
    #self.session.connect("activate", self.noop)
    self.session.set_sensitive(False)
    self.menu.append(self.session)

    # Start session item
    self.start = gtk.MenuItem('Start')
    self.start.connect("activate", self.start_session)
    self.menu.append(self.start)

    # Pause item
    self.pause = gtk.MenuItem('Pause')
    self.pause.connect("activate", self.pause_session)
    self.pause.set_sensitive(False)
    self.menu.append(self.pause)

    # Tooltip item
    self.end = gtk.MenuItem('End')
    self.end.connect("activate", self.end_session, None)
    self.end.set_sensitive(False)
    self.menu.append(self.end)

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

    self.session_status = self.SESSION_NOT_STARTED
    self.total_session_time = 0

  def noop(self, *args):
    pass

  def start_session(self, *args):
    if self.session_status == self.SESSION_NOT_STARTED or self.session_status == self.SESSION_PAUSED or self.session_status == self.SESSION_ENDED:
      self.start_recording()
      self.start.set_sensitive(False)
      self.pause.set_sensitive(True)
      self.end.set_sensitive(True)
      if self.session_status != self.SESSION_PAUSED:
        self.total_session_time = 0
        self.session.set_label("Session:")
      pass
      self.session_status = self.SESSION_STARTED
    else:
      # @TODO: Error?
      pass
    pass

  def pause_session(self, *args):
    if self.session_status == self.SESSION_STARTED:
      self.session_status = self.SESSION_PAUSED
      self.stop_recording()

      self.start.set_sensitive(True)
      self.start.set_label("Continue")
      self.pause.set_sensitive(False)
      self.end.set_sensitive(True)
    pass

  def end_session(self, *args):
    if self.session_status == self.SESSION_STARTED or self.session_status == self.SESSION_PAUSED:
      self.session_status = self.SESSION_ENDED
      self.stop_recording()
      source_id = gobject.timeout_add(2000, self.compile_session)

      self.start.set_sensitive(True)
      self.start.set_label("Start")
      self.pause.set_sensitive(False)
      self.end.set_sensitive(False)
    pass

  def start_recording(self):
    if not self.cur_proc:
      cmd_args = "-an -f x11grab -r {} -s {} -i $DISPLAY+0,0 -vcodec libx264 -b 150k -threads 2 -y ~/Videos/workday/$(date +%Y-%m-%d)/workday-$(date +%H-%M-%S).mp4".format(INPUT_FPS, SIZE)
      self.cur_record_start_time = time()
      self.ind.set_icon(self.icon_directory()+"working.png")
      subprocess.call("mkdir -p ~/Videos/workday/$(date +%Y-%m-%d)", shell=True)
      self.cur_proc = subprocess.Popen(["ffmpeg {}".format(cmd_args)], shell=True, stdin=subprocess.PIPE)
      source_id = gobject.timeout_add(TICK_INTERVAL, self.update)
    pass

  def stop_recording(self):
    if self.cur_proc:
      self.cur_proc.communicate('q\n')
      self.cur_proc = None
      self.cur_record_start_time = None
      self.ind.set_icon(self.icon_directory()+"idle.png")
    pass

  def compile_session(self):
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

    if self.session_status == self.SESSION_STARTED:
      self.total_session_time += TICK_INTERVAL / 1000
      formatted_time = self.format_seconds_to_hhmmss(self.total_session_time)
      self.session.set_label('Session: [{}]'.format(formatted_time))

  def format_seconds_to_hhmmss(self, seconds):
      hours = seconds // (60*60)
      seconds %= (60*60)
      minutes = seconds // 60
      seconds %= 60
      return "%02i:%02i:%02i" % (hours, minutes, seconds)

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
