#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2010 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""GIO: makes I/O less painful.  Except when it doesn't."""
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'


import os
import shutil

import gio

from xdg import BaseDirectory


class MoveError(Exception):

    def __init__(self, message, path):
        msg = "Could not move the file {0}.  Inner exception: {1}"
        self._message = msg.format(path, message)

    def __str__(self):
        return self._message


class FityFileProxy(object):
    """Proxy base class masquerading as gio.File, because the latter can't be 
    subclassed, apparently."""
    
    def __init__(self, gio_file):
        self._gfile = gio_file.dup()

    def __getattr__(self, attr):
        return getattr(self._gfile, attr)


class FityFile(FityFileProxy):
    """Pythonic wrapper gio.File & gio.FileInfo."""
    
    # FIXME: replace (at least most) of this with pathlib or unipath or some such.
    
    # I would have just subclassed this instead of wrapping, but that's somehow
    # not possible.
    #
    # Seriously, try it.  FREE BEERS here in Minneapolis with me for the first
    # person to email me with how to subclass gio.File without resorting to
    # Total Evil(TM).  Actually, there might still be beer in it if it's a 
    # particularly clever or cute flavor of Evil.

    def __init__(self, file_name=None, gio_file=None):
        """Initialize this obj, using full path `file_name` or gio.File `gio_file`.

        Either file_name or gio_file must be provided, but not both.

        Args:
            file_name: optional if you specify gio_file.  The full path name of the
                file to represent with this object.
            gio_file: optional if you specify file_name.  A gio.File instance for
                the file to represent with this object.
        """
        if file_name and gio_file:
            raise Exception("Only ONE of 'file_name' or 'gio_file' should be set.")
        elif file_name:
            gio_file = gio.File(file_name)
        super(FityFile, self).__init__(gio_file)

        self._gfile_info_real = None    # lazy-load this stuff as a property later
        self._icon = None

    @property
    def basename(self):
        return self._gfile.get_basename()

    @property
    def exists(self):
        return self._gfile.query_exists()

    @property
    def ext(self):
        return os.path.splitext(self.basename)[1]

    @property
    def generic_type(self):
        return self.mime_type.split('/')[0]

    @property
    def is_dir(self):
        filetype = self._gfile.query_file_type(gio.FILE_MONITOR_NONE,
                                               gio.Cancellable())
        return filetype == gio.FILE_TYPE_DIRECTORY

    @property
    def mime_type(self):
        return self._gfile_info.get_content_type()

    @property
    def notes(self):
        notes_ = self._gfile_info.get_attribute_string('metadata::annotation')
        if notes_ is None:
            return ""
        else:
            return notes_

    @property
    def path(self):
        return self._gfile.get_path()

    @property
    def parent(self):
        return FityFile(gio_file=self._gfile.get_parent())

    @property
    def size(self):
        return self._get_human_file_size()

    @property
    def uri(self):
        return self._gfile.get_uri()

    @property
    def _gfile_info(self):
        if not self._gfile_info_real:
            self._gfile_info_real = self._gfile.query_info('*')
        return self._gfile_info_real

    def find_enclosing_mount(self, cancellable=None):
        return self._gfile.find_enclosing_mount(cancellable)

    def get_child(self, fname):
        """Return a FityFile from `self`'s child file/folder, `fname`."""
        if self.is_dir:
            return FityFile(gio_file=self._gfile.get_child(fname))
        else:
            # FIXME: write a real exception for this
            raise ValueError("I am not a directory, I can't have children.")

    def get_children(self):
        # FIXME: this can timeout under some conditions which I can't currently
        #     identify.  Exception info:
        #          gio.Error: DBus error org.freedesktop.DBus.Error.NoReply:
        #                Did not receive a reply. Possible causes include:
        #                    the remote application did not send a reply,
        #                    the message bus security policy blocked the reply,
        #                    the reply timeout expired,
        #                    or the network connection was broken.
        for info in self._gfile.enumerate_children('*'):
            gfile = self._gfile.get_child(info.get_name())
            yield FityFile(gio_file=gfile)

    def copy(self, destination, create_parent_dirs=False):
        """Copy this file/folder to FityFile instance `destination`.

        Args:
            destination: FityFile instance with the desired path
        """
#        orig_path = self.path
        if create_parent_dirs:
            if not destination.parent.exists:
                print("Making dir(s):", destination.parent)
                destination.parent.make_directory_with_parents()
        self._gfile.copy(destination._gfile)

    def make_directory_with_parents(self):
        self._gfile.make_directory_with_parents(gio.Cancellable())

    def move(self, destination):
        """Move this file/folder to FityFile instance `destination`.

        Args:
            destination: FityFile instance with the desired path

        Raises:
            MoveError: if destination.path already exists
        """
        orig_path = self.path
        try:
            if self.is_dir:
                # FIXME: I'm pretty sure the following comment is actually wrong re:
                # *moving* files...
                    # gotta use shutil because fucking gio still doesn't do
                    # do recursion.  pathetic...
                shutil.move(self.path, destination.path)
            else:
                self._gfile.move(destination._gfile)
            self._gfile = destination._gfile
        except gio.Error as g_err:
            raise MoveError(g_err.message, orig_path)

    def mount_enclosing_volume(self, mount_operation=None, callback=None,
                               flags=gio.FILE_COPY_NONE, cancellable=None,
                               user_data=None):
        """Mount the enclosing volume for `self`.

        Stolen from the PyGObject docs:
            "The mount_enclosing_volume() method starts a mount_operation, mounting
             the volume that contains the file location.  When this operation has
             completed, callback will be called with user_data, and the operation
             can be finalized with gio.File.mount_enclosing_volume_finish().

             If cancellable is not None, then the operation can be cancelled by
             triggering the cancellable object from another thread. If the operation
             was cancelled, the error gio.ERROR_CANCELLED will be returned."

        Args:
            mount_operation: a gio.MountOperation - one will be created for you if
                you don't pass one in.
            callback: a function to call when the operation is complete - if None,
                'lambda *args: None' will irresponsibly be used instead.
            flags: optional -- gio file copy flags - defaults to gio.FILE_COPY_NONE
            cancellable: optional -- a gio.Cancellable.  Defaults to NONE
            user_data: optional -- any data to pass to `callback` when the mount
                operation completes.  Defaults to None.
        """
        mount_operation = mount_operation if mount_operation else gio.MountOperation()
        callback = callback if callback else lambda *args: None
        self._gfile.mount_enclosing_volume(mount_operation, callback, flags,
                                           cancellable, user_data)

    def trash(self):
        # FIXME: what if there are dupe files in the trash... what about the
        # file name mangling??
        # stupid uninheritable BS *grumblegrumble*
        trash_path = BaseDirectory.xdg_data_home + "/Trash/files/"
        self._gfile.trash()
        self._gfile = gio.File(trash_path + self._gfile.get_basename())

    def _get_human_file_size(self):
        size_names = ("bytes", "KB", "MB", "GB", "TB")
        raw_size = self._gfile_info.get_size()
        for name in size_names:
            if raw_size > 1024:
                raw_size = raw_size / 1024
            else:
                return "{0} {1}".format(round(raw_size, 1), name)

    def __repr__(self):
        oldrepr = super(FityFile, self).__repr__().rstrip('>')
        things = oldrepr, ": ", str(self._gfile).strip('<>'), '>'
        return "".join(things)
