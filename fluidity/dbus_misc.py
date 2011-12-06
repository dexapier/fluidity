#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2010 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""Misc. D-Bus-related functions & an app-wide note proxy"""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


import dbus
import dbus.mainloop.glib

from fluidity import defs


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
_session_bus = dbus.SessionBus()
# D-Bus setup - making sure we don't lose our damned Tomboy/Gnote connection ;P
notes_proxy = None


# see dbus.SessionBus.watch_name_owner for why this is needed.
def set_notes_proxy(bus_name):
    global notes_proxy
    if bus_name != "":
        notes_proxy = _session_bus.get_object(bus_name, defs.NOTES_OBJECT_PATH)

_session_bus.watch_name_owner(defs.NOTES_BUS_NAME, set_notes_proxy)
set_notes_proxy(defs.NOTES_BUS_NAME)
