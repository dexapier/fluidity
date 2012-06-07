#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2010 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""GeeTeeDee-related data objects"""
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'


import datetime
import uuid

from xml.sax import saxutils

from fluidity import app_utils
from fluidity import defs
from fluidity import defs_gui
from fluidity import models
from fluidity import utils


# FIXME: try to remove this, we don't use it anywhere, it may just be stored in
# the pickle data
TOP_LEVEL_PROJECT_LEGACY = '00000000-0000-0000-0000-000000000000'
TOP_LEVEL_PROJECT_UUID = uuid.UUID(
        bytes='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xCA\xFE\xD0\x0D')

# the Actions and Prjs use the same priority values (at least for now)
ENERGY_LABELS_TO_VALUES = {"High": defs.EnergyEstimate.HIGH,
                           "Normal": defs.EnergyEstimate.MEDIUM,
                           "Low": defs.EnergyEstimate.LOW}
ENERGY_VALUES_TO_LABELS = utils.invert_dict(ENERGY_LABELS_TO_VALUES)
PRIORITY_LABELS_TO_VALUES = {"High": defs.Priority.HIGH,
                             "Normal": defs.Priority.MEDIUM,
                             "Low": defs.Priority.LOW}
PRIORITY_VALUES_TO_LABELS = utils.invert_dict(PRIORITY_LABELS_TO_VALUES)


class GeeTeeDeeData(object):

    def __init__(self, summary, data_manager):
        self.summary = summary
        self.creation_date = datetime.datetime.now()
        self.priority = models.MEDIUM
        self.uuid = str(uuid.uuid1())
        self._completion_date = None
        self._queue_date = None
        self._due_date = None
        self._data_manager = data_manager

    @property
    def summary(self):
        return self._summary
    @summary.setter
    def summary(self, value):
        type_error = "Summary must be a str"
        assert isinstance(value, basestring), type_error
        self._summary = value

    @property
    def age(self):
        return (datetime.datetime.now() - self.creation_date).days

    @property
    def completion_date(self):
        return self._completion_date
    @completion_date.setter
    def completion_date(self, value):
        type_error = "completion_date must be a datetime.datetime or None"
        assert isinstance(value, datetime.datetime) or value is None, type_error
        self._completion_date = value

    @property
    def creation_date(self):
        try:
            return self._creation_date
        except AttributeError:
            return datetime.datetime.fromtimestamp(defs.CREATION_EPOCH)
    @creation_date.setter
    def creation_date(self, value):
        type_error = "creation_date must be a datetime.datetime or None"
        assert isinstance(value, datetime.datetime) or value is None, type_error
        self._creation_date = value

    @property
    def due_date(self):
        return self._due_date
    @due_date.setter
    def due_date(self, value):
        type_error = "due_date must be a datetime.date or None"
        assert isinstance(value, datetime.date) or value is None, type_error
        self._due_date = value

    @property
    def priority(self):
        return self._priority
    @priority.setter
    def priority(self, value):
        error = "priority must be 1, 2, or 3, representing 'High', " + \
                "'Normal', & 'Low', respectively."
        assert value in PRIORITY_VALUES_TO_LABELS.keys(), error
        self._priority = value

    @property
    def queue_date(self):
        if isinstance(self._queue_date, int):
            # work around a past mistake in how I stored date info
            self._queue_date = datetime.date.fromordinal(self._queue_date)
        return self._queue_date
    @queue_date.setter
    def queue_date(self, value):
        type_error = "queue_date must be a datetime.date or None"
        assert isinstance(value, datetime.date) or value is None, type_error
        self._queue_date = value

    def _mark_complete(self):
        self.completion_date = datetime.datetime.now()


class NextAction(GeeTeeDeeData):

    def __init__(self, summary, data_manager):
        super(NextAction, self).__init__(summary, data_manager)
        self.complete = False
        self.energy_est = models.NextAction.MEDIUM
        self.time_est = 10.0
        self._context = ""
        self._notes = None
        self._url = None

    def __str__(self):
        return "NextAction: {0}, uuid: {1}".format(self.summary, self.uuid)

    # PROPERTIES-A-GO-GO!
    @property
    def complete(self):
        return self._complete
    @complete.setter
    def complete(self, value):
        assert isinstance(value, bool), "'complete' property must be a bool."
        self._complete = value
        if self._complete:
            self._mark_complete()

    @property
    def context(self):
        return self._context
    @context.setter
    def context(self, value):
        assert isinstance(value, basestring), "Context must be a str"
        assert " " not in value, "Contexts must not contain spaces"
        value = '@' + value.lstrip('@').capitalize()
        self._context = value

    @property
    def energy_est(self):
        return self._energy_est
    @energy_est.setter
    def energy_est(self, value):
        error = "energy_est must be 0, 1, or 2, representing 'Low', " + \
                "'Normal', & 'High', respectively."
        assert value in ENERGY_VALUES_TO_LABELS.keys(), error
        self._energy_est = value

    @property
    def notes(self):
        return self._notes
    @notes.setter
    def notes(self, value):
        value = None if value == "" else value
        self._notes = value

    @property
    def time_est(self):
        return self._time_est
    @time_est.setter
    def time_est(self, value):
        error = ("time_est must be a float between 1 and 360 - a float "
                 "because that's what gtk.Spinbutton likes...")
        assert (1 <= value < 360), error
        self._time_est = float(value)

    @property
    def url(self):
        return self._url
    @url.setter
    def url(self, value):
        url_error = "WTF kind of URL is that?"
        assert value in (None, "", str("")) or "://" in value, url_error
        self._url = value


    # DISPLAY/UI-RELATED BITS
    # FIXME: this is waaaaaayy ghetto.
    # I think this can be done properly with Kiwi's column format setting?  Doesn't matter,
    # we're ditching Kiwi. :-/
    @property
    def formatted_summary(self):
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
        icon = defs_gui.NOTE_ICON_PIXBUF if self.notes else defs_gui.FAKE_ICON_PIXBUF
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
        icon = defs_gui.URL_ICON_PIXBUF if self.url else defs_gui.FAKE_ICON_PIXBUF
        return icon


class Project(GeeTeeDeeData):

    def __init__(self, summary, data_manager):
        super(Project, self).__init__(summary, data_manager)
        self.status = 'active'
        self.waiting_for_text = None
        self._aofs = []
        self._incubating_next_actions = []
        self._next_actions = []
        self.parent_project = TOP_LEVEL_PROJECT_LEGACY
        # FIXME: create a special observable list which notifies observers
        # of addition, replacement, deletion, etc - would keep a "natural", 
        # Pythonic interface, but would allow some controller-like behavior
        # for the owner of the list. 
        self.subprojects = []
        self._waiting_for_since = None

    def __str__(self):
        return "Project: {0}, uuid: {1}".format(self.summary, self.uuid)

    # PROPERTIES-A-GO-GO!
    #FIXME: not sure this one should live on indefinitely...
    @property
    def aofs(self):
        return self._aofs

    @property
    def incubating_next_actions(self):
        # FIXME: lame -- replace this property with a regular attribute
        return self._incubating_next_actions

    @property
    def key_name(self):
        return app_utils.format_for_dict_key(self.summary)

    @property
    def next_actions(self):
        # FIXME: lame -- replace this property with a regular attribute
        return self._next_actions

    @property
    def status(self):
        return self._status
    @status.setter
    def status(self, value):
        valid = ['active', 'incubating', 'waiting_for', 'queued', 'completed']
        assert value in valid, "status must be 'active', 'incubating'," + \
                                "'waiting_for', 'queued', or 'completed'"
        self._status = value
        if value == "completed":
            self._mark_complete()

    @property
    def waiting_for_since(self):
        return self._waiting_for_since
    @waiting_for_since.setter
    def waiting_for_since(self, value):
        type_error = "waiting_for_since must be a datetime.date"
        assert isinstance(value, datetime.date), type_error
        self._waiting_for_since = value

    # DISPLAY/UI-ONLY -- i.e.: these should be in a different class...
    @property
    def alert(self):
        """Indicate if the project is in an "alert" status."""
        if self._status != "active":
            return defs_gui.FAKE_ICON_PIXBUF
        else:
            for na in self.next_actions:
                if not na.complete:
                    return defs_gui.FAKE_ICON_PIXBUF
            return defs_gui.ALERT_ICON_PIXBUF

    @property
    def formatted_summary(self):
        formats = {1: '<b>{0}</b>', 
                   2: '{0}', 
                   3: '<span weight="light">{0}</span>'}
        fs = saxutils.escape(self.summary)
        return formats[self.priority].format(fs)
