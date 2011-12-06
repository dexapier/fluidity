# pylint: disable-msg=C0103

from collections import namedtuple


_MAJOR = 0
_MINOR = 3
_MICRO = 0


_vers_ntuple = namedtuple('version_info', 'description major minor micro')
_vers_nums = _MAJOR, _MINOR, _MICRO

__version_info__ = _vers_ntuple(".".join([str(i) for i in _vers_nums]), *_vers_nums)
__version__ = __version_info__.description

# clean up the namespace now that we're done...
del namedtuple, _MAJOR, _MINOR, _MICRO, _vers_ntuple, _vers_nums, i


# Thanks, Fluendo!  No thanks to you, PyGobject changes!
def fuck_you_too_pygobject():
    """GNOME 3: you can use any dynamic language you want, as long 
    as it's Javascript.
    """
    if gobject.pygobject_version > (2, 26, 0):
        # Kiwi is not compatible yet with the changes introduced in
        # http://git.gnome.org/browse/pygobject/commit/?id=84d614
        # Basically, what we do is to revert the changes in _type_register of
        # GObjectMeta at least until kiwi works properly with new pygobject
        from gobject._gobject import type_register  #@UnresolvedImport  #IGNORE:E0611

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

