#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2010 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""View/Display objects for use with Kiwi ObjectList/ObjectTrees, etc."""
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'


import abc
import datetime
import os

import gio
import glib
import gtk

from xml.sax import saxutils

from fluidity import defs
from fluidity import utils


ICON_THEME = gtk.icon_theme_get_for_screen(gtk.gdk.Screen())
ALERT_ICON_PIXBUF = ICON_THEME.load_icon('gtk-dialog-warning', 16,
                                         gtk.ICON_LOOKUP_USE_BUILTIN)
FAKE_ICON_PIXBUF = gtk.gdk.pixbuf_new_from_file(
                           os.path.join(defs.APP_DATA_PATH, '16x16_trans.png'))
NOTE_ICON_PIXBUF = ICON_THEME.load_icon('text-x-generic', 16,
                                        gtk.ICON_LOOKUP_USE_BUILTIN)
URL_ICON_PIXBUF = ICON_THEME.load_icon('emblem-web', 16,
                                        gtk.ICON_LOOKUP_USE_BUILTIN)

ENERGY_LABELS_TO_VALUES = {"High": 2, "Normal": 1, "Low": 0}
ENERGY_VALUES_TO_LABELS = utils.invert_dict(ENERGY_LABELS_TO_VALUES)
PRIORITY_LABELS_TO_VALUES = {"High": 1, "Normal": 2, "Low": 3}
PRIORITY_VALUES_TO_LABELS = utils.invert_dict(PRIORITY_LABELS_TO_VALUES)


# HACK: SMART OR SMRT?
def translate_priority(priority):
    """Give a string, get an int; give an int, get a string."""
    if isinstance(priority, basestring):
        mapping = PRIORITY_LABELS_TO_VALUES
    elif isinstance(priority, int):
        mapping = PRIORITY_VALUES_TO_LABELS
    return mapping[priority]


def type_ahead_combo(combo, gdk_keyval):
    keyval = gtk.gdk.keyval_name(gdk_keyval.keyval)
    # we don't want to match on shit like "Alt_R", etc.  this is a cheesy way
    # of doing it, but it has worked so far.
    if len(keyval) == 1:
        selected = combo.get_selected_label()
        combo_strings = combo.get_model_strings()
        selected_index = combo_strings.index(selected) + 1
        selection_range = range(len(combo_strings))[selected_index:]
        for i in selection_range:
            temp_string = combo_strings[i].replace('@', '').lower()
            if (temp_string.startswith(keyval) or
                temp_string.startswith(keyval.lower())):
                combo.select_item_by_label(combo_strings[i])
                return True
        # no joy, it wasn't in the remainder of the list; start from the
        # beginning then
        for s in combo_strings:
            temp_i = s.replace('@', '').lower()
            if temp_i.startswith(keyval) or temp_i.startswith(keyval.lower()):
                combo.select_item_by_label(s)
                return True


class DisplayABC(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, data_src):
        self._data_src = data_src

    def __getattr__(self, attr):
        if hasattr(self._data_src, attr):
            return self._data_src.__getattribute__(attr)

    def __setattr__(self, attr, value):
        # FIXME: I'm sure someone will explain to me at some point why this is
        # Evil or Stupid, but until then, it'll have to do.
        if attr == "_data_src":
            obj = self
        elif hasattr(self._data_src, attr):
            obj = self._data_src
        else:
            obj = self
        object.__setattr__(obj, attr, value)


class DisplayNextAction(DisplayABC):

    def __init__(self, data_src):
        super(DisplayNextAction, self).__init__(data_src)

    # DISPLAY/UI-RELATED BITS
    @property
    def formatted_summary(self):
        # FIXME: this is gheeeeeeeeetttoooooooooooooo.  icky icky icky icky icky.
        # I think this can be done properly with Kiwi's column format setting?
        fs = saxutils.escape(self.summary)
        formats = {1: '<b>{0}</b>', 3: '<span weight="light">{0}</span>',
                   'complete': '<span strikethrough="true">{0}</span>'}
        if self.priority in (1, 3):
            fs = formats[self.priority].format(fs)
        if self.complete:
            fs = formats['complete'].format(fs)
        return fs

    @property
    def energy_est_word(self):
        return ENERGY_VALUES_TO_LABELS[self.energy_est]

    @property
    def notes_icon(self):
        icon = NOTE_ICON_PIXBUF if self.notes else FAKE_ICON_PIXBUF
        return icon

    # FIXME: this should really be sort_due_date or something, shouldn't it?
    @property
    def sort_date(self):
        # FIXME: this is pretty lame...
        # i.e.: we don't have a due date...
        due = self.due_date if self.due_date else datetime.date.fromordinal(1000000)
        return due

    @property
    def url_icon(self):
        icon = URL_ICON_PIXBUF if self.url else FAKE_ICON_PIXBUF
        return icon


class DisplayProject(DisplayABC):

    def __init__(self, data_src):
        super(DisplayProject, self).__init__(data_src)

    # DISPLAY/UI-ONLY -- i.e.: these should be in a different class...
    @property
    def alert(self):
        """Indicate if the project is in an "alert" status."""
        if self._status != "active":
            return FAKE_ICON_PIXBUF
        else:
            for na in self.next_actions:
                if not na.complete:
                    return FAKE_ICON_PIXBUF
            return ALERT_ICON_PIXBUF

    @property
    def formatted_summary(self):
        formats = {1: '<b>{0}</b>', 2: '{0}', 3: '<span weight="light">{0}</span>'}
        fs = saxutils.escape(self.summary)
        return formats[self.priority].format(fs)


class ProjectSupportFileRow(object):

    def __init__(self, full_path):
        self.icon = self._get_icon_pixbuf(full_path)
        self.full_path = full_path
        self.file_name = os.path.split(full_path)[1]
        self.name_lowercase = self.file_name.lower()
        #we want to sort folders first, but after that we don't care
        if os.path.isdir(full_path):
            self.isdir = True
        else:
            self.isdir = False

    def _get_icon_pixbuf(self, file_path):
        it = gtk.icon_theme_get_default()
        #short-circuit on folders, since it fails otherwise...  strange.
        if os.path.isdir(file_path):
            return it.load_icon('folder', 16, gtk.ICON_LOOKUP_USE_BUILTIN)

        content_type = gio.content_type_guess(file_path)
        type_names = gio.content_type_get_icon(content_type).get_names()
        for stock_id in type_names:
            # jesus fscking christ.  this is stoopid... for GTK's sake, I HOPE
            # this is the wrong way to do this
            try:
                pixbuf = it.load_icon(stock_id, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
                return pixbuf
            except glib.GError:
                pass
        # FAIL.  just return something completely generic.
        pixbuf = it.load_icon('text-x-generic', 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        return pixbuf
