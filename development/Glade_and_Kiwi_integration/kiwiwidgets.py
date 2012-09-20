#!/usr/bin/env python

# thank you, Fluendo!
def fuck_you_too_pygobject():
    """GObject introspection: you can use any dynamic language you want, as long 
    as it's Javascript.
    """
    if gobject.pygobject_version > (2, 26, 0):
        # Kiwi is not compatible yet with the changes introduced in
        # http://git.gnome.org/browse/pygobject/commit/?id=84d614
        # Basically, what we do is to revert the changes in _type_register of
        # GObjectMeta at least until kiwi works properly with new pygobject
        from gobject._gobject import type_register  #@UnresolvedImport
    
        def _type_register(cls, namespace):
            ## don't register the class if already registered
            if '__gtype__' in namespace:
                return
    
            if not ('__gproperties__' in namespace or
                    '__gsignals__' in namespace or
                    '__gtype_name__' in namespace):
                return
    
            # Do not register a new GType for the overrides, as this would sort
            # of defeat the purpose of overrides...
            if cls.__module__.startswith('gi.overrides.'):
                return
    
            type_register(cls, namespace.get('__gtype_name__'))
    
        gobject.GObjectMeta._type_register = _type_register
    
    return True


try:
    import gobject
    fuck_you_too_pygobject()
except ImportError:
    pass



import os
import glob

import gtk

from kiwi.ui.hyperlink import HyperLink
from kiwi.ui.objectlist import ObjectList, ObjectTree
from kiwi.ui.widgets.label import ProxyLabel
from kiwi.ui.widgets.combo import ProxyComboEntry, ProxyComboBox
from kiwi.ui.widgets.checkbutton import ProxyCheckButton
from kiwi.ui.widgets.radiobutton import ProxyRadioButton
from kiwi.ui.widgets.entry import ProxyEntry, ProxyDateEntry
from kiwi.ui.widgets.spinbutton import ProxySpinButton
from kiwi.ui.widgets.textview import ProxyTextView
from kiwi.ui.widgets.button import ProxyButton

# first object added by JENSCK
# pyflakes
HyperLink
ObjectList
ObjectTree
ProxyLabel
ProxyComboEntry
ProxyComboBox
ProxyCheckButton
ProxyRadioButton
ProxyEntry
ProxyDateEntry
ProxySpinButton
ProxyTextView
ProxyButton

def _register_icons():
    icondir = '/usr/share/gazpacho/resources/kiwiwidgets'
    for filename in glob.glob(os.path.join(icondir, '*.png')):
        basename = os.path.basename(filename)
        name = basename[:-4]
        gtk.icon_theme_add_builtin_icon(
            'widget-kiwi-%s' % (name,),
            22,
            gtk.gdk.pixbuf_new_from_file(filename))

_register_icons()

