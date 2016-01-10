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
from lib.pygtk_text_entry_dialog import wdTextEntryDialog

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
    self.ended_session = None

    # Indicator setup
    self.ind = appindicator.Indicator("workday","workday", appindicator.CATEGORY_APPLICATION_STATUS)
    self.ind.set_status (appindicator.STATUS_ACTIVE)
    self.ind.set_icon(self.icon_directory()+"idle.png")

    self.ind.set_menu(self.get_menu())

    self.total_session_time = 0

  def get_menu(self):
    self.menu = gtk.Menu()

    session_status = self._session.getStatus()

    # Session name item
    clean_session_statuses = [WorkdaySession.SESSION_NOT_STARTED, WorkdaySession.SESSION_ENDED]
    self.session_name_label_text = '-Set session name-\n ...and start it' if session_status in clean_session_statuses else self.get_session_info_label()
    self.session_name_label = gtk.Label(self.session_name_label_text)
    self.session_name = gtk.MenuItem()
    self.session_name.add(self.session_name_label)
    self.session_name.set_sensitive(True if session_status in clean_session_statuses else False)
    self.session_name.connect("activate", self.set_session_name)
    self.menu.append(self.session_name)

    # Start/Continue session item
    start_label = 'Start' if session_status in clean_session_statuses else 'Continue'
    self.start = gtk.MenuItem(start_label)
    self.start.connect("activate", self.start_session)
    start_session_statuses = [WorkdaySession.SESSION_NOT_STARTED, WorkdaySession.SESSION_PAUSED]
    self.start.set_sensitive(True if session_status in start_session_statuses else False)
    self.menu.append(self.start)

    # Pause item
    self.pause = gtk.MenuItem('Pause')
    self.pause.connect("activate", self.pause_session)
    self.pause.set_sensitive(True if session_status == WorkdaySession.SESSION_STARTED else False)
    self.menu.append(self.pause)

    # Tooltip item
    self.end = gtk.MenuItem('End')
    self.end.connect("activate", self.end_session_confirm, None)
    self.end.set_sensitive(False if session_status in clean_session_statuses else True)
    self.menu.append(self.end)

    # A separator
    self.menu.append(gtk.SeparatorMenuItem())

    self.new = gtk.MenuItem('New session')
    self.new.connect('activate', self.new_session, None)
    new_session_statuses = [WorkdaySession.SESSION_PAUSED]
    self.new.set_sensitive(True if session_status in new_session_statuses else False)
    self.menu.append(self.new)

    # Unclosed sessions
    # Refresh data
    self._wd_config.load()
    saved_sessions = self._wd_config.getSessions()
    restore = gtk.MenuItem('Continue session')
    sessions_menu = gtk.Menu()
    ses_count = 0
    for i in self._wd_config.getSessions():
      if (self._session.getName() != i):
        ses_count += 1
        session_data = self._wd_config.getSession(i)
        misession = gtk.MenuItem()
        label = gtk.Label()
        # Keep these, in case indicators start supporting Pango markup syntax.
        label.set_use_markup(True)
        label.set_markup("<b>{}</b>\n-- Elapsed: <small>{}</small>".format(i, self.format_seconds_to_hhmmss(session_data['duration'])))
        misession.add(label)
        misession.connect('activate', self.resume_session, i)
        sessions_menu.append(misession)
    restore.set_submenu(sessions_menu)
    restore.show_all()
    restore.set_sensitive(True if session_status in start_session_statuses and ses_count > 0 else False)
    restore.set_label('Continue session' if ses_count > 0 else '(No saved sessions)')
    self.restore = restore
    self.menu.append(restore)

    # Previous session info
    if (self.ended_session != None):
      previous_session_label_text = 'Ended session:\n' + self.ended_session.getName() + '\n-- Duration: ' + self.format_seconds_to_hhmmss(self.ended_session.getDuration())
      pass
    else:
      previous_session_label_text = 'Ended session:\n(No ended session)'
      pass
    previous_session_label = gtk.Label(previous_session_label_text)
    ended_session_info = gtk.MenuItem()
    ended_session_info.add(previous_session_label)
    ended_session_info.set_sensitive(False)
    self.ended_session_info = ended_session_info
    self.menu.append(ended_session_info)

    # A separator
    self.menu.append(gtk.SeparatorMenuItem())

    # A quit item
    self.quitMenu = gtk.MenuItem("Quit")
    self.quitMenu.connect("activate", self.quit, None)
    quit_disabled = [WorkdaySession.SESSION_STARTED]
    self.quitMenu.set_sensitive(False if session_status in quit_disabled else True)
    self.menu.append(self.quitMenu)

    self.menu.show_all()

    return self.menu

  def update_menu(self):
    self.ind.set_menu(self.get_menu())

  def resume_session(self, widget, ses_name=None):
    if ses_name != None:
      if (self._session.getStatus() == WorkdaySession.SESSION_NOT_STARTED or self._session.getStatus() == WorkdaySession.SESSION_PAUSED):
        self._session.loadFromConfig(ses_name)
        self.start.activate()

    self.update_menu()

  def set_session_name(self, *args):
    if (self._session.getStatus() == self._session.SESSION_NOT_STARTED):
      new_session_name = wdTextEntryDialog().getText()
      if (len(new_session_name) > 0):
        self._session.setName(new_session_name)
        self.start.activate()
        self.update_menu()

  def noop(self, *args):
    pass

  def new_session(self, *args):
    if (self._session.getDuration() > 0):
      self._session.save()

    self._session = WorkdaySession(self._wd_config, None)
    self.update_menu()

  def start_session(self, *args):
    session_status = self._session.getStatus()
    if session_status == self._session.SESSION_NOT_STARTED or session_status == self._session.SESSION_PAUSED or session_status == self._session.SESSION_ENDED:
      self._session.start()
      self.start_recording()

      self.update_menu()
      pass
    else:
      # @TODO: Error?
      pass
    pass

  def pause_session(self, *args):
    session_status = self._session.getStatus()
    if session_status == self._session.SESSION_STARTED:
      self._session.increaseDuration(time() - self.cur_record_last_time)
      self._session.stop()
      self.stop_recording()

      self.update_menu()
    pass

  def end_session_confirm(self, *args):
    messagedialog = gtk.MessageDialog(parent=None,
                                      flags=gtk.DIALOG_MODAL,
                                      type=gtk.MESSAGE_WARNING,
                                      buttons=gtk.BUTTONS_OK_CANCEL,
                                      message_format="Are you sure you want to end the session?")
    if messagedialog.run() == gtk.RESPONSE_OK:
      self.end_session()

    messagedialog.destroy()

  def end_session(self):
    session_status = self._session.getStatus()
    if session_status == self._session.SESSION_STARTED or session_status == self._session.SESSION_PAUSED:
      self.stop_recording()
      source_id = gobject.timeout_add(2000, self.compile_session)
    pass

  def start_recording(self):
    if not self.cur_proc:
      chunkFilename = 'workday-{}.mp4'.format(strftime('%Y-%m-%d-%H-%M-%S'))
      cmd_args = "-an -f x11grab -r {} -s {} -i $DISPLAY+0,0 -vcodec libx264 -b 150k -threads 2 -y {}/{}".format(INPUT_FPS, SIZE, self._session.getDirPathShellQuoted(), chunkFilename)
      self.cur_record_start_time = time()
      self.cur_record_last_time = self.cur_record_start_time
      self.ind.set_icon(self.icon_directory()+"working.png")
      self.cur_proc = subprocess.Popen(["ffmpeg {}".format(cmd_args)], shell=True, stdin=subprocess.PIPE)
      source_id = gobject.timeout_add(TICK_INTERVAL, self.update)
    pass

  def stop_recording(self):
    if self.cur_proc:
      self.cur_proc.communicate('q\n')
      self.cur_proc = None
      self.cur_record_start_time = None
      self.cur_record_last_time = None
      self.ind.set_icon(self.icon_directory()+"idle.png")
    pass

  def compile_session(self):
    if not self.cur_proc:
      # Properly quote the filename since it may include spaces
      output_filename = "'full-{}.mp4'".format(self._session.getName().replace("'", "'\\''"))
      compile_command = "cd {} && MP4Box $(for file in workday-*.mp4; do echo -n ' -cat '$file; done) {}".format(self._session.getDirPathShellQuoted(), output_filename)
      print compile_command
      subprocess.call(compile_command, shell=True)

      # Keep duration of last session
      self.ended_session = self._session
      self._session.close()
      self._session = WorkdaySession(self._wd_config, None)

      self.update_menu()
    else:
      #TODO: Show error message dialog
      pass
    pass

  def get_session_info_label(self):
    return "Session: {}\n-- Elapsed: [{}]".format(self._session.getName(), self.format_seconds_to_hhmmss(self._session.getDuration()))

  def update_session_info_menu_item(self):
    session_status = self._session.getStatus()

    # Session name item
    clean_session_statuses = [WorkdaySession.SESSION_NOT_STARTED, WorkdaySession.SESSION_ENDED]
    self.session_name_label_text = '-Set session name-\n ...and start it' if session_status in clean_session_statuses else self.get_session_info_label()
    self.session_name_label.set_markup(self.session_name_label_text)

  def icon_directory(self):
    return os.path.dirname(os.path.realpath(__file__)) + os.path.sep

  def update(self):
    print "Tick interval triggered"
    if self.cur_proc:
      self.cur_record_last_time = time()
      age = self.cur_record_last_time - self.cur_record_start_time
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

    self.update_session_info_menu_item()

  def format_seconds_to_hhmmss(self, seconds):
      hours = seconds // (60*60)
      seconds %= (60*60)
      minutes = seconds // 60
      seconds %= 60
      return "%02i:%02i:%02i" % (hours, minutes, seconds)

  def main(self):
    gtk.main()

  def quit(self, *args):
    # Just stop the recording, do not close the session
    self.stop_recording()
    gtk.main_quit()

# If the program is run directly or passed as an argument to the python
# interpreter then create a Workday instance and show it
if __name__ == "__main__":
    app = Workday()
    app.main()
