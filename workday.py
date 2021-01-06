#!/usr/bin/env python
from __future__ import division

from gi import pygtkcompat
pygtkcompat.enable()
pygtkcompat.enable_gtk(version='3.0')

#import pygtk
#pygtk.require('3.0')
#import gtk
from gi.repository import Gtk as gtk
import gi
gi.require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3 as appindicator
import os
from datetime import timedelta
import time
from time import *
from math import floor
gtk.gdk.threads_init()
import gobject
#import appindicator
import signal
import subprocess

from lib.workday_config import WorkdayConfig
from lib.workday_session import WorkdaySession
from lib.pygtk_text_entry_dialog import wdTextEntryDialog

#Parameters
INPUT_FPS="0.5"
SIZE="1920x1080"
SIZE="1366x768"
SIZE="w=1366:h=768"
VIDEO_CHUNK_LENGTH=300 # Seconds
TICK_INTERVAL=2000 # Milliseconds

'''
Helper routine, allows inspecting a gtk widget tree
'''
def get_descendant(widget, child_name, level, doPrint=False):
  if widget is not None:
    if doPrint: print("-"*level + " :: " + widget.get_name())
  else:
    if doPrint:  print("-"*level + "None")
    return None
  #/*** If it is what we are looking for ***/
  if(gtk.Buildable.get_name(widget) == child_name): # not widget.get_name() !
    return widget;
  #/*** If this widget has one child only search its child ***/
  if (hasattr(widget, 'get_child') and callable(getattr(widget, 'get_child')) and child_name != ""):
    child = widget.get_child()
    if child is not None:
      return get_descendant(child, child_name,level+1,doPrint)
  # /*** Ity might have many children, so search them ***/
  elif (hasattr(widget, 'get_children') and callable(getattr(widget, 'get_children')) and child_name !=""):
    children = widget.get_children()
    # /*** For each child ***/
    found = None
    for child in children:
      if child is not None:
        found = get_descendant(child, child_name,level+1,doPrint) # //search the child
        if found: return found

class Workday:
  def __init__(self):
    # Internal initialization
    self.cur_proc = None
    self._wd_config = WorkdayConfig()
    self._session = WorkdaySession(self._wd_config, None)
    self.ended_session = None
    self._chunks_duration = {}

    # Indicator setup
    self.ind = appindicator.Indicator.new("workday","workday", appindicator.IndicatorCategory.APPLICATION_STATUS)
    self.ind.set_status (appindicator.IndicatorStatus.ACTIVE)
    self.ind.set_icon(self.icon_directory()+"idle.png")
    self.ind.set_label("Workday", "")

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
    start_label_text = 'Start' if session_status in clean_session_statuses else 'Continue'
    start_session_statuses = [WorkdaySession.SESSION_NOT_STARTED, WorkdaySession.SESSION_PAUSED]
    self.start = self._get_menu_item(gtk.STOCK_MEDIA_RECORD, start_label_text, start_session_statuses)
    self.start.connect("activate", self.start_session)
    self.menu.append(self.start)

    # Pause item
    self.pause = self._get_menu_item(gtk.STOCK_MEDIA_PAUSE, 'Pause', [WorkdaySession.SESSION_STARTED])
    self.pause.connect("activate", self.pause_session)
    self.menu.append(self.pause)

    # End item
    end_enabled_statuses = [WorkdaySession.SESSION_STARTED, WorkdaySession.SESSION_PAUSED]
    self.end = self._get_menu_item(gtk.STOCK_MEDIA_STOP, 'End', end_enabled_statuses)
    self.end.connect("activate", self.end_session_confirm, None)
    self.menu.append(self.end)

    # A separator
    self.menu.append(gtk.SeparatorMenuItem())

    # New session item
    new_session_statuses = [WorkdaySession.SESSION_PAUSED]
    self.new = self._get_menu_item(gtk.STOCK_NEW, 'New session', new_session_statuses)
    self.new.connect('activate', self.new_session, None)
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
    ended_session_info = gtk.ImageMenuItem()
    ended_session_info.add(previous_session_label)
    ended_session_info.set_image(self._get_menu_icon(ended_session_info, gtk.STOCK_INFO, False))
    ended_session_info.set_always_show_image(True)
    ended_session_info.set_sensitive(False)
    self.ended_session_info = ended_session_info
    self.menu.append(self.ended_session_info)

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

  def _get_menu_item(self, stock_icon, label_text, enabled_statuses):
    session_status = self._session.getStatus()

    mi_sensitive = True if session_status in enabled_statuses else False
    mi = gtk.ImageMenuItem(label_text)
    mi.set_always_show_image(True)

    mi.set_image(self._get_menu_icon(mi, stock_icon, mi_sensitive))
    mi.set_sensitive(mi_sensitive)

    return mi

  def _get_menu_icon(self, widget, stock_icon, sensitive = True):
    # Create the requested icon
    icon = widget.render_icon(stock_icon, gtk.ICON_SIZE_MENU)

    # Create the icon to use as empty canvas, use .copy() to ensure no shared pixbuf between calls
    empty_icon = widget.render_icon(gtk.STOCK_NEW, gtk.ICON_SIZE_MENU).copy()
    # Clean the canvas entirely (full transparency)
    empty_icon.fill(0x00000000)
    # Composite the requested icon on top of the canvas, apply transparency according to sensitive state
    icon.composite(empty_icon, 0, 0, icon.get_width(), icon.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_NEAREST, 255 if sensitive else 127)

    # Return a new image created from the pixbuf
    return gtk.image_new_from_pixbuf(empty_icon)

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

      try:
        # Update duration
        sess_dir = self._session.getDirPath()
        chunks_list = [f for f in os.listdir(sess_dir) if os.path.isfile(os.path.join(sess_dir, f)) and f.startswith('workday-')]
        print chunks_list
        durations = []

        for f in chunks_list:
          print "--- Processing chunk {} from chunks_list".format(f)
          if self._chunks_duration.has_key(f):
            durations.append(self._chunks_duration[f])
          else:
            try:
              #chunk_stat = subprocess.check_output(["ffprobe -i {} -show_streams -hide_banner | grep duration=".format(os.path.join(sess_dir, f))], shell=True)
              chunk_stat = subprocess.check_output(["ffprobe -i {} -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1".format(os.path.join(sess_dir, f))], shell=True)
              try:
                chunk_duration = int(float(chunk_stat))
                self._chunks_duration[f] = chunk_duration
                durations.append(chunk_duration)
              except ValueError:
                pass

            except:
              pass

        print "- All durations: {}".format(durations)
        duration = reduce(lambda a,b: a+b, durations)
#       messagedialog = gtk.MessageDialog(parent=None,
#                                         flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
#                                         type=gtk.MESSAGE_WARNING,
#                                         buttons=gtk.BUTTONS_OK_CANCEL,
#                                         message_format="\nUpdate session duration from {} to {}?".format(self.format_seconds_to_hhmmss(self._session.getDuration()), self.format_seconds_to_hhmmss(duration)))
#       # Trick to show the dialog above everything else
#       messagedialog.set_title('Confirmation')
#       messagedialog.show_all()
#       messagedialog.set_keep_above(True)
#       messagedialog.set_keep_above(False)
#       messagedialog.grab_focus()
#       messagedialog.show()

#       if messagedialog.run() == gtk.RESPONSE_OK:
        self._session.setDuration(duration)

        messagedialog.destroy()
      except:
        pass

      self.update_menu()
      # Update indicator label with total time.
      self.ind.set_label("[{}]".format(self.format_seconds_to_hhmmss(self._session.getDuration())), "")
    pass

  def end_session_confirm(self, *args):
    messagedialog = gtk.MessageDialog(parent=None,
                                      flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                      type=gtk.MESSAGE_WARNING,
                                      buttons=gtk.BUTTONS_OK_CANCEL,
                                      message_format="\nAre you sure you want to end the session?")
    # Trick to show the dialog above everything else
    messagedialog.set_title('Confirmation')
    messagedialog.show_all()
    messagedialog.set_keep_above(True)
    messagedialog.set_keep_above(False)
    messagedialog.grab_focus()
    messagedialog.show()

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
      cmd_args = "-an -f x11grab -r {} -s {} -i $DISPLAY+0,0 -vcodec libx264 -b 150k -x264opts keyint=15:min-keyint=15:scenecut=-1 -threads 2 -y {}/{}".format(INPUT_FPS, SIZE, self._session.getDirPathShellQuoted(), chunkFilename)
      cmd_parts = [
        "/usr/bin/ffmpeg",
        "-crtc_id", "42",
        "-framerate", "10",
        "-f", "kmsgrab",
        "-i", "-",
        "-vaapi_device", "/dev/dri/renderD128",
        "-filter:v", "hwmap,scale_vaapi={}:format=nv12,hwdownload,fps={}".format(SIZE, INPUT_FPS),
        "-c:v", "libx264",
        "-b:v", "150k",
        "-r:v", "{}".format(INPUT_FPS),
        "-y", "{}/{}".format(self._session.getDirPath(), chunkFilename)
      ]
      self.cur_record_start_time = time()
      self.cur_record_last_time = self.cur_record_start_time
      self.ind.set_icon(self.icon_directory()+"working.png")
      #self.cur_proc = subprocess.Popen(["ffmpeg {}".format(cmd_args)], shell=True, stdin=subprocess.PIPE)
      self.cur_proc = subprocess.Popen(cmd_parts, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env={"LIBVA_DRIVER_NAME": "i965", "PATH": "/usr/bin"})
      source_id = gobject.timeout_add(TICK_INTERVAL, self.update)
    pass

  def stop_recording(self):
    if self.cur_proc:
      #self.cur_proc.communicate('q\n')
      self.cur_proc.send_signal(signal.SIGINT)
      self.cur_proc = None
      self.cur_record_start_time = None
      self.cur_record_last_time = None
      self.ind.set_icon(self.icon_directory()+"idle.png")
    pass

  def compile_session(self):
    if not self.cur_proc:
      # Properly quote the filename since it may include spaces
      output_filename = "'full-{}.mp4'".format(self._session.getName().replace("'", "'\\''"))
      compile_command = "cd {} && for file in workday*; do echo \"file $file\" >> workday-file-list.txt; done && ffmpeg -f concat -i workday-file-list.txt -codec copy {} && rm workday-file-list.txt".format(self._session.getDirPathShellQuoted(), output_filename)
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
    # Update indicator label with total time.
    self.ind.set_label("[{}]".format(self.format_seconds_to_hhmmss(self._session.getDuration())), "")

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
