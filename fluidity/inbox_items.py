#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""All the Inbox item classes."""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


import gio
import glib
import gtk

from fluidity import gio_fml


class InboxStuff(object):
    """Used exclusively to do 'isinstance' calls on subclasses."""
    # FIXME: icky and unpythonic.]
    pass


class InboxFile(gio_fml.FityFile, InboxStuff):

    def __init__(self, file_name):
        super(InboxFile, self).__init__(file_name)
        self.icon = self._init_icon()
        self.summary = self.basename

    def _init_icon(self):
        """Return an icon pixbuf for this Stuff."""
        pixbuf = None
        # first, if it's an image, try to get a thumbnail.
        if self.generic_type == "image":
            thumbnail_path = \
                self._gfile_info.get_attribute_as_string('thumbnail::path')
            if thumbnail_path:
                thumbnail_path = thumbnail_path.replace('/normal/', '/large/')
                if gio.File(thumbnail_path).query_exists():
                    thumbnail = gtk.Image()
                    thumbnail.set_from_file(thumbnail_path)
                    pixbuf = thumbnail.get_pixbuf()
        if not pixbuf:
            # thumbnail FAIL
            icon_theme = gtk.icon_theme_get_for_screen(gtk.gdk.Screen())
            names = self._gfile_info.get_icon().props.names
            for stock_name in names:
                try:
                    pixbuf = icon_theme.load_icon(stock_name, 48,
                                                  gtk.ICON_LOOKUP_USE_BUILTIN)
                    break
                except glib.GError:
                    pass
            if not pixbuf:
                # just do what's guaranteed to work
                pixbuf = icon_theme.load_icon('text-x-generic', 48,
                                              gtk.ICON_LOOKUP_USE_BUILTIN)
        return pixbuf

    def get_preview(self):
        """Return a "preview" of the file's contents.  WARNING: NASTY HACK.

        Return type will vary based on content type.
        """
        if self.generic_type == "image":
#            thumbnail_path = \
#                    self._gfile_info.get_attribute_as_string('thumbnail::path')
#            thumbnail_path = thumbnail_path.replace('/normal/', '/large/')
            thumbnail = gtk.Image()
            thumbnail.set_from_file(self._gfile.get_path())
            return thumbnail.get_pixbuf()
        elif self.generic_type == "audio":
            return None
        elif self.generic_type == "text":
            with open(self._gfile.get_path(), 'r') as content:
                if self._gfile_info.get_size() <= 2048:
                    return content.read()
                else:
                    return content.read(2048)


# pylint: disable-msg=R0903
class InboxNote(InboxStuff):

    def __init__(self, summary, details=None):
        self.summary = summary
        self.details = details


class InboxEmail(InboxStuff):

    def __init__(self, summary, details=None):
        raise NotImplementedError("Not yet implemented")
#        self.summary = summary
#        self.details = details
