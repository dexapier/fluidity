'''
Simple class to transform a Gtk Pixbuf into a clickable icon
'''
from gi.repository import Gtk       #@UnresolvedImport pylint: disable-msg=E0611
from gi.repository import GObject   #@UnresolvedImport pylint: disable-msg=E0611

class CellRendererIcon(Gtk.CellRendererPixbuf):
    __gsignals__    = { 'clicked' : (GObject.SIGNAL_RUN_LAST,
                                     GObject.TYPE_NONE,
                                    (GObject.TYPE_STRING,)), }
    '''
    Add 'clicked' signal to turn the Pixbuf into an icon
    '''
    def __init__(self):
        Gtk.CellRendererPixbuf.__init__(self)
        self.set_property('mode', Gtk.CellRendererMode.ACTIVATABLE) #pylint: disable-msg=E1101
        '''
        Set mode of CellRenderer to Activatable - inherited from
        Gtk.CellRenderer. The default is INERT. This is necessary
        for the CellRendererIcon to respond to mouse clicks.
        '''
        self.set_property('follow-state', True) #pylint: disable-msg=E1101
        '''
        Colorize icons according to CellRendererState - inherited from
        Gtk.CellRendererPixBuf
        '''
 
    def do_activate(self, even, widget, path, background_area, cell_area, flags):
        '''
        Override do_activate from Gtk.CellRendererPixbuf to emit the "clicked" signal
        '''
        self.emit('clicked', path)  #pylint: disable-msg=E1101