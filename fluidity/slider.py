#!/usr/bin/python -O
#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""Contains the Slider app class"""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


try:
    import cPickle as pickle
except ImportError:
    import pickle
import datetime
import operator
import os
import time

import gtk

from collections import namedtuple

from kiwi.ui.objectlist import Column, ObjectList #pylint: disable-msg=W0611
from kiwi.ui.widgets.combobox import ProxyComboBox #pylint: disable-msg=W0611

from fluidity import defs
from fluidity import gee_tee_dee
from fluidity import ui
from fluidity import app_utils
from fluidity.magic_machine import MagicMachine
from fluidity.managers import DataManager


class Slider(object):

    def __init__(self, separate_process=False):
        """Initialize this Slider.

        Args:
            separate_process: If True, gtk.main_quit() will be called when the
                window closes.
        """
        app_utils.log_line("Starting Slider", datetime.datetime.now())

        self._is_separate_process = separate_process

        self._b = gtk.Builder()
        self._b.add_from_file(os.path.join(defs.APP_DATA_PATH, 'slider.ui'))
        self._b.connect_signals(self)

        self.data_lumbergh = DataManager()
        self._magical = MagicMachine(self.data_lumbergh)
        self._magic_checked = False

        self._map_fields_to_instance_names()
        self._init_ui()

    def fill_prj_list_w(self):
        prj_list = self.data_lumbergh.get_prjs_by_aof("All", "incomplete")
        prj_list.sort(key=operator.attrgetter('status', 'summary'))
        for prj in prj_list:
            pr = ProjectRow(prj.formatted_summary, prj.status, prj.key_name)
            if prj.summary == 'singletons':
                singletons_prj = pr
            self.prj_list_w.append(pr)
        self.prj_list_w.select(singletons_prj)

    def _add_note_to_prj(self):
        # FIXME: make this actually do something.
        print("CAN HAS PRJ NOTE?  YES!  CAN HAZ!")

    def _autocomplete_context(self, widget):
        context = self._magical.get_magic_context(widget.get_text())
        widget.set_text(context)

    def _create_inbox_note(self):
        note = {'summary': self.summary_w.get_text(),
                'details': self.note_details_w.get_buffer().props.text}
        file_name = (note['summary'][:50].replace(os.sep, '') +
                     str(time.time()) + "-note.pkl")
        file_path = os.path.join(defs.NOTE_SLIDER_FOLDER, file_name)
        with open(file_path, 'wb') as pickle_file:
            pickle.dump(note, pickle_file, pickle.HIGHEST_PROTOCOL)
        self._quit()

    def _create_incoming_na(self, na):
        """Create an incoming NextAction, if we have valid data for one in the form."""
        if self._validate_fields():
            prj = self.prj_list_w.get_selected()
            if prj and prj.key_name != "singletons":
                self._write_na(na, prj.key_name, "-na.pkl")
            elif self.queue_to_w.date:
                print(self.queue_to_w.date)
                if not na.queue_date:
                    na.queue_date = self.queue_to_w.date
                self._write_na(na, 'queued_singletons', "-queued_na.pkl")
            elif prj.key_name == "singletons":
                self._write_na(na, 'singletons', "-na.pkl")

    def _create_incoming_obj(self):
        self.DO_IT_w.grab_focus()
        if not self.expandotron.props.expanded:
            if not self._magic_checked:
                magic_na = self._get_magic_na(self.summary_w.props.text)
            if magic_na:
                self._fill_fields_from_magic(magic_na)
                self._create_incoming_na(magic_na)
            else:
                self._create_inbox_note()
        else:
            if self.create_inbox_note_w.get_active():
                self._create_inbox_note()
            elif self.add_note_to_prj_w.get_active():
                self._add_note_to_prj()
            elif self.create_na_w.get_active():
                na = self._create_na_from_fields()
                if na:
                    self._create_incoming_na(na)

    def _create_na_from_fields(self):
        na = None
        summary = self.summary_w.get_text()
        if summary:
            na = gee_tee_dee.NextAction(summary, self.data_lumbergh) # set summary
            na.context = self.context_w.get_text()       # set context
            na.time_est = self.time_est_w.get_value()    # set time_est
            na.energy_est = self._na_energy_est          # set energy_est
            na.priority = self._get_priority()           # set priority
            if self.due_date_w.date:
                na.due_date = self.due_date_w.date       # set due_date
            if self.queue_to_w.date:
                na.queue_date = self.queue_to_w.date     # set queue date
            url = self.url_w.get_text()                  # set url
            if url != "":
                na.url = url
            notes = self.na_notes_w.get_buffer().props.text     # set notes
            na.notes = notes if notes != "" else None
        return na

    def _fill_fields_from_magic(self, magic_na):
        self.summary_w.props.text = magic_na.summary
        p_o_a = namedtuple("PropObjAttr", "property object attribute")
        poas = [p_o_a(prop, obj, attr) for prop, obj, attr in
                    (("context", self.context_w.props, 'text'),
                     ("time_est", self.time_est_w.props, 'value'),
                     ("energy_est", self, '_na_energy_est'),
                     ("priority", self, '_na_priority_est'),
                     ("due_date", self.time_est_w, 'date'),
                     ("queue_date", self.queue_to_w, 'date'),
                     ("url", self.url_w.props, 'text'),
                     ("notes", self.na_notes_w.get_buffer().props, 'text'),)]
        for poa in poas:
            value = magic_na.__getattribute__(poa.property)
            if value or value == 0:
                poa.object.__setattr__(poa.attribute, value)
        self._validate_fields()

    def _get_magic_na(self, summary_text):
        self._magic_checked = True
        mt = self._magical.get_magic_task(summary_text)
        has_magic = False
        # if our dict doesn't have these keys, our magic failed, and we
        # should show the dialog instead
        magic_keys = ['context', 'time_est', 'energy_est', 'priority', 'due_date']
        for key in mt.keys():
            if key in magic_keys:
                has_magic = True
        # 'url' left out of magic_keys prior b/c it's not an integral part of a
        # NextAction; adding it back in now so we can use it as a generic attr list
        magic_keys.append('url')
        if has_magic:
            na = gee_tee_dee.NextAction(mt['summary'], self.data_lumbergh)
            for key in mt.keys():
                if key in magic_keys:
                    na.__setattr__(key, mt[key])
            return na
        else:
            return None

    def _get_priority(self):
        label = self.priority_w.get_selected_label()
        return ui.PRIORITY_LABELS_TO_VALUES[label]

    def _init_prj_list_w(self, obj_list):
        obj_list.set_columns([Column('formatted_summary', title='Summary',
                                     data_type=str, use_markup=True,
                                     searchable=True, expand=True),
                              Column('status', data_type=str)])

    def _init_ui(self):
        self._init_prj_list_w(self.prj_list_w)
        self._b.get_object("energy_w").select_item_by_position(1)
        self._b.get_object("priority_w").select_item_by_position(1)
        self._b.get_object("time_est_w").set_value(defs.DEFAULT_TIME_EST)
        # set "Create Next Action" as the default mode
        self.create_na_w.clicked()
        # give the date fields their date name, as None
        self.due_date_w.date = None
        self.queue_to_w.date = None
        self._set_ui_mode(self.create_na_w)

    def _map_fields_to_instance_names(self):
        self.add_na_label = self._b.get_object("add_na_label")
        self.add_note_label = self._b.get_object("add_note_label")
        self.add_note_to_prj_w = self._b.get_object("add_note_to_prj_w")
        self.context_w = self._b.get_object("context_w")
        self.create_inbox_note_w = self._b.get_object("create_inbox_note_w")
        self.create_na_w = self._b.get_object("create_na_w")
        self.DO_IT_w = self._b.get_object("DO_IT_w")
        self.due_date_w = self._b.get_object("due_date_w")
        self.energy_est_w = self._b.get_object("energy_w")
        self.expandotron = self._b.get_object("expandotron")
        self.na_notes_w = self._b.get_object("na_notes_w")
        self.na_table = self._b.get_object("na_table")
        self.note_details_box = self._b.get_object("note_details_box")
        self.note_details_w = self._b.get_object("note_details_w")
        self.priority_w = self._b.get_object("priority_w")
        self.prj_list_box = self._b.get_object("prj_list_box")
        self.prj_list_w = self._b.get_object("prj_list_w")
        self.queue_to_w = self._b.get_object("queue_to_w")
        self.summary_w = self._b.get_object("summary_w")
        self.time_est_w = self._b.get_object("time_est_w")
        self.url_w = self._b.get_object("url_w")
        self.window = self._b.get_object("ntng_dialog")

    @property
    def _na_energy_est(self):
        label = self.energy_est_w.get_selected_label()
        return ui.ENERGY_LABELS_TO_VALUES[label]
    @_na_energy_est.setter
    def _na_energy_est(self, value):    #pylint: disable-msg=E0102
        label = ui.ENERGY_VALUES_TO_LABELS[value]
        self.energy_est_w.select_item_by_label(label)

    @property
    def _na_priority_est(self):
        label = self.priority_w.get_selected_label()
        return ui.PRIORITY_LABELS_TO_VALUES[label]
    @_na_priority_est.setter
    def _na_priority_est(self, value):  #pylint: disable-msg=E0102
        label = ui.PRIORITY_VALUES_TO_LABELS[value]
        self.priority_w.select_item_by_label(label)

    def _quit(self):
        app_utils.log_line("Exiting Slider normally.", datetime.datetime.now())
        # don't quit if we're not actually running as a separate process.. heh.
        if self._is_separate_process:
            gtk.main_quit()
        else:
            self.window.destroy()

    def _set_ui_mode(self, widget):
        summary_text = self.summary_w.get_text()
        if gtk.Buildable.get_name(widget) == "create_na_w":
            self.na_table.show()
            self.note_details_box.hide()
            self.prj_list_box.show()
            self.add_na_label.show()
            self.add_note_label.hide()
            if summary_text != "":
                self.context_w.grab_focus()
            if not self._magic_checked and summary_text:
                magic = self._get_magic_na(summary_text)
                if magic:
                    self._fill_fields_from_magic(magic)
        elif gtk.Buildable.get_name(widget) == "create_inbox_note_w":
            self.na_table.hide()
            self.note_details_box.show()
            self.prj_list_box.hide()
            if summary_text != "":
                self.note_details_w.grab_focus()
        elif gtk.Buildable.get_name(widget) == "add_note_to_prj_w":
            self.na_table.hide()
            self.note_details_box.show()
            self.prj_list_box.show()
            self.add_na_label.hide()
            self.add_note_label.show()
            if summary_text != "":
                self.note_details_w.grab_focus()

    def _set_valid_date_w(self, widget):
        if widget.get_text() == "":
            widget.date = None
        else:
            # We'll get None on failure here, so we're safe either way
            widget.date = self._magical.get_magic_date(widget.get_text())
            # get_magic_date() didn't understand the mystery meat you fed it.
            if widget.date == None:
                widget.set_text(defs.UNRECOGNIZED_DATE_TEXT)
            else:
                date_text = widget.date.strftime(defs.GTK_DATE_TEXT_TEMPLATE)
                widget.set_text(date_text)

    def _validate_fields(self):
        # fuck it.  I don't care how unreadable, unmaintainable, or otherwise
        # shameful this is.  i just want it done.
        if self.summary_w.get_text() == "":
            self.summary_w.grab_focus()
            self.expandotron.set_expanded(True)
            return False
        context = self.context_w.get_text()
        # if we have an @ at the beginning, don't make that the "capitalize" char
        if context != "":
            context = context[0] + context[1:].capitalize()
            self.context_w.set_text(context)
        if " " in context or not context.startswith('@'):
            self.expandotron.set_expanded(True)
            self.context_w.grab_focus()
            return False
        if self.due_date_w.get_text() == defs.UNRECOGNIZED_DATE_TEXT:
            self.expandotron.set_expanded(True)
            self.due_date_w.grab_focus()
            return False
        if self.queue_to_w.get_text() == defs.UNRECOGNIZED_DATE_TEXT:
            self.expandotron.set_expanded(True)
            self.queue_to_w.grab_focus()
            return False
        return True

    def _write_na(self, na, prj_key, ext):
        to_dump = {'prj_key': prj_key, 'na_obj': na}
        fname = "".join((app_utils.format_for_dict_key(na.summary)[:50],
                         str(time.time()), ext))
        with open(os.path.join(defs.NOTE_SLIDER_FOLDER, fname), 'wb') as pfile:
            pickle.dump(to_dump, pfile, pickle.HIGHEST_PROTOCOL)
        self._quit()

# CALLBACKS
    def context_w_focus_out_event_cb(self, widget, data=None):
        self._autocomplete_context(widget)

    def date_w_focus_out_event_cb(self, widget, data=None):
        self._set_valid_date_w(widget)

    def DO_IT_w_clicked_cb(self, widget, data=None):
        self._create_incoming_obj()

    def expandotron_activate_cb(self, widget, data=None):
        """Ensures the UI is set up correctly & the best widget is focused."""
        if not widget.props.expanded:
            self.summary_w.grab_focus()
        else:
            for w in (self.create_inbox_note_w, self.create_na_w,
                      self.add_note_to_prj_w):
                if w.get_active():
                    self._set_ui_mode(w)
                    break

    # hml, i.e.: "high, medium, low"
    def hml_combo_key_press_event_cb(self, widget, data=None):
        ui.type_ahead_combo(widget, data)

    # "mode toggles" here meaning "the toggle buttons effecting app mode"
    def mode_toggles_clicked_cb(self, widget, data=None):
        if widget.get_active() and self.expandotron.props.expanded:
            self._set_ui_mode(widget)

    def na_notes_expander_activate_cb(self, widget, data=None):
        if widget.get_expanded():
            self._previously_focused = self.window.get_focus()
            self.na_notes_w.grab_focus()
        else:
            self._previously_focused.grab_focus()

    def prj_list_w_focus_in_event_cb(self, widget, data=None):
        # Why do we have to grab focus after we're... focused?  bleh.
        # BIZZARRO!  I LOVE YOu@
        selected_row = widget.get_selected_row_number()
        if not selected_row:
            selected_row = 0
        widget.grab_focus()
        widget.select_paths([selected_row])
        widget._select_and_focus_row(selected_row)

    def prj_list_w_row_activated_cb(self, widget, data=None):
        self._create_incoming_obj()

    def quit_cb(self, widget, data=None):
        self._quit()

    def summary_w_key_press_event_cb(self, widget, data=None):
        # if the keypress is "down arrow", expand the Expand-o-tron
        if (gtk.gdk.keyval_name(data.keyval) == "Down"
            and self.expandotron.props.expanded == False):
            self.expandotron.set_expanded(True)

    def url_w_focus_out_event_cb(self, widget, data=None):
        url = widget.get_text()
        if "://" not in url and url != "":
            widget.set_text("http://" + url)

    def url_w_icon_press_cb(self, widget, icon=None, event=None):
        self.url_w_focus_out_event_cb(widget)
        gtk.show_uri(gtk.gdk.Screen(), widget.get_text(), int(time.time()))


class ProjectRow(object):
# pylint: disable-msg=R0903
    def __init__(self, formatted_summary, status, key_name):
        self.formatted_summary = formatted_summary
        self.status = status.capitalize()
        self.key_name = key_name


def run():
    slider_app = Slider(True)
    slider_app.window.show()
    slider_app.fill_prj_list_w()
    gtk.main()


if __name__ == "__main__":
    print("""HEY YOU: Yes, you, the user -- DON'T RUN THIS DIRECTLY!  Use the
launching script 'slider' in your system path (e.g.: in /usr/bin/), or if you're
running straight out of the folder from the .tar.gz file you grabbed, then look
for the script in the "bin" folder.""")
    run()
