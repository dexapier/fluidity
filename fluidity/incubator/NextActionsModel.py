import gtk
import pygtk
pygtk.require('2.0')

class NextAction(object):
    
    def __init__(self):
        self.summary = ""
        self.complete = False
        self.priority = 2
        self.context = ""
        
def ProvideDataStore():
    '''
    Simple in-line ListStore with dummy data done to demonstrate
    functionality of NextActionsView module
    '''
    
    liststore = gtk.ListStore(bool, str, int, str)
    liststore.append([False, "Finish Fluidity 2", 1, "@Programming"])
    liststore.append([True, "Complete Contreras Discovery", 2, "@Legal Work"])
    liststore.append([False, "Read Library Book", 3, "@Leisure"])
    liststore.append([True, "Pay Bills", 1, "@Home"])
    
    return liststore