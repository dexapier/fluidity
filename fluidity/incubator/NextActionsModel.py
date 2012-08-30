import gtk
import pygtk
pygtk.require('2.0')
from NextActionsView import NextActionsView

class NextAction(object):
    
    def __init__(self, complete, summary = "", priority = 2, context = ""):
        self.complete = complete
        self.summary = summary
        self.priority = priority
        self.context = context
        
class NextActionDemo(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
        self.connect("delete-event", self.on_window_delete)
       
        self.connect("delete-event", self.on_window_delete)
        self.set_title("Next Actions List")
        next_actions = []
        next_actions.append(NextAction(False, "Finish Fluidity 2", 1, "@Programming"))
        next_actions.append(NextAction(True, "Complete Contreras Discovery", 2, "@Legal Work"))
        next_actions.append(NextAction(False, "Read Library Book", 3, "@Leisure"))
        next_actions.append(NextAction(True, "Pay Bills", 1, "@Home"))
        liststore = _formatDataStore(next_actions)
        box = NextActionsView(liststore)
        self.add(box)
        self.show_all()
        
    def on_window_delete(self, widget, event):
        self.destroy()
        gtk.main_quit()
        
def _formatDataStore(next_actions):
    
    liststore = gtk.ListStore(bool, str, int, str)
    for na in next_actions:
        liststore.append([na.complete, na.summary, na.priority, na.context])
    return liststore

if __name__ == "__main__":
    win = NextActionDemo()
    gtk.main()