import gtk
import pango
        

class NextActionsView(gtk.VBox):
    """Simple class for display of Next Actions"""
    
    def __init__(self):
        super(NextActionsView, self).__init__()
        self._liststore = gtk.ListStore(bool, str, int, str)
        self._treeview = gtk.TreeView()
        self._treeview.set_model(self._liststore)
        self._actions = []
        
        # Although this module requires a gtk.ListStore with a fixed format
        # (bool, str, int, str), the code for supplying that ListStore
        # is in the NextActionsModel module.
        # we're assuming that a checkbox in a list of tasks, along with the 
        # strikethrough text for completed actions, will be enough to let the 
        # user know what the column is, instead of trying to fit the longer label
        done_column = gtk.TreeViewColumn('', gtk.CellRendererToggle(), active=0)

        summary_cell = gtk.CellRendererText()
        summary_column = gtk.TreeViewColumn("Summary", summary_cell, text=1)
        summary_column.set_cell_data_func(summary_cell, _format_func, data=None)

        priority_cell = gtk.CellRendererText()        
        priority_column = gtk.TreeViewColumn("Priority", priority_cell, text=2)
        priority_column.set_cell_data_func(priority_cell, _format_func, data=None)

        context_cell = gtk.CellRendererText()
        context_cell.set_property("font", "Sans 11")
        context_column = gtk.TreeViewColumn("Context", context_cell, text=3)

        for col in done_column, summary_column, priority_column, context_column:
            self._treeview.append_column(col)
        
        self.pack_start(self._treeview, True, True, 0)

    def set_actions(self, actions):
        self.clear()
        self._actions.extend(actions)
        for action in actions:
            self._liststore.append(_convert_na_to_iterable(action))

    def clear(self):
        self._actions = []  # Gross.  Why don't Python lists have a .clear()?
        self._liststore.clear()


def _convert_na_to_iterable(na):
    item = list()
    item.append(na.complete)
    item.append(na.summary)
    item.append(na.priority)
    item.append(na.context)
    return item


def _format_func(column, cell, model, my_iter):
    """Format gtk.TreeView cell according to priority and completion status 
    of a gee_tee_dee.NextAction.
    """
    # Using this font makes the UltraHeavy, Normal, and UltraLight text 
    # weights clearly distinguishable from one another.
    cell.set_property("font", "Sans 12")
    if (model.get_value(my_iter, 0) == True):
        # First check completion status of task (column 0 of the model)
        # and set "strikethrough" for display of completed tasks.
        cell.set_property("strikethrough", True)
    else:
        cell.set_property("strikethrough", False)
    
    if model.get_value(my_iter, 2) == 1:
        # Now check priority of task and set text weight accordingly.
        cell.set_property("weight", pango.WEIGHT_ULTRAHEAVY)
    elif model.get_value(my_iter, 2) == 3:
        cell.set_property("weight", pango.WEIGHT_ULTRALIGHT)
    else:
        cell.set_property("weight", pango.WEIGHT_NORMAL)