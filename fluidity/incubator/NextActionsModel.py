"""Simple demo program to provide store of Next Actions and top-level window
to allow demonstration of NextActionsView display widget.
"""
import gobject
import gtk

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
        self.set_title("Next Actions List")

        self.box = NextActionsView()
        self.add(self.box)
        self.show_all()
        gobject.timeout_add_seconds(1, self.show_actions)
        gobject.timeout_add_seconds(3, self.box.clear)
        gobject.timeout_add_seconds(4, self.show_actions)

    def show_actions(self):
        next_actions = []
        next_actions.append(NextAction(False, "Finish Fluidity 2", 1, "@Programming"))
        next_actions.append(NextAction(True, "Complete Contreras Discovery", 2, "@Legal Work"))
        next_actions.append(NextAction(False, "Read Library Book", 3, "@Leisure"))
        next_actions.append(NextAction(True, "Pay Bills", 1, "@Home"))
        self.box.set_actions(next_actions)
        
    def on_window_delete(self, widget, event):
        self.destroy()
        gtk.main_quit()


if __name__ == "__main__":
    win = NextActionDemo()
    gtk.main()