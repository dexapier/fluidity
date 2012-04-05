#-*- coding:utf-8 -*-
#
# Copyright (C) 2012 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
#pylint: disable-msg=W0201
"""Shove handler"""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


import uuid

import pathlib
import shove

from fluidity import defs


SHOVE_PATH = pathlib.Path(defs.USER_DATA_PATH).join('shove_ftw.shove')
TEST_KEY = uuid.UUID('12340000-0000-4000-0000-0000deadbeef')


class Shover(object):
    """Decorator pattern impl. around a Shove datastore, with an API better 
    suited to my needs."""
    
    SHOVE_SQLITE_URI_TEMPLATE = "sqlite:///{0}"
    
    def __init__(self, shove_path=SHOVE_PATH):
        print("Shover initialized with path:", shove_path)
        self._shove_store = None
        self._shove_path = shove_path
    
    def __enter__(self):
        """CONTEXT MANAGERS FTW!"""
        return self.open()
    
    def __exit__(self, exc_type, exc_value, traceback):
        """CONTEXT MANAGERS FTW!"""
        self.close()
        return False
    
    def clear(self):
        """Remove all data from the store."""
        self._shove_store.clear()
    
    def close(self):
        self._shove_store.close()
        self._shove_store = None
    
    def open(self, new_path=None):
        uri = self.SHOVE_SQLITE_URI_TEMPLATE.format(new_path or self._shove_path)
        self._shove_store = shove.Shove(uri)
        return self
    
    # FIXME: refactor to just use the dict "protocol"/interface, by redirecting all calls to things
    # like keys() or items() to the shove store.  For now we have this. 
    def get_item(self, uuid_key):
        """Retrieve an item from the Shove datastore"""
        return self._shove_store[uuid_key.bytes]
    
    def store_item(self, uuid_key, item):
        """Store a single item in the hashtable."""        
        self._shove_store[uuid_key.bytes] = item
