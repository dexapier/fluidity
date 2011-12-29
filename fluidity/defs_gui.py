#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2011 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""GUI-specific definitions"""
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'


import os

import gtk

from fluidity import defs


ICON_THEME = gtk.icon_theme_get_for_screen(gtk.gdk.Screen())
ALERT_ICON_PIXBUF = ICON_THEME.load_icon('gtk-dialog-warning', 16,
                                         gtk.ICON_LOOKUP_USE_BUILTIN)
FAKE_ICON_PIXBUF = gtk.gdk.pixbuf_new_from_file(
                           os.path.join(defs.APP_DATA_PATH, '16x16_trans.png'))
NOTE_ICON_PIXBUF = ICON_THEME.load_icon('text-x-generic', 16,
                                        gtk.ICON_LOOKUP_USE_BUILTIN)
URL_ICON_PIXBUF = ICON_THEME.load_icon('emblem-web', 16,
                                        gtk.ICON_LOOKUP_USE_BUILTIN)
