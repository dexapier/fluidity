from gi.repository import Gtk
from CellRendererIcon import CellRendererIcon

class CellRendererIcon_Test:
    
    
    def delete_event(self, widget, event, data = None):
        Gtk.main_quit()
        return False

    
    def __init__(self):
        self.window = Gtk.Window()
        self.window.set_title("CellRendererIcon Test")
        self.window.set_default_size(275, 170)
        self.window.connect("delete_event", self.delete_event)
        self.vbox = Gtk.Box(orientation = Gtk.Orientation.VERTICAL)
        
        self.liststore = Gtk.ListStore(str, str)
        '''
        Second field is a str reference to a stock Gtk icon that a 
        CellRendererPixbuf and its subclasses use to find and render
        that icon.
        '''
        self.liststore.append(["New", Gtk.STOCK_NEW])
        self.liststore.append(["Open", Gtk.STOCK_OPEN])
        self.liststore.append(["Save", Gtk.STOCK_SAVE])
        self.liststore.append(["Delete", Gtk.STOCK_DELETE])
        
        
        self.treeview = Gtk.TreeView(self.liststore)
        
        self.NameCell = Gtk.CellRendererText()    
        self.NameColumn = Gtk.TreeViewColumn("Name", self.NameCell, text = 0)
        self.treeview.append_column(self.NameColumn)
        
        self.IconCell = CellRendererIcon()
        self.IconColumn = Gtk.TreeViewColumn("Icon", self.IconCell, stock_id = 1)
        '''
        Note the reference to "stock_id" rather than to Pixbuf itself
        '''
        self.IconColumn.set_alignment(0.5)
        self.treeview.append_column(self.IconColumn)
        
        self.IconCell.connect("clicked", self.on_icon_clicked)
        self.vbox.pack_start(self.treeview, True, True, 0)
        self.window.add(self.vbox)
        self.window.show_all()
        
    def on_icon_clicked(self, cell, path):
        path = int(path)
        
        if (path == 0):
            print("You clicked on the New icon.")
        elif (path == 1):
            print("You clicked on the Open icon.")
        elif (path == 2):
            print("You clicked on the Save icon.")
        elif (path == 3):
            print("You clicked on the Delete icon.")
        else:
            print("You must have goofed up somewhere!")
            
def main():
    Gtk.main()
    
if __name__ == "__main__":
    test = CellRendererIcon_Test()
    main() 