'''
Taken from https://ardoris.wordpress.com/2008/07/05/pygtk-text-entry-dialog/
'''
import gtk

class wdTextEntryDialog(object):
  def __init__(self):
    pass

  def responseToDialog(self, entry, dialog, response):
      dialog.response(response)

  def getText(self):
      #base this on a message dialog
      dialog = gtk.MessageDialog(
          None,
          gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
          gtk.MESSAGE_QUESTION,
          gtk.BUTTONS_OK,
          None)
      dialog.set_title('Name the new session')
      dialog.set_markup('\nPlease enter the <b>session name</b>:')
      #create the text input field
      entry = gtk.Entry()
      #allow the user to press enter to do ok
      entry.connect("activate", self.responseToDialog, dialog, gtk.RESPONSE_OK)
      #create a horizontal box to pack the entry and a label
      hbox = gtk.HBox()
      hbox.pack_end(entry)
      #add it and show it
      dialog.vbox.pack_end(hbox, True, True, 0)
      dialog.show_all()
      # Trick to show the dialog above everything else
      dialog.set_keep_above(True)
      dialog.set_keep_above(False)
      dialog.grab_focus()
      dialog.show()

      #go go go
      dialog.run()
      text = entry.get_text()
      dialog.destroy()
      return text
