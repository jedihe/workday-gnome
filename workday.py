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

from lib.workday_config import WorkdayConfig
from lib.workday_session import WorkdaySession
from lib.takeinput import TakeInput

#Parameters
INPUT_FPS="0.5"
SIZE="1920x1080"
VIDEO_CHUNK_LENGTH=600 # Seconds
TICK_INTERVAL=5000 # Milliseconds

class Workday:
  def __init__(self):
    # Internal initialization
    self.cur_proc = None
    self._wd_config = WorkdayConfig()
    self._session = WorkdaySession(self._wd_config, None)

    # Indicator setup
    self.ind = appindicator.Indicator("workday","workday", appindicator.CATEGORY_APPLICATION_STATUS)
    self.ind.set_status (appindicator.STATUS_ACTIVE)
    self.ind.set_icon(self.icon_directory()+"idle.png")

    self.menu = gtk.Menu()

    # Session name item
    self.session_name = gtk.MenuItem("-Set session name-")
    self.session_name.set_sensitive(True)
    self.session_name.connect("activate", self.set_session_name)
    self.menu.append(self.session_name)

    # Session item
    self.session = gtk.MenuItem('-No Elapsed Time-')
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
    self.quitMenu = gtk.MenuItem("Quit")
    self.quitMenu.connect("activate", self.quit, None)
    self.quitMenu.show()
    self.menu.append(self.quitMenu)
    self.menu.show_all()
    self.ind.set_menu(self.menu)

    self.total_session_time = 0

  def set_session_name(self, *args):
    if (self._session.getStatus() == self._session.SESSION_NOT_STARTED):
      inputBox = TakeInput("Enter the session name")
      inputBox.waitForInput()
      new_session_name = inputBox.getString()
      self._session.setName(new_session_name)
      self.session_name.set_label('Session: {}'.format(self._session.getName()))

  def noop(self, *args):
    pass

  def start_session(self, *args):
    session_status = self._session.getStatus()
    if session_status == self._session.SESSION_NOT_STARTED or session_status == self._session.SESSION_PAUSED or session_status == self._session.SESSION_ENDED:
      self._session.start()
      self.session_name.set_sensitive(False)
      self.start_recording()
      self.start.set_sensitive(False)
      self.pause.set_sensitive(True)
      self.end.set_sensitive(True)
      if session_status != self._session.SESSION_PAUSED:
        self.session_name.set_label("Session: {}".format(self._session.getName()))
        self.session.set_label("Elapsed:")

      self.quitMenu.set_sensitive(False)
      pass
    else:
      # @TODO: Error?
      pass
    pass

  def pause_session(self, *args):
    session_status = self._session.getStatus()
    if session_status == self._session.SESSION_STARTED:
      self._session.stop()
      self.stop_recording()

      self.start.set_sensitive(True)
      self.start.set_label("Continue")
      self.pause.set_sensitive(False)
      self.end.set_sensitive(True)
      self.quitMenu.set_sensitive(False)
    pass

  def end_session(self, *args):
    session_status = self._session.getStatus()
    if session_status == self._session.SESSION_STARTED or session_status == self._session.SESSION_PAUSED:
      self.stop_recording()
      source_id = gobject.timeout_add(2000, self.compile_session)

      self.session_name.set_sensitive(True)
      self.session_name.set_label('-Set session name-')
      self.start.set_sensitive(True)
      self.start.set_label("Start")
      self.pause.set_sensitive(False)
      self.end.set_sensitive(False)
    pass

  def start_recording(self):
    if not self.cur_proc:
      chunkFilename = 'workday-{}.mp4'.format(strftime('%Y-%m-%d-%H-%M-%S'))
      cmd_args = "-an -f x11grab -r {} -s {} -i $DISPLAY+0,0 -vcodec libx264 -b 150k -threads 2 -y {}/{}".format(INPUT_FPS, SIZE, self._session.getDirPath(), chunkFilename)
      self.cur_record_start_time = time()
      self.ind.set_icon(self.icon_directory()+"working.png")
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
      subprocess.call("cd {} && MP4Box $(for file in workday-*.mp4; do echo -n \" -cat \"$file; done) full-{}.mp4".format(self._session.getDirPath(), self._session.getName()), shell=True)

      # Keep duration of last session
      formatted_time = self.format_seconds_to_hhmmss(self._session.getDuration())
      self.session.set_label('Total time: [{}] - Session: {}'.format(formatted_time, self._session.getName()))

      self._session.close()
      self._session = WorkdaySession(self._wd_config, None)

      self.quitMenu.set_sensitive(True)
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

    session_status = self._session.getStatus()
    if session_status == self._session.SESSION_STARTED:
      self._session.increaseDuration(TICK_INTERVAL / 1000)
      self._session.save()
      formatted_time = self.format_seconds_to_hhmmss(self._session.getDuration())
      self.session.set_label('Elapsed: [{}]'.format(formatted_time))

  def format_seconds_to_hhmmss(self, seconds):
      hours = seconds // (60*60)
      seconds %= (60*60)
      minutes = seconds // 60
      seconds %= 60
      return "%02i:%02i:%02i" % (hours, minutes, seconds)

  def main(self):
    gtk.main()

  def quit(self, *args):
    self._session.close()
    self.stop_recording()
    gtk.main_quit()

# If the program is run directly or passed as an argument to the python
# interpreter then create a Workday instance and show it
if __name__ == "__main__":
    app = Workday()
    app.main()
