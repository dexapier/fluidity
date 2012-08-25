import pygtk
pygtk.require('2.0')
import gtk
import pango
import NextActionsModel
        
def format_func(column, cell, model, my_iter):
    '''
    Function to format gtk.TreeView cells according to priority
    and completion status of Next Actions.
    '''
    cell.set_property("font", "Sans 12")
    '''
    This font makes the UltraHeavy, Normal, and UltraLight text 
    weights clearly distinguishable from one another.
    '''
    if (model.get_value(my_iter, 0) == True):
        '''
        First check completion status of task (column 0 of the model)
        and set "strikethrough" for display of completed tasks.
        '''
        cell.set_property("strikethrough", True)
    else:
        cell.set_property("strikethrough", False)
        
    if (model.get_value(my_iter, 2) == 1):
        '''
        Now check priority of task and set text weight accordingly.
        '''
        cell.set_property("weight", pango.WEIGHT_ULTRAHEAVY)
    elif (model.get_value(my_iter, 2) == 3):
        cell.set_property("weight", pango.WEIGHT_ULTRALIGHT)
    else:
        cell.set_property("weight", pango.WEIGHT_NORMAL)
        
class NextActionView(gtk.Window):
    '''
    Simple class for display of Next Actions
    '''
    
    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
        self.connect("delete-event", self.on_window_delete)
        self.box = gtk.VBox()
        self.add(self.box)
        
        treeview = gtk.TreeView()
        treeview.set_model(NextActionsModel.ProvideDataStore())
        '''
        Although this module requires a gtk.ListStore with a fixed format
        (bool, str, int, str), the code for supplying that ListStore
        is in the NextActionsModel module.
        '''
        done_column = gtk.TreeViewColumn('Complete?', gtk.CellRendererToggle(), active = 0)
        treeview.append_column(done_column)
        summary_cell = gtk.CellRendererText()
        summary_column = gtk.TreeViewColumn("Summary", summary_cell, text = 1)
        treeview.append_column(summary_column)
        summary_column.set_cell_data_func(summary_cell, format_func, data = None)
        priority_cell = gtk.CellRendererText()        
        priority_column = gtk.TreeViewColumn("Priority", priority_cell, text = 2)
        treeview.append_column(priority_column)
        priority_column.set_cell_data_func(priority_cell, format_func, data = None)
        context_cell = gtk.CellRendererText()
        context_cell.set_property("font", "Sans 12")
        context_column = gtk.TreeViewColumn("Context", context_cell, text = 3)
        treeview.append_column(context_column)
        self.box.pack_start(treeview, True, True, 0)
        self.show_all()
        
    def on_window_delete(self, widget, event):
        self.destroy()
        gtk.main_quit()


if __name__ == "__main__":
    win = NextActionView()
    gtk.main()
        
        
        
    