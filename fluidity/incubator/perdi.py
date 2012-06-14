#!/usr/bin/python
"""Dead-simple (but mildly braindead), safe, persistent dictionary
classes for use with Python 2.7 and 3.x, on Linux, OS X, and even Android (via SL4A)

NOT performance-optimized.  These are for getting your app off the ground and being
reasonably well assured that your data won't disappear on you.

Requires the excellent 'pathlib', because paths-as-strings is awkward and 
ridiculously error-prone.  ;-P
"""
from __future__ import print_function


__author__ = 'Jens Knutson <jens.knutson@gmail.com>'
__copyright__ = 'Copyright (c) 2012 Jens Knutson'
__license__ = 'LGPLv3+'
__version__ = '0.0.2'


import abc
import collections
import os
import time

# this also relies on either the 'shove' or 'shelve' modules, preferring 'shove'
import pathlib


DEBUG = True
_NAMESPACE = "org.solemnsilence.fluidity"


def ez_perdi(app_namespace, allow_keyless=True):
    data_dir = _get_suitable_user_data_dir(app_namespace)
    if not data_dir.exists():   # pylint: disable-msg=E1103
        _dprint("Creating dir(s):", data_dir)
        os.makedirs(data_dir.as_posix())       
    data_file = data_dir.join('persistent_app_data.perdi')
    _dprint("Data file:", data_file)
    # pick the best persistence system available
    if _we_have_shove():
        _dprint("Returning ShOve-backed perdi")
        if allow_keyless:
            return KeysOptionalPerdiShove(data_file)
        else:
            return PerdiShove(data_file)
    else:
        # for Py3k - no Shove yet. :-(
        _dprint("Returning ShELve-backed perdi")
        if allow_keyless:
            return KeysOptionalPerdiShelve(data_file)
        else:
            return PerdiShelve(data_file)


class _SuperPerdi(collections.Mapping):
    """Generic base class for persistent dictionaries."""

    __metaclass__ = abc.ABCMeta
        
    def __init__(self, persistence_file):
        """Init the obj.
        
        Args:
            persistence_file: pathlib.Path, path to the file used to store the dict
        """
        self._persistence_file = persistence_file
        self._perdict = None
        self._previous_key_uid = 0

    @abc.abstractmethod
    def open(self):
        """Read from the perdi file, become avail. for writing, & return `self`."""

    def clear(self):
        """Remove all data from the store."""
        self._perdict.clear()
    
    def close(self):
        """Write to the persistence file & make the dict unavailable until we are 
        open()ed again."""
        self._perdict.close()
        self._perdict = None

    def __enter__(self):
        """CONTEXT MANAGERS FTW!"""
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        """CONTEXT MANAGERS FTW!"""
        self.close()
        return False

    def __getitem__(self, key):
        return self._perdict[key]

    def __setitem__(self, key, value):
        # in case you care about the key.
        self._perdict[key] = value

    def __iter__(self):
        return iter(self._perdict)

    def __len__(self):
        return len(self._perdict)

    def __del__(self, key):
        del self._perdict[key]


class _KeysOptional(_SuperPerdi):
    
    ITEMS_KEY_TEMPLATE = "perdi_item-{0}-{1}"

    def remove(self, obj):
        for k in tuple(self._perdict.keys()):
            if self._perdict[k] == obj:
                del self._perdict[k]
                break

    def retrieve_all(self):
        """Return all items in the Shove datastore.
        
        Returns: a tuple of all values in the Shove datastore
        """
        return tuple(v for v in self._perdict.values())

    def add_keyless(self, item):
        """Store a single item in the Shove backend without caring about the key."""
        key = self.ITEMS_KEY_TEMPLATE.format(time.time(), self._previous_key_uid)
        self._previous_key_uid += 1
        self._perdict[key] = item


class PerdiShove(_SuperPerdi):
    """Decorator pattern impl. around a Shove or Shelve datastore, with an API 
    better suited to my needs."""
    
    # FIXME: implement such that LevelDB can be easily used, too.
    SHOVE_URI_TEMPLATE = "sqlite:///{0}"
    
    def open(self):
        import shove
        uri = self.SHOVE_URI_TEMPLATE.format(self._persistence_file.as_posix())
        self._perdict = shove.Shove(uri)
        return self


class KeysOptionalPerdiShove(PerdiShove, _KeysOptional):
    # this is here just to add that mixin.
    pass


class PerdiShelve(_SuperPerdi):
    
    def open(self):
        import shelve
        file_name = self._persistence_file.as_posix()
        print(file_name)
        self._perdict = shelve.open(file_name, flag='c', protocol=2)
        return self


class KeysOptionalPerdiShelve(PerdiShove, _KeysOptional):
    pass



def _we_have_shove():
    try:
        import shove
        return True
    except ImportError:
        return False

def _we_are_on_android():
    try:
        # see if the Android module is present at all
        import android  # pylint: disable-msg=F0401
        return True
    except ImportError:
        return False

def _get_suitable_user_data_dir(app_namespace):
    if _we_are_on_android():
        base_dir = pathlib.PosixPath("/sdcard/Android/data")
        return base_dir.join(app_namespace, 'files')
    else:
        # Assume UNIX.  I'm not writing for Windows.
        # this is what xdg.BaseDirectory does, basically, but without needing the
        # whole module (or needing to port it to Py3k...)
        home_dir = pathlib.PosixPath(os.path.expanduser('~'))
        app_name = app_namespace.split('.')[-1]
        return home_dir.join(os.path.join('.local', 'share', app_name))

def _dprint(*to_print):
    if DEBUG:
        print(*to_print)



class _PerdiTester(object):

    YOUR_MOM = "Yeah?  Well your MOM is a persistent dictionary!"
    YOUR_MOM_KEY = "heh, your mom's key.  I have that."
    TEST_NAMESPACE = 'org.solemnsilence.perdi_test'
    TEST_FILE = pathlib.Path(_get_suitable_user_data_dir(TEST_NAMESPACE))
    TEST_OBJECTS = (
        "She is so understanding",
        TEST_FILE.as_posix(),
        12345,
        ['list', 'of', 'strings'],
    )

    def __init__(self):
        self._perdi = None
    
    def start(self):
        self._perdi = ez_perdi(self.TEST_NAMESPACE)

    def read_test(self):
        with self._perdi as perdi_test:
            all_items = perdi_test.retrieve_all()
            try:
                print("Reading YOUR_MOM:", perdi_test[self.YOUR_MOM_KEY])
            except KeyError:
                print("No joy using YOUR_MOM_KEY.  That's a first.")

            for obj in self.TEST_OBJECTS:
                if not obj in all_items:
                    print("FAIL: Item NOT found:", obj)
                else:
                    print("Found:", obj)
            print("all_items:", all_items)
            print("READ test: done!")

    def write_test(self):
        with self._perdi as perdi_test:
            print("Adding obj with YOUR_MOM_KEY:", self.YOUR_MOM)
            perdi_test[self.YOUR_MOM_KEY] = self.YOUR_MOM
            for obj in self.TEST_OBJECTS:
                print("Adding without key:", obj)
                perdi_test.add_keyless(obj)
        print("WRITE test: done!")


def _crappy_little_test(delete_existing=False):
    tester = _PerdiTester()
    tester.start()
    if delete_existing:
        tester._perdi._persistence_file.unlink()
    tester.write_test()
    print("\n\n")
    time.sleep(3)
    tester.read_test()
    print("\n\n")
    tester._perdi.open()
    tester._perdi.remove(tester.YOUR_MOM)
    tester._perdi.close()
    tester.read_test()
    print("\n\n")
    print("open, clear, close")
    tester._perdi.open()
    tester._perdi.clear()
    tester._perdi.close()
    print("\n\n")
    tester.read_test()
