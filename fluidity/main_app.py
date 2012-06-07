#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""The main Fluidity app module."""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


import datetime
import operator
import os
import shutil
import sys
import time

import dbus   #@UnusedImport
import dbus.mainloop.glib
import dbus.service
import gobject
import gtk
import kiwi
import pango

import fluidity.ui.dialogs as dialogs

from kiwi.ui.objectlist import Column, ObjectList   #pylint: disable-msg=W0611
from kiwi.ui.widgets.combobox import ProxyComboBox  #pylint: disable-msg=W0611
from kiwi.ui.widgets.textview import ProxyTextView  #pylint: disable-msg=W0611

from fluidity import app_utils
from fluidity import boxidate
from fluidity import defs
from fluidity import gee_tee_dee
from fluidity import inbox_items
from fluidity import managers
from fluidity import task_export
from fluidity import ui
from fluidity.magic_machine import MagicMachine
from fluidity.note import ProjectNote


class Fluidity(object):
    """Main Fluidity application class."""

    def __init__(self):
        # first things first...
        app_utils.log_line("Launching Fluidity", datetime.datetime.now())
        self._enforce_running_as_singleton(defs.DBUS_BUS_NAME,
                                           defs.DBUS_OBJECT_PATH)
        # SAY MY NAME!
        gobject.set_prgname(defs.APP_NAME)
        gobject.set_application_name(defs.APP_NAME)

        self.data_lumbergh = managers.DataManager()
        self.data_lumbergh.activate_due_queued()
        self.b = gtk.Builder()
        self.b.add_from_file(os.path.join(defs.APP_DATA_PATH, 'fluidity.ui'))
        self.b.connect_signals(self)

        self.map_fields_to_instance_names()

        app_utils.validate_paths()

        self._magical = MagicMachine()
        self._inbox_manager = managers.InboxManager(self, self.stuff_tree_w,
                                                    self.data_lumbergh)
        self._inbox_manager.gather_slider_items()

        self._rec_manager = managers.RecurrenceManager(self.data_lumbergh)
        gobject.idle_add(self._rec_manager.place_recurring_tasks)

        jesus = managers.BackupJesus()
        gobject.idle_add(jesus.kill_stale_backups)
        del(jesus)

        self._search_window = dialogs.JumptoSearchDialog(self.data_lumbergh, self)

        self.clipboard = gtk.clipboard_get()

        self.init_ui()

        gobject.timeout_add_seconds(defs.AUTOSAVE_INTERVAL,
                                    self.data_lumbergh.autosave)
        self._run_daily_tasks(False)
        gtk.gdk.notify_startup_complete()

    def _enforce_running_as_singleton(self, bus_name, obj_path):
        """Ensure this app is a singleton; register a 'well-known' D-Bus bus name.

        No object paths are currently defined - the sole purpose of registering
        the bus name is to ensure that we only ever run one copy of the app.

        The main purpose here is to avoid having two copies of the app trying to
        modify the data file at once.  Possibly hackish, but better than the
        stupid thing I had it doing before.
        """
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        session_bus = dbus.SessionBus()
        try:
            name = dbus.service.BusName(bus_name, session_bus,
                                        allow_replacement=False,
                                        replace_existing=False,
                                        do_not_queue=True)
            dbus.service.Object(name, obj_path)
        except dbus.exceptions.NameExistsException:
            #no good.  we're bailing.
            dialog = gtk.Dialog("Error",
                        flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
            error_label = gtk.Label()
            error_label.set_use_markup(True)
            error_msg = "Fluidity is already running."
            error_label.set_markup("<big><b>" + error_msg + "</b></big>")
            fuck_you_gtk = gtk.Alignment()
            fuck_you_gtk.set_padding(12, 24, 12, 12)
            fuck_you_gtk.add(error_label)
            dialog.get_content_area().pack_start(fuck_you_gtk)
            dialog.get_content_area().set_border_width(12)
            error_label.show()
            fuck_you_gtk.show()
            dialog.run()
            app_utils.log_line("Exiting -- found another process with the same "
                            "D-Bus bus name.", datetime.datetime.now())
            sys.exit("Another process has that bus name; " + error_msg)

    def add_file_to_prj(self, prj):
        chooser = gtk.FileChooserDialog(action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_ADD, gtk.RESPONSE_OK))
        chooser.set_property("select-multiple", True)
        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            file_names = chooser.get_filenames()
            for f in file_names:
                self.data_lumbergh.copy_to_project_folder(f, prj)
            #now re-fill the project's files ObjectList
            self.fill_prj_support_files_w(prj)
        chooser.destroy()
        chooser = None

    def attach_stuff_to_prj(self, prj_key, stuff):
        prj = self.data_lumbergh.prjs[prj_key]
        if isinstance(stuff, inbox_items.InboxFile):
            self.data_lumbergh.copy_to_project_folder(stuff.path, prj)
        elif isinstance(stuff, inbox_items.InboxNote):
            prj_ = prj
            note = ProjectNote(prj=prj_)
            note.add_stuff(stuff)

    def complete_project(self, prj):
        self.data_lumbergh.change_project_status(prj, "completed")
        self.fill_prj_list_w()

    def consolidate_inboxes(self, widget):
        # FIXME: this shit really belongs in DataManager
        # Also, it needs to actually work for other people... *cough*
        if os.environ.get("USER") != "jensck":
            pass
        else:
            self.temporarily_disable_widget(widget)
            boxidate.consolidate()
            self._inbox_manager.gather_slider_items()
            self._inbox_manager.add_actual_shit_to_columns()
            self.temporarily_disable_widget(widget)

    def create_new_aof(self):
        d = self.b.get_object("new_aof_dialog")
        e = self.b.get_object("new_aof_name_w")
        if d.run() == gtk.RESPONSE_APPLY:
            aof_name = e.get_text()
            e.set_text("")
            self.data_lumbergh.create_new_aof(aof_name)
            self.fill_aofs_w(self.aof_filter_w, self.data_lumbergh.aof_names())
            self.fill_aofs_w(self.prj_details_aofs_w,
                             self.data_lumbergh.aof_names(), False)
        d.hide()

    def delete_na(self, na):
        prj = self.prj_list_w.get_selected()
        na_index = self.prj_details_na_list_w.index(na)
        self.data_lumbergh.delete_na(na, prj)
        self.fill_prj_details_na_list_w(self.prj_list_w.get_selected())
        self.prj_details_na_list_w.select_paths([na_index - 1])

    def delete_prj(self, prj):
        self.data_lumbergh.delete_prj(prj)
        self.fill_prj_list_w()

    def display_prj_notes(self, prj_):
        ProjectNote(prj=prj_).show()

    def edit_extant_na(self, na):
        #FIXME: review this later - is it doing what we intend?
        # also, in case I forget - this isn't a datamanager issue - the NAD should
        # take care of the actual data question with
        nad = dialogs.NewNextActionDialog(self, self.data_lumbergh)
        nad.edit_extant_na(na)
        nad = None

    def file_stuff_as_reference(self, stuff):
        title_text = "Please select the folder where you would like to move this file to"
        chooser = gtk.FileChooserDialog(title=title_text,
                                        action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                        buttons=(gtk.STOCK_CANCEL, 
                                                 gtk.RESPONSE_CANCEL,
                                                 gtk.STOCK_SAVE_AS,
                                                 gtk.RESPONSE_OK))
        ok_button = chooser.get_child().get_children()[1].get_children()[0]
        ok_button.set_label("Move file")
        home_dir = os.getenv("HOME")
        chooser.set_current_folder_uri("file://" + home_dir)
        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            new_location = chooser.get_filename()
            try:
                shutil.move(stuff.path, os.path.join(new_location, stuff.summary))
            except IOError:
                print("Something has gone wrong.  Oops.")
        chooser.destroy()
        chooser = None
        self._inbox_manager.complete_processing(stuff)

    def fill_aofs_w(self, widget, aofs, all_item=True):
        widget.clear()
        if all_item:
            widget.append_item('All')
        for i in sorted(aofs):
            widget.append_item(i)
        widget.append_item(defs.NO_AOF_ASSIGNED)
        widget.select_item_by_position(0)

    def fill_engage_context_w(self, widget):
        widget.clear()
        self.engage_context_w.append_item('Any')
        contexts = self.data_lumbergh.get_contexts()
        for i in contexts:
            self.engage_context_w.append_item(i)
        self.engage_context_w.set_active(0)

    def fill_engage_na_list(self):
        energy = self.engage_energy_level_w.get_selected_label()
        max_time = self.engage_time_available_w.get_selected_label()
        due_only = self.engage_due_today_filter_w.props.active
        today = datetime.date.today()
        # FIXME: when things are loading up for the first time, we get
        # NoneType problems - i need to eventually fix this properly.
        if max_time:
            if "+" in max_time:
                max_time = 1000.0  # catch-all for "60+" minutes
            else:
                max_time = float(max_time)
        context = self.engage_context_w.get_selected()
        candidate_nas = []
        active_nas = self.data_lumbergh.get_na_for_each_active_prj()
        # and of those, get all the ones which meet our filter criteria
        for n in active_nas:
            if (context == "Any" and 'agenda' not in n.context.lower() or
                    n.context == context):
                if n.time_est > max_time:
                    continue
                
                na_energy = ui.ENERGY_VALUES_TO_LABELS[n.energy_est]
                if energy != "Any" and na_energy != energy:
                    continue

                if due_only and (n.due_date is None or n.due_date > today):
                    continue

                candidate_nas.append(n)

        # next, sort the filtered candidates
#        candidate_nas.sort(key=operator.attrgetter('time_est', 'energy_est'),
#                                                   reverse=True)
#        candidate_nas.sort(key=operator.attrgetter('sort_date', 'priority',
#                                                   'context'))
#        candidate_nas.sort(key=operator.attrgetter('age'), reverse=True)
#        candidate_nas.sort(key=operator.attrgetter('sort_date', 'priority',
#                                                   'context'))

#        candidate_nas.sort(key=operator.attrgetter('foo', 'bar'), reverse=True)
#        candidate_nas.sort(key=operator.attrgetter('foo', 'bar'))

        candidate_nas = self.sort_actions(candidate_nas)

        # Clear the list and re-populate it appropriately
        self.engage_na_list.clear()
        for na in candidate_nas:
            self.engage_na_list.append(na)
        total_time, tasks_count = 0, 0
        # FIXME: review this - should I really be hardcoding the exclusion
        # of Agendas?
        for na in self.engage_na_list:
            context = na.context
            if context is not None and "agenda" not in context.lower():
                total_time = int(total_time + na.time_est)
                tasks_count += 1
        hours = total_time // 60
        mins = total_time % 60
        self.engage_current_totals_w.set_text(
                defs.ENGAGE_TOTALS_TEMPLATE.format(tasks_count, hours, mins))
        self.engage_na_list.select_paths([0])

    def sort_actions(self, active_actions_to_sort):
        # first line we make a copy of the list; then we just modify it in place for convenience
        active_actions_to_sort = sorted(active_actions_to_sort, key=operator.attrgetter('context'))
        active_actions_to_sort.sort(key=operator.attrgetter('age', 'time_est', 'energy_est'),
                                    reverse=True)
        active_actions_to_sort.sort(key=operator.attrgetter('sort_date', 'priority'))
        return active_actions_to_sort

    def fill_na_list_w(self, prj=None):
        if not prj:
            prj = self.prj_list_w.get_selected()
        self.fill_prj_details_na_list_w(prj)

    def fill_prj_details(self, prj):
        self.prj_details_na_list_w.clear()
        for widget in (self.prj_details_due_date_w, 
                       self.prj_details_queue_date_w,
                       self.prj_details_waiting_for_w,
                       self.prj_details_waiting_for_since_w):
            widget.props.text = ""
        prj = self.prj_list_w.get_selected()
        if prj:
            self.fill_prj_details_na_list_w(prj)
            self.fill_prj_support_files_w(prj)
            if prj.due_date:
                self.prj_details_due_date_w.set_text(
                            prj.due_date.strftime(defs.GTK_DATE_TEXT_TEMPLATE))
            if prj.queue_date:
                self.prj_details_queue_date_w.set_text(
                            prj.queue_date.strftime(defs.GTK_DATE_TEXT_TEMPLATE))
            if prj.waiting_for_text:
                self.prj_details_waiting_for_w.set_text(prj.waiting_for_text)
            if prj.waiting_for_since:
                self.prj_details_waiting_for_since_w.set_text(
                    prj.waiting_for_since.strftime(defs.GTK_DATE_TEXT_TEMPLATE))
            self.prj_details_aofs_w.select_item_by_label(
                        self.data_lumbergh.get_prj_aof_names(prj)[0])
            translated = ui.translate_priority(prj.priority)
            self.prj_details_priority_w.select_item_by_label(translated)

    #FIXME: put this in dm???  does this need fixing?
    def fill_prj_details_na_list_w(self, prj):
        self.prj_details_na_list_w.clear()
        for n in prj.next_actions:
            self.prj_details_na_list_w.append(n)
        self.prj_details_incubating_na_list_w.clear()
        for n in prj.incubating_next_actions:
            self.prj_details_incubating_na_list_w.append(n)

    def fill_prj_list_w(self, area_name=None, rfilter=None):
        if area_name == None:
            area_name = self.aof_filter_w.get_selected()
        if rfilter == None:
            rfilter = self.get_prj_review_status_filter()
        # when aof selector contents are getting shuffled around, 'area_name'
        # will be None, which of course causes problems.
        if area_name:
            self.prj_list_w.clear()
            prjs = self.data_lumbergh.get_prjs_by_aof(area_name, rfilter)
            self.prj_list_w.extend(prjs)
            self.prj_list_w.select_paths([0])
        pdbox = self.b.get_object("project_details_vbox")
        if len(self.prj_list_w) <= 0:
            pdbox.hide()
        else:
            pdbox.show()

    def fill_prj_support_files_w(self, prj):
        self.prj_support_files_w.clear()
        file_list = self.data_lumbergh.get_file_list_for_prj(prj)
        for f in file_list:
            row = ui.ProjectSupportFileRow(f)
            self.prj_support_files_w.append(row)
        self.prj_support_files_w.sort_by_attribute("isdir", order=gtk.SORT_ASCENDING)
        self.prj_support_files_w.sort_by_attribute("name_lowercase",
                                                   order=gtk.SORT_ASCENDING)

    def fill_stuff_details(self, obj):
        if isinstance(obj, inbox_items.InboxNote):
            self.clarify_stuff_details_notebook.set_current_page(0)
            self.clarify_notes_details_summary_w.set_text(obj.summary)
            if obj.details:
                self.clarify_notes_details_details_w.update(obj.details)
            else:
                self.clarify_notes_details_details_w.update("")
            self.clarify_stuff_details_notebook.show()
            self.clarify_file_as_reference_w.props.sensitive = False
            self.clarify_add_to_read_review_w.props.sensitive = False
        elif isinstance(obj, inbox_items.InboxFile):
            self.clarify_stuff_details_notebook.set_current_page(2)
            self.clarify_file_details_name_w.set_text(obj.summary)
            self.clarify_file_details_type_w.set_text(obj.mime_type)
            self.clarify_file_details_size_w.set_text(obj.size)
            self.clarify_file_details_path_w.set_text(obj.parent.path)
            self.clarify_file_details_notes_w.update(obj.notes)
            self.clarify_file_details_icon_w.set_from_pixbuf(obj.icon)
            self.clarify_stuff_details_notebook.show()
            self.clarify_file_as_reference_w.props.sensitive = True
            self.clarify_add_to_read_review_w.props.sensitive = True
#            self.clarify_file_details_mime_nb_w.show()
#            if obj.generic_type == 'text':
#                self.clarify_file_info_text_preview_w.update(obj.get_preview())
#                self.clarify_file_details_mime_nb_w.set_current_page(1)
#            if obj.generic_type == 'image':
#                self.clarify_file_info_image_thumbnail_w.set_from_pixbuf(obj.get_preview())
#                self.clarify_file_details_mime_nb_w.set_current_page(2)
#            else:
#                self.clarify_file_details_mime_nb_w.hide()
        else:
            self.clarify_stuff_details_notebook.hide()

    def get_prj_review_status_filter(self):
        group = self.b.get_object("review_active_w").get_group()
        for b in group:
            if b.get_active():
                if gtk.Buildable.get_name(b) == 'review_active_w':
                    return "active"
                elif gtk.Buildable.get_name(b) == 'review_incubating_w':
                    return "incubating"
                elif gtk.Buildable.get_name(b) == 'review_waiting_for_w':
                    return "waiting_for"
                elif gtk.Buildable.get_name(b) == 'review_queued_w':
                    return "queued"
                elif gtk.Buildable.get_name(b) == 'review_completed_w':
                    return "completed"

    def incubate_project(self, prj):
        self.data_lumbergh.change_project_status(prj, "incubating")
        self.fill_prj_list_w()

    def mark_project_as_waiting_for(self, prj):
        # throw out a dialog to ask for the waiting_for_text and waiting_for_since
        wfd = dialogs.WaitingForDialog()
        wf_results = wfd.get_waiting_for_info()
        prj.waiting_for_since = wf_results[0]
        prj.waiting_for_text = wf_results[1]
        self.data_lumbergh.change_project_status(prj, "waiting_for")
        self.fill_prj_list_w()

    def init_engage_na_list(self, obj_list):
        obj_list.set_columns(
            [Column('uuid', data_type=str, visible=False),
             Column('complete', title=' ', data_type=bool, editable=True),
             Column('formatted_summary', title="Summary", data_type=str,
                    use_markup=True, searchable=True, expand=True,
                    ellipsize=pango.ELLIPSIZE_END),
             Column('url_icon', title=' ', data_type=gtk.gdk.Pixbuf),
             Column('notes_icon', title=' ', data_type=gtk.gdk.Pixbuf),
             Column('context', title="Context", data_type=str),
             Column('due_date', title='Due date', data_type=datetime.date),
             Column('time_est', title='Time', data_type=float),
             Column('energy_est_word', title='Energy', data_type=str),
             Column('age', title='Age', data_type=str)])

    def init_prj_details_na_list_w(self, obj_list):
        obj_list.set_columns([Column('uuid', data_type=str, visible=False),
                              Column('complete', data_type=bool, editable=True),
                              Column('context', data_type=str),
                              Column('formatted_summary', data_type=str,
                                     use_markup=True, searchable=True),
                              Column('due_date', data_type=str)])
        obj_list.set_headers_visible(False)

    def init_prj_list_w(self, obj_list):
        obj_list.set_columns([Column('alert', data_type=gtk.gdk.Pixbuf,
                                     visible=True),
                              Column('summary', data_type=str, searchable=True),
                              Column('key_name', data_type=str, visible=False),
                              Column('priority', data_type=int, visible=False)])
        obj_list.set_headers_visible(False)

    def init_prj_support_files_w(self, obj_list):
        #I have no idea why 23 worked best.
        obj_list.set_columns([Column('icon', width=23, data_type=gtk.gdk.Pixbuf),
                              Column('file_name', data_type=str, searchable=True,
                                     expand=True),
                              Column('full_path', data_type=str, visible=False),
                              Column('name_lowercase', data_type=str,
                                     visible=False),
                              Column('isdir', data_type=bool, visible=False)])
        obj_list.set_headers_visible(False)

    def init_ui(self):
        """Collection of mostly one-liners to set some UI details."""
        self.fill_aofs_w(self.prj_details_aofs_w, self.data_lumbergh.aof_names(),
                         False)
        self.init_prj_list_w(self.prj_list_w)
        self.fill_aofs_w(self.aof_filter_w, self.data_lumbergh.aof_names())
        self.init_prj_details_na_list_w(self.prj_details_na_list_w)
        self.init_prj_details_na_list_w(self.prj_details_incubating_na_list_w)
        self.workflow_nb.set_show_tabs(False)
        self.init_prj_support_files_w(self.prj_support_files_w)
        self.init_engage_na_list(self.engage_na_list)
        self.show_correct_project_action_buttons()
        self.engage_energy_level_w.select_item_by_position(0)
        #FIXME: wow, this blows.
        self._inbox_manager.add_actual_shit_to_columns()
        self.clarify_stuff_details_notebook.set_show_tabs(False)
        self.stuff_tree_w.get_treeview().props.enable_search = False
        #show Review tab by default when starting up
        self.b.get_object("show_review_tab").set_active(True)
        self.engage_na_list.get_treeview().connect('button-press-event',
                                                   self.engage_na_list_click_cb)
        self.clarify_file_details_mime_nb_w.set_show_tabs(False)
        self.clarify_file_details_mime_nb_w.hide()

    def jump_to_search_result(self, prj_key, na_uuid=None):
        status_widget_map = (("active", "review_active_w"),
                             ("incubating", "review_incubating_w"),
                             ("waiting_for", "review_waiting_for_w"),
                             ("queued", "review_queued_w"),
                             ("completed", "review_completed_w"))
        # First, "clear" AOF selector, select the right prj status,
        # so we can actually see the project/na
        self.aof_filter_w.select_item_by_position(0)
        self.b.get_object("show_review_tab").set_active(True)
        prj = self.data_lumbergh.prjs[prj_key]
        for status, widget in status_widget_map:
            if prj.status == status:
                self.b.get_object(widget).set_active(True)
                break
        self.prj_list_w.select(prj, scroll=True)
        if na_uuid:
            self.b.get_object("prj_details_notebook").set_current_page(0)
            for na in self.prj_details_na_list_w:
                if na.uuid == na_uuid:
                    self.prj_details_na_list_w.select(na, scroll=True)
                    gobject.idle_add(self.prj_details_na_list_w.grab_focus)
                    break

    def map_fields_to_instance_names(self):
        """Collection of one-liners to set up convenient names for UI elements"""
        self.window = self.b.get_object("main_window")
        self.aof_filter_w = self.b.get_object("aof_filter_w")
        self.clarify_add_to_read_review_w = \
                self.b.get_object("clarify_add_to_read_review_w")
        self.clarify_file_as_reference_w = \
                self.b.get_object("clarify_file_as_reference_w")
        self.clarify_image_preview = self.b.get_object("clarify_image_preview")
        self.clarify_nb = self.b.get_object("clarify_notebook")
        self.clarify_notes_copy_summary_w = \
                self.b.get_object("clarify_notes_copy_summary_w")
        self.clarify_notes_details_details_w = \
                self.b.get_object("clarify_notes_details_details_w")
        self.clarify_notes_details_summary_w = \
                self.b.get_object("clarify_notes_details_summary_w")
        self.clarify_stuff_details_notebook = \
                self.b.get_object("clarify_stuff_details_notebook")
        self.engage_context_w = self.b.get_object("engage_context_w")
        self.engage_current_totals_w = \
                self.b.get_object("engage_current_totals_w")
        self.engage_energy_level_w = self.b.get_object("engage_energy_level_w")
        self.engage_na_list = self.b.get_object("engage_na_list")
        self.engage_due_today_filter_w = \
                self.b.get_object("engage_due_today_filter_w")
        self.engage_time_available_w = \
                self.b.get_object("engage_time_available_w")
        self.new_prj_d = self.b.get_object("new_prj_dialog")
        self.prj_details_aofs_w = self.b.get_object("prj_details_aofs_w")
        self.prj_details_due_date_w = self.b.get_object("prj_details_due_date_w")
        self.prj_details_incubating_na_list_w = \
                self.b.get_object("prj_details_incubating_na_list_w")
        self.prj_details_na_list_w = self.b.get_object("prj_details_na_list_w")
        self.prj_details_priority_w = self.b.get_object("prj_details_priority_w")
        self.prj_details_queue_date_w = \
                self.b.get_object("prj_details_queue_date_w")
        self.prj_list_w = self.b.get_object("prj_list_w")
        self.prj_queue_date_hbox = self.b.get_object("prj_queue_date_hbox")
        self.prj_support_files_w = self.b.get_object("prj_support_files_w")
        self.prj_details_waiting_for_w = \
                self.b.get_object("prj_details_waiting_for_w")
        self.prj_details_waiting_for_since_w = \
                self.b.get_object("prj_details_waiting_for_since_w")
        self.review_project_status_filter_w = \
                self.b.get_object("review_project_status_filter_w")
        self.stuff_tree_w = self.b.get_object("stuff_tree_w")
        self.waiting_for_table = self.b.get_object("waiting_for_table")
        self.workflow_nb = self.b.get_object("workflow_notebook")

        self.clarify_file_details_name_w = self.b.get_object("clarify_file_details_name_w")
        self.clarify_file_details_type_w = self.b.get_object("clarify_file_details_type_w")
        self.clarify_file_details_size_w = self.b.get_object("clarify_file_details_size_w")
        self.clarify_file_details_path_w = self.b.get_object("clarify_file_details_path_w")
        self.clarify_file_details_notes_w = self.b.get_object("clarify_file_details_notes_w")
        self.clarify_file_details_mime_nb_w = self.b.get_object("clarify_file_details_mime_nb_w")
        self.clarify_file_details_icon_w = self.b.get_object("clarify_file_details_icon_w")
        self.clarify_file_info_text_preview_w = self.b.get_object("clarify_file_info_text_preview_w")
        self.clarify_file_info_image_thumbnail_w = self.b.get_object("clarify_file_info_image_thumbnail_w")

    def move_na_position(self, objlist, prj, position):
        nas = objlist.get_selected_rows()
        if len(nas) == 1:
            na = nas[0]
            old_index = objlist.index(na)
            if position == "up":
                if old_index > 0:
                    del(prj.next_actions[old_index])
                    prj.next_actions.insert(old_index - 1, na)
            elif position == "down":
                if old_index + 1 < len(objlist):
                    del(prj.next_actions[old_index])
                    prj.next_actions.insert(old_index + 1, na)
            elif position == "first":
                if old_index > 0:
                    del(prj.next_actions[old_index])
                    prj.next_actions.insert(0, na)
            elif position == "last":
                if old_index + 1 < len(objlist):
                    del(prj.next_actions[old_index])
                    prj.next_actions.append(na)
            self.fill_prj_details_na_list_w(prj)
            self.prj_details_na_list_w.select(na)

    def process_stuff_as_na(self, selected_stuff, stuff_summary=None,
                            stuff_details=None, incubate_=False):
        # FIXME: ugh.  this is so NOT ok.  fix this also.  .... *sigh*
        prj = self.data_lumbergh.prjs['singletons']
        # FIXME: there's no WAY this is the right way to do this - why are we
        # getting kiwi.ValueUnset when the kiwi TextView is empty, instead of
        # an empty string?
        if not isinstance(stuff_details, str):
            stuff_details = None
        self.start_new_na(stuff_summary, prj, stuff_details, incubate=incubate_,
                          stuff=selected_stuff)
        self._inbox_manager.complete_processing(selected_stuff)

    def process_stuff_as_prj(self, stuff, summary=None, details=None,
                             status="active"):
        # FIXME: there's no WAY this is the right way to do this - why are we
        # getting kiwi.ValueUnset when the kiwi TextView is empty, instead of
        # an empty string?
        if isinstance(stuff, inbox_items.InboxStuff):
            self.start_new_prj(summary, status, notes=details,
                               stuff_obj=stuff)
            self._inbox_manager.complete_processing(stuff)

    def queue_project(self, prj):
        qdialog = dialogs.QueueProjectDialog()
        qdate = qdialog.get_datetime()
        # and in case the magic date we got was invalid...
        while not qdialog.valid:
            qdialog = dialogs.QueueProjectDialog(True)
            qdate = qdialog.get_datetime()
        # i.e.: did we hit cancel?
        if qdate:
            self.data_lumbergh.change_project_status(prj, "queued", qdate)
            self.fill_prj_list_w()

    def quit(self):
        # FIXME: when I'm finally using signals (like I should be... *cough*),
        # this will be deprecated
        processed = self._inbox_manager._tree.get_descendants(
                self._inbox_manager._row_processed_stuff)
        self.data_lumbergh.dump_processed_stuff_notes(processed)
        self.data_lumbergh.cleanup_before_exit()
        app_utils.log_line("Exiting normally.", datetime.datetime.now())
        dbus.SessionBus().release_name(defs.DBUS_BUS_NAME)
        gtk.main_quit()

    def remove_file_from_prj(self, prj):
        file_list = self.prj_support_files_w.get_selected_rows()
        label = self.b.get_object("file_name_label")
        title_label = self.b.get_object("delete_file_header_label")
        if len(file_list) == 1:
            file_name = os.path.split(file_list[0].full_path)[1]
            template = self.b.get_object("stupid_file_template_label").get_text()
            label.set_text(template % file_name)
            title_label_text = """<span weight="bold"
                                  size="x-large">Delete this file?</span>"""
        else:
            template = self.b.get_object(
                    "stupid_multiple_files_template_label").get_text()
            label.set_text(template)
            #FIXME: this is waaaaaaaaaaaay too ghetto, even for me.
            title_label_text = """<span weight="bold"
                                   size="x-large">Delete these files?</span>"""
        title_label.set_text(title_label_text)
        title_label.set_use_markup(True)
        d = self.b.get_object("delete_prj_file_dialog")
        d.set_focus(self.b.get_object("cancel_delete_prj_file_w"))
        response = d.run()
        if response == gtk.RESPONSE_OK:
            d.hide()
            for f in file_list:
                self.data_lumbergh.remove_file_from_prj(f.file_name, prj)
            #now re-fill the project's files ObjectList
            self.fill_prj_support_files_w(prj)
        else:
            d.hide()

    def search(self, query):
        self._search_window.search(query)

    def select_clarify_tab(self, widget):
        self.clarify_nb.set_current_page(self.clarify_nb.page_num(widget))

    def set_aof_w_text(self, widget, prj):
        aof_text = self.data_lumbergh.get_prj_aof_names(prj)[0]
        widget.select_item_by_label(aof_text)

    def set_clipboard_text(self, text):
        self.clipboard.set_text(text)
        self.clipboard.store()

    def _set_date_w_values(self, dt, widget):
    # UPDATE: disabling the try/except so I can find out what exceptions
    # actually get thrown, ffs
#        try:
            #this will fail and thus short-circuit if the date is 'None'
        date_text = dt.strftime(defs.GTK_DATE_TEXT_TEMPLATE)
        widget.set_text(date_text)
        # FIXME: more ghetto garbage from me, because I'm tired and slothful
        if "due_date" in gtk.Buildable.get_name(widget):
            self.prj_list_w.get_selected().due_date = dt
        elif "queue_date" in gtk.Buildable.get_name(widget):
            self.prj_list_w.get_selected().queue_date = dt
        elif "waiting_for" in gtk.Buildable.get_name(widget):
            self.prj_list_w.get_selected().waiting_for_since = dt
        widget.date = dt
#        except:
#            widget.date = None

    def set_prj_waiting_for(self, prj, wf_status_text):
        prj.waiting_for_text = wf_status_text

    def _set_valid_date_w(self, widget):
        if widget.get_text() == "":
            widget.date = None
        else:
            # get_magic_date() returns None on failure, so we're safe either way here
            widget.date = self._magical.get_magic_date(widget.get_text())
            # get_magic_date() didn't understand the mystery meat you fed it.
            if widget.date == None:
                widget.set_text(defs.UNRECOGNIZED_DATE_TEXT)
            else:
                self._set_date_w_values(widget.date, widget)

    def show_correct_project_action_buttons(self):
        for widget in self.b.get_object("project_actions_bbox").get_children():
            widget.show()
        status = self.get_prj_review_status_filter()
        if status == "active":
            self.b.get_object("activate_prj_w").hide()
#            self.prj_queue_date_hbox.hide()
            self.waiting_for_table.hide()
        elif status == "incubating":
            self.b.get_object("incubate_prj_w").hide()
#            self.prj_queue_date_hbox.hide()
            self.waiting_for_table.hide()
        elif status == "waiting_for":
            self.b.get_object("prj_waiting_for_w").hide()
            self.waiting_for_table.show()
        elif status == "queued":
            self.b.get_object("queue_prj_w").hide()
#            self.prj_queue_date_hbox.show()
            self.waiting_for_table.hide()
        elif status == "completed":
            self.b.get_object("mark_prj_complete_w").hide()
#            self.prj_queue_date_hbox.hide()
            self.waiting_for_table.hide()

    def start_new_na(self, new_na_summary, prj, na_notes=None, incubate=False,
                     stuff=None):
        if isinstance(stuff, inbox_items.InboxFile):
            new_na_summary = stuff.summary
        nad = dialogs.NewNextActionDialog(self, self.data_lumbergh)
        nad.start_new_na(new_na_summary, prj, na_notes, incubate=incubate,
                         stuff=stuff)
        # jesus this is so not the right place for this.  Fity needs a rewrite.
        # ...
        # ...reeeaaaal bad.
        if prj.summary == 'singletons' and isinstance(stuff,
                                                      inbox_items.InboxFile):
            self.data_lumbergh.copy_to_project_folder(stuff.path, prj)

    def start_new_prj(self, new_prj_name, status=None, notes=None, stuff_obj=None):
        if not status:
            status = self.get_prj_review_status_filter()
        if (self.aof_filter_w.get_selected() != "All" and 
                self.b.get_object("show_review_tab").get_active()):
            aofs = self.aof_filter_w.get_selected()
        else:
            aofs = defs.NO_AOF_ASSIGNED
        project = gee_tee_dee.Project(new_prj_name)
        pd = dialogs.NewProjectDialog(self, self.data_lumbergh)
        exit_hooks = []
        if status == "waiting_for":
            exit_hooks.append('waiting_for')
        elif status == "queued":
            exit_hooks.append('queued')
        pd.open_new_prj_dialog(project, status, aofs, notes, exit_hooks)
        if isinstance(stuff_obj, inbox_items.InboxFile):
            pd.add_files_to_files_list(stuff_obj.path)

    def sync_nas_and_notes(self):
        sorted_nas = self.sort_actions(self.data_lumbergh.get_na_for_each_active_prj())
        task_export.ProtoExporter().export_next_actions(sorted_nas, self.data_lumbergh)

    def temporarily_disable_widget(self, widget):
        if widget.get_property('sensitive'):
            widget.set_sensitive(False)
            # FIXME: horrible, cheap hack to get around the fact that I don't
            # know how to make & use my own signals yet.  *sigh*
        else:
            widget.set_sensitive(True)

    def _open_na_url_or_note(self, treeview, event):
        path = treeview.get_path_at_pos(int(event.x), int(event.y))
        if not path:
            msg = "got bad 'url clicked' event: {0}\nEvent x: {1}\nEvent y: {2}\n"
            msg = msg.format(event, event.x, event.y)
            app_utils.log_line(msg, debug=True)
        else:
            row_num = path[0][0]
            col = path[1]
            obj_list = treeview.get_parent()
            if col.attribute == 'url_icon':
                obj_list.select_paths([row_num])
                url = obj_list.get_selected().url
                if url is not None:
                    _fity_show_uri(url, event.time)
                    
            if col.attribute == 'notes_icon':
                obj_list.select_paths([row_num])
                if obj_list.get_selected().notes is not None:
                    self.edit_extant_na(obj_list.get_selected())

    def _run_daily_tasks(self, run_now=True):
        if run_now:
            self.data_lumbergh.activate_due_queued()
            self._rec_manager.place_recurring_tasks()
            self.data_lumbergh.save_data()
            jesus = managers.BackupJesus()
            jesus.kill_stale_backups()
        # technically "midnight tonight" is really "00:00" tomorrow
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        midnight = time.mktime(tomorrow.timetuple())
        # fudge on the time a little bit; make sure we always run after midnight
        seconds_to_midnight = int(midnight - time.time() + 30)
        # make sure we don't run again after our same interval - instead,
        # just call ourselves again and keep creating new intervals.
        log_msg = ("Running _run_daily_tasks(), and I am under the "
                   "impression believe there are %s seconds to midnight.")
        app_utils.log_line(log_msg % seconds_to_midnight, datetime.datetime.now())
        gobject.timeout_add_seconds(seconds_to_midnight, self._run_daily_tasks)
        return False

    def _type_ahead_combo(self, combo, gdk_keyval):
        ui.type_ahead_combo(combo, gdk_keyval)

#CALLBACKS
    def activate_na_w_clicked_cb(self, widget, data=None):
        nas = self.prj_details_incubating_na_list_w.get_selected_rows()
        if len(nas) > 0:
            prj = self.prj_list_w.get_selected()
            self.data_lumbergh.activate_nas(nas, prj.key_name)
            self.fill_prj_details_na_list_w(prj)

    def activate_prj_w_clicked_cb(self, widget, data=None):
        self.data_lumbergh.change_project_status(self.prj_list_w.get_selected(),
                                                 "active")
        self.fill_prj_list_w()

    def archive_completed_singletons_w_clicked_cb(self, widget, data=None):
        self.data_lumbergh.archive_completed_singletons()
        self.fill_prj_details_na_list_w(self.prj_list_w.get_selected())

    def areas_of_focus_w_changed_cb(self, widget, data=None):
        self.fill_prj_list_w()

    def areas_of_focus_w_key_press_event_cb(self, widget, data=None):
        self._type_ahead_combo(widget, data)

    def can_has_quit_box_grab_focus_cb(self, widget, data=None):
        #FIXME someday..
        # oh dear.  this isn't a good thing.  I forsee a lot of ghetto-tastic
        # action like this in my future though, because I can't seem to set up
        # an accel group in Glade that actually WORKS
        self.quit()

    def clarify_notes_copy_both_w_clicked_cb(self, widget, data=None):
        text = self.clarify_notes_details_summary_w.get_text() + "\n\n" + \
                                    self.clarify_notes_details_details_w.read()
        self.set_clipboard_text(text)

    def clarify_notes_copy_summary_w_clicked_cb(self, widget, data=None):
        self.set_clipboard_text(self.clarify_notes_details_summary_w.get_text())

    def clarify_create_new_na_clicked_cb(self, widget, data=None):
        self.process_stuff_as_na(self.stuff_tree_w.get_selected(),
                                 self.clarify_notes_details_summary_w.get_text(),
                                 self.clarify_notes_details_details_w.read())

    def clarify_create_prj_clicked_cb(self, widget, data=None):
        selected_stuff = self.stuff_tree_w.get_selected()
        details = None
        if isinstance(selected_stuff, inbox_items.InboxNote):
            summary = self.clarify_notes_details_summary_w.get_text()
            maybe = self.clarify_notes_details_details_w.read()
            if maybe != kiwi.ValueUnset:
                details = maybe
        else:
            summary = selected_stuff.summary
        self.process_stuff_as_prj(selected_stuff, summary, details)

    def clarify_file_as_reference_w_clicked_cb(self, widget, data=None):
        stuff = self.stuff_tree_w.get_selected()
        self.file_stuff_as_reference(stuff)

    def clarify_incubate_na_w_clicked_cb(self, widget, data=None):
        self.process_stuff_as_na(self.stuff_tree_w.get_selected(),
                                 self.clarify_notes_details_summary_w.get_text(),
                                 self.clarify_notes_details_details_w.read(),
                                 incubate_=True)

    def clarify_incubation_prj_w_clicked_cb(self, widget, data=None):
        selected_stuff = self.stuff_tree_w.get_selected()
        details = None
        if isinstance(selected_stuff, inbox_items.InboxNote):
            summary = self.clarify_notes_details_summary_w.get_text()
            maybe = self.clarify_notes_details_details_w.read()
            if maybe != kiwi.ValueUnset:
                details = maybe
        else:
            summary = selected_stuff.summary
        self.process_stuff_as_prj(selected_stuff, summary, details,
                                  status="incubating")

    def clarify_queue_project_w_clicked_cb(self, widget, data=None):
        selected_stuff = self.stuff_tree_w.get_selected()
        details = None
        if isinstance(selected_stuff, inbox_items.InboxNote):
            summary = self.clarify_notes_details_summary_w.get_text()
            maybe = self.clarify_notes_details_details_w.read()
            if maybe != kiwi.ValueUnset:
                details = maybe
        else:
            summary = selected_stuff.summary
        self.process_stuff_as_prj(selected_stuff, summary, details,
                                  status="queued")

    def clarify_stuff_details_open_w_clicked_cb(self, widget, data=None):
        _fity_show_uri(self.stuff_tree_w.get_selected().uri)

    def clarify_trash_stuff_w_clicked_cb(self, widget, data=None):
        self._inbox_manager.complete_processing(self.stuff_tree_w.get_selected())

    def clarify_waiting_for_prj_w_clicked_cb(self, widget, data=None):
        selected_stuff = self.stuff_tree_w.get_selected()
        details = None
        if isinstance(selected_stuff, inbox_items.InboxNote):
            summary = self.clarify_notes_details_summary_w.get_text()
            maybe = self.clarify_notes_details_details_w.read()
            if maybe != kiwi.ValueUnset:
                details = maybe
        else:
            summary = selected_stuff.summary
        self.process_stuff_as_prj(selected_stuff, summary, details,
                                  status="waiting_for")

    def edit_na_w_clicked_cb(self, widget, data=None):
        na = self.prj_details_na_list_w.get_selected_rows()[0]
        self.edit_extant_na(na)

    def edit_project_notes_w_clicked_cb(self, widget, data=None):
        prj = self.prj_list_w.get_selected()
        self.display_prj_notes(prj)

    def engage_context_w_changed_cb(self, widget, data=None):
        self.fill_engage_na_list()

    def engage_context_w_key_press_event_cb(self, widget, data=None):
        self._type_ahead_combo(widget, data)

    def engage_energy_level_w_changed_cb(self, widget, data=None):
        self.fill_engage_na_list()

    def engage_energy_level_w_key_press_event_cb(self, widget, data=None):
        self._type_ahead_combo(widget, data)

    def engage_na_list_cell_edited_cb(self, widget, obj=None, attribute=None):
        self.engage_na_list.refresh()

    def engage_na_list_focus_in_event_cb(self, widget, data=None):
        index = widget.index(widget.get_selected())
        # this is a bit absurd, but it's required to get the right behavior... strange.
        widget.select_paths([index])
        gobject.idle_add(widget.grab_focus)

    def engage_na_list_row_activated_cb(self, widget, obj=None):
        self.edit_extant_na(obj)

# FIXME ZOMG FIXME!!
    def engage_sync_w_clicked_cb(self, widget, data=None):
        self.temporarily_disable_widget(widget)
        self.sync_nas_and_notes()
        self.temporarily_disable_widget(widget)

    def engage_time_available_w_changed_cb(self, widget, data=None):
        self.fill_engage_na_list()

    def engage_time_available_w_key_press_event_cb(self, widget, data=None):
        self._type_ahead_combo(widget, data)

    def enter_new_na_w_activate_cb(self, widget, data=None):
        text = widget.get_text() # strange.  if I don't do this, somehow 'widget'
        widget.set_text("")      # gets reassigned after calling start_new_na??
        self.start_new_na(text, self.prj_list_w.get_selected())

    def enter_new_prj_w_activate_cb(self, widget, data=None):
        t = widget.get_text()
        widget.set_text("")
        self.start_new_prj(t)

    def fidy_window_accelgroup_accel_activate_cb(self, window, data1=None,
                                                 data2=None, data3=None):
    #FIXME: just testing.
#        print "\n\n\n\n\n"
#        for d in [data1, data2, data3]: print d
#        print window
#        print "\n\n\n\n\n"
        pass

    def clarify_add_stuff_to_prj_w_clicked_cb(self, widget, data=None):
        stuff = self.stuff_tree_w.get_selected()
        reference_search_box = dialogs.ReferenceAttacherSearchDialog(
                                   self.data_lumbergh, self, stuff)
        reference_search_box.search("")
        self._inbox_manager.complete_processing(stuff)

    def clarify_add_to_read_review_w_clicked_cb(self, widget, data=None):
        stuff = self.stuff_tree_w.get_selected()
        self.data_lumbergh.file_stuff_as_read_review(stuff, defs.READ_REVIEW_PATH)
        self._inbox_manager.complete_processing(stuff)

    def incubate_na_w_clicked_cb(self, widget, data=None):
        nas = self.prj_details_na_list_w.get_selected_rows()
        if len(nas) > 0:
            prj = self.prj_list_w.get_selected()
            self.data_lumbergh.incubate_nas(nas, prj.key_name)
            self.fill_prj_details_na_list_w(prj)

    def incubate_prj_w_clicked_cb(self, widget, data=None):
        self.incubate_project(self.prj_list_w.get_selected())

    def incubate_stuff_clicked_cb(self, widget, data=None):
        self.select_clarify_tab(self.b.get_object("incubation_frame"))

    def main_window_destroy_cb(self, widget, data=None):
        self.quit()

    def mark_prj_complete_w_clicked_cb(self, widget, data=None):
        self.complete_project(self.prj_list_w.get_selected())

    def new_aof_w_clicked_cb(self, widget, data=None):
        self.create_new_aof()

    def open_project_support_folder_w_clicked_cb(self, widget, data=None):
        prj = self.prj_list_w.get_selected()
        _fity_show_uri(self.data_lumbergh.get_project_folder_uri(prj))

    def prj_add_file_w_clicked_cb(self, widget, data=None):
        self.add_file_to_prj(self.prj_list_w.get_selected())

#FIXME: all this shouldn't be in a callback - put into a proper method
    def prj_delete_w_clicked_cb(self, widget, data=None):
        selected_row_num = self.prj_list_w.get_selected_row_number()
        if selected_row_num + 1 == len(self.prj_list_w):
            selected_row_num = selected_row_num - 1
        prj = self.prj_list_w.get_selected()
        label = self.b.get_object("project_name_label")
        template = self.b.get_object("stupid_template_label").get_text()
        label.set_text(template % prj.summary)
        d = self.b.get_object("delete_prj_dialog")
        d.set_focus(self.b.get_object("cancel_delete_prj_w"))
        if d.run() == gtk.RESPONSE_OK:
            d.hide()
            self.delete_prj(prj)
            self.prj_list_w.select_paths([selected_row_num])
            gobject.idle_add(self.prj_list_w.grab_focus)
        else:
            d.hide()

    def prj_details_aofs_w_content_changed_cb(self, widget, data=None):
        prj = self.prj_list_w.get_selected()
        if prj != None:
            # don't try to set anything if the AOF combo was just changed by
            # selecting a new prj, instead of the user clicking the AOF combo
            aof = self.data_lumbergh.get_prj_aof_names(prj)[0]
            if widget.get_selected_label() != aof:
                self.data_lumbergh.set_prj_aofs(prj, widget.get_selected_label())

    def prj_details_na_list_w_cell_edited_cb(self, widget, data=None, wtf=None):
        self.prj_details_na_list_w.refresh()

    def prj_details_na_list_w_key_press_event_cb(self, widget, data=None):
        if gtk.gdk.keyval_name(data.keyval) == "Delete":
            nas = self.prj_details_na_list_w.get_selected_rows()
            if len(nas) == 1:
                self.delete_na(nas[0])

    def prj_details_na_list_w_row_activated_cb(self, widget, obj=None, data=None):
        na = self.prj_details_na_list_w.get_selected_rows()[0]
        self.edit_extant_na(na)

    def prj_details_priority_w_content_changed_cb(self, widget, data=None):
        prj = self.prj_list_w.get_selected()
        prj.priority = ui.translate_priority(widget.get_selected_label())

    def prj_details_priority_w_key_press_event_cb(self, widget, data=None):
        self._type_ahead_combo(widget, data)

    def prj_details_set_waiting_for_cb(self, widget, data=None):
        prj = self.prj_list_w.get_selected()
        self.set_prj_waiting_for(prj, widget.get_text())

    def prj_list_w_focus_in_event_cb(self, widget, data=None):
        index = self.prj_list_w.index(self.prj_list_w.get_selected())
        #this seems sort of absurd, but it's required to get the right behavior...
        self.prj_list_w.select_paths([index])
        gobject.idle_add(self.prj_list_w.grab_focus)

    def prj_list_w_selection_changed_cb(self, widget, data=None):
        if len(self.prj_list_w) > 0:
            self.fill_prj_details(self.prj_list_w.get_selected())

    def prj_remove_file_w_clicked_cb(self, widget, data=None):
        self.remove_file_from_prj(self.prj_list_w.get_selected())

    def prj_support_files_w_key_press_event_cb(self, widget, data=None):
        if gtk.gdk.keyval_name(data.keyval) == "Delete":
            self.remove_file_from_prj(self.prj_list_w.get_selected())

    def prj_support_files_w_row_activated_cb(self, widget, data=None):
        header = "file://"
        selected = widget.get_selected_rows()
        # don't do anything if multiple files are selected
        if len(selected) == 1:
            path = selected[0].full_path
            _fity_show_uri(header + path)

    def prj_waiting_for_w_clicked_cb(self, widget, data=None):
        self.mark_project_as_waiting_for(self.prj_list_w.get_selected())

    def queue_prj_w_clicked_cb(self, widget, data=None):
        self.queue_project(self.prj_list_w.get_selected())

    #FIXME: push to separate method
    def review_filter_clicked_cb(self, widget, data=None):
        self.fill_prj_list_w()
        self.show_correct_project_action_buttons()
        self.prj_list_w.select_paths([0])
        gobject.idle_add(self.prj_list_w.grab_focus)

    def remove_na_w_clicked_cb(self, widget, data=None):
        nas = self.prj_details_na_list_w.get_selected_rows()
        if len(nas) == 1:
            self.delete_na(nas[0])

    def set_prj_date_cb(self, widget, data=None):
        self._set_valid_date_w(widget)

    def show_clarify_tab_toggled_cb(self, widget, data=None):
        self.workflow_nb.set_current_page(0)

    #FIXME: push to separate method
    def show_engage_tab_toggled_cb(self, widget, data=None):
        self.engage_time_available_w.select_item_by_label("60+")
        self.engage_energy_level_w.select_item_by_label("Any")
        self.fill_engage_context_w(self.engage_context_w)
        self.workflow_nb.set_current_page(2)
        gobject.idle_add(self.engage_context_w.grab_focus)

    #FIXME: push to separate method
    def show_review_tab_toggled_cb(self, widget, data=None):
        self.workflow_nb.set_current_page(1)
        #focus the prj list
        gobject.idle_add(self.prj_list_w.grab_focus)

    def stuff_tree_w_key_press_event_cb(self, widget, data=None):
        if gtk.gdk.keyval_name(data.keyval) == "Delete":
            self._inbox_manager.complete_processing(
                    self.stuff_tree_w.get_selected())

    def stuff_tree_w_selection_changed_cb(self, widget, data=None):
        self.fill_stuff_details(widget.get_selected())

    # FIXME: remove when not needed
    def ohnoes_w_clicked_cb(self, widget, data=None):
        self.fill_engage_na_list()

    def achanged_cb(self, widget, data=None):
        self.fill_engage_na_list()

    def hbox10_grab_focus_cb(self, widget, data=None):
        # FIXME: testing (kind of) - fix it for godssakes
        # this is a hack to open URLs in the Engage tab, because I don't yet
        # understand how AccelGroups work. ;-P
        na = self.engage_na_list.get_selected()
        if na.url:
            _fity_show_uri(na.url)

    def clarify_consolidate_inboxes_w_clicked_cb(self, widget, data=None):
        self.consolidate_inboxes(widget)

    def move_na_down_w_clicked_cb(self, widget, data=None):
        prj = self.prj_list_w.get_selected()
        self.move_na_position(self.prj_details_na_list_w, prj, 'down')

    def move_na_first_w_clicked_cb(self, widget, data=None):
        prj = self.prj_list_w.get_selected()
        self.move_na_position(self.prj_details_na_list_w, prj, 'first')

    def move_na_last_w_clicked_cb(self, widget, data=None):
        prj = self.prj_list_w.get_selected()
        self.move_na_position(self.prj_details_na_list_w, prj, 'last')

    def move_na_up_w_clicked_cb(self, widget, data=None):
        prj = self.prj_list_w.get_selected()
        self.move_na_position(self.prj_details_na_list_w, prj, 'up')

    def search_w_activate_cb(self, widget, data=None):
        self.search(widget.get_text())
        widget.set_text("")

    def stuff_tree_w_mnemonic_activate_cb(self, widget, data=None):
        gobject.idle_add(widget.grab_focus)

    def search_w_grab_focus_cb(self, widget, data=None):
        pass

    def na_reset_age_menuitem_activate_cb(self, widget, data=None):
        selected = self.engage_na_list.get_selected()
        selected.creation_date = datetime.datetime.now()

    def engage_na_list_right_click_cb(self, widget, item=None, event=None):
        menu = self.b.get_object('na_context_menu')
        menu.popup(None, None, None, event.button, event.get_time())

    def engage_na_list_click_cb(self, widget, event):
        self._open_na_url_or_note(widget, event)
        return False

    def na_queue_to_cb(self, menu_item):
        self.data_lumbergh.queue_singleton_na(self.engage_na_list.get_selected(),
                                              menu_item.get_label())
        self.fill_engage_na_list()

    def engage_na_list_key_press_event_cb(self, widget, data=None):
        if gtk.gdk.keyval_name(data.keyval) == "Delete":
            na = widget.get_selected()
            self.data_lumbergh.engage_na_deleter(na.uuid)
            self.fill_engage_na_list()

    def delete_na_menuitem_activate_cb(self, widget, data=None):
        na = self.engage_na_list.get_selected()
        # FIXME: Add in a confirmation dialog here?
        self.data_lumbergh.engage_na_deleter(na.uuid)
        self.fill_engage_na_list()

    def add_stuff_w_activate_cb(self, widget, data=None):
        from fluidity import slider
        slider_app = slider.Slider()
        slider_app.window.show()
        slider_app.fill_prj_list_w()
        del(slider_app)

    def _engage_due_today_filter_w_toggled_cb(self, widget, data=None):
        self.fill_engage_na_list()


def _fity_show_uri(uri, time_arg=None):
    if uri.startswith('note:'):
        # HACK: Tomboy has a stupid bug where it won't handle opening notes via URI
        # from the command line if the app's already open
        ProjectNote(uri=uri).show()
    else:
        time_arg = time_arg if time_arg else int(time.time())    
        gtk.show_uri(gtk.gdk.Screen(), uri, time_arg)



def _run():
    g = Fluidity()
    g.window.show()
    gtk.main()

def _run_profiled():
    profile_path = os.path.join(os.path.expanduser('~'), 'profile.out')
    import cProfile
    cProfile.run("_run()", profile_path)
    
def run():
    _run()
#    _run_profiled()


if __name__ == "__main__":
    print("""HEY YOU: Yes, you, the user -- DON'T RUN THIS DIRECTLY!  Use the
launching script 'fluidity' in your system path (e.g.: in /usr/bin/), or if
you're running straight out of the folder from the .tar.gz file you grabbed,
then look for the script in the "bin" folder.

...or you could do the *really* wacky thing and click on the Fluidity item in
your GNOME/KDE menu.  But that's not worth any nerd points, now is it?""")
    run()
