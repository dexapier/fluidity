'''
Simple program to test CellRendererIcon Class.
'''
from gi.repository import Gtk #@UnresolvedImport pylint: disable-msg=E0611
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
        
        self.liststore = Gtk.ListStore(str, str, str, str)
        '''
        Second field is a str reference to a stock Gtk icon that a 
        CellRendererPixbuf and its subclasses use to find and render
        that icon.
        '''
        self.liststore.append(["New", Gtk.STOCK_NEW, "Open", Gtk.STOCK_OPEN])
        self.liststore.append(["Save", Gtk.STOCK_SAVE, "Save As", Gtk.STOCK_SAVE_AS])
        self.liststore.append(["Delete", Gtk.STOCK_DELETE, "About", Gtk.STOCK_ABOUT])
        self.liststore.append(["Cut", Gtk.STOCK_CUT, "Paste", Gtk.STOCK_PASTE])
        
        
        self.treeview = Gtk.TreeView(self.liststore)
        
        self.NameCell1 = Gtk.CellRendererText()    
        self.NameColumn1 = Gtk.TreeViewColumn("Name", self.NameCell1, text = 0)
        self.treeview.append_column(self.NameColumn1)
        
        self.IconCell1 = CellRendererIcon()
        self.IconColumn1 = Gtk.TreeViewColumn("Icon", self.IconCell1, stock_id = 1)
        self.IconColumn1.set_alignment(0.5)
        self.treeview.append_column(self.IconColumn1)
        
        self.NameCell2 = Gtk.CellRendererText()
        self.NameColumn2 = Gtk.TreeViewColumn("Name", self.NameCell2, text = 2)
        self.treeview.append_column(self.NameColumn2)
        
        self.IconCell2 = CellRendererIcon()
        self.IconColumn2 = Gtk.TreeViewColumn("Icon", self.IconCell2, stock_id = 3)
        self.IconColumn2.set_alignment(0.5)
        self.treeview.append_column(self.IconColumn2)
        '''
        Note the reference to "stock_id" rather than to an actual Pixbuf.
        '''
        
        
        
        
        self.IconCell1.connect("clicked", self.on_icon_clicked) #pylint: disable-msg=E1101
        self.IconCell2.connect("clicked", self.on_icon_clicked)
        self.vbox.pack_start(self.treeview, True, True, 0)
        self.window.add(self.vbox)
        self.window.show_all()
        
    def on_icon_clicked(self, cell, path):
        path = int(path)
        
        if (path == 0):
            if cell == self.IconCell1:
                print("You clicked on the New icon.")
            elif cell == self.IconCell2:
                print("You clicked on the Open icon.")
            else:
                print("You must have goofed up somewhere!!")
        elif (path == 1):
            if cell == self.IconCell1:
                print("You clicked on the Save icon.")
            elif cell == self.IconCell2:
                print("You clicked on the Save As icon.")
            else:
                print("You must have goofed up somewhere!!")
        elif (path == 2):
            if cell == self.IconCell1:
                print("You clicked on the Delete icon.")
            elif cell == self.IconCell2:
                print("You clicked on the About icon.")
            else:
                print("You must have goofed up somewhere!!")
        elif (path == 3):
            if cell == self.IconCell1:
                print("You clicked on the Cut icon.")
            elif cell == self.IconCell2:
                print("You clicked on the Paste icon.")
            else:
                print("You must have goofed up somewhere!!")
        else:
            print("You must have goofed up somewhere!")
            
def main():
    Gtk.main()
    
if __name__ == "__main__":
    test = CellRendererIcon_Test()
    main() 