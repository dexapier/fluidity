'''slider app class coded for gtk3'''
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

from gi.repository import Gtk
from collections import namedtuple

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

        self._builder = Gtk.Builder()
        self._builder.add_from_file(os.path.join(defs.APP_DATA_PATH, 'slider_ui.gtk3.glade'))
        self._builder.connect_signals(self)

        self._data_lumbergh = DataManager()
        self._magical = MagicMachine(self._data_lumbergh)
        self._magic_checked = False

        self._map_fields_to_instance_names()
        self._init_ui()
        
    def _map_fields_to_instance_names(self):
        self.add_na_label = self._builder.get_object("add_na_label")
#        self.add_note_label = self._builder.get_object("add_note_label")
#        self.add_note_to_prj_w = self._builder.get_object("add_note_to_prj_w")
        self.context_w = self._builder.get_object("context_w")
        self.create_inbox_note_w = self._builder.get_object("create_inbox_note_w")
        self.create_na_w = self._builder.get_object("create_na_w")
        self.DO_IT_w = self._builder.get_object("DO_IT_w")
        self.due_date_w = self._builder.get_object("due_date_w")
        self.energy_est_w = self._builder.get_object("energy_w")
        self.expandotron = self._builder.get_object("expandotron")
        self.na_notes_w = self._builder.get_object("na_notes_w")
        self.na_table = self._builder.get_object("na_table")
#        self.note_details_box = self._builder.get_object("note_details_box")
#        self.note_details_w = self._builder.get_object("note_details_w")
        self.priority_w = self._builder.get_object("priority_w")
#        self.prj_list_box = self._builder.get_object("prj_list_box")
        self.prj_list_w = self._builder.get_object("prj_list_w")
        self.queue_to_w = self._builder.get_object("queue_to_w")
        self.summary_w = self._builder.get_object("summary_w")
        self.time_est_w = self._builder.get_object("time_est_w")
        self.url_w = self._builder.get_object("url_w")
        self.window = self._builder.get_object("ntng_dialog")