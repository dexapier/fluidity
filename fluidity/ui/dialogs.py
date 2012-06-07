#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""Dialog controller classes for Fluidity."""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


import datetime
import os
import time

import gobject
import gtk
import pango

from kiwi.ui.objectlist import Column

from fluidity import app_utils
from fluidity import defs
from fluidity import gee_tee_dee
from fluidity import inbox_items
from fluidity import ui
from fluidity.magic_machine import MagicMachine
from fluidity.note import ProjectNote


class GeeTeeDeeDialog(object):

    GTK_BUILDER_FILENAME = None

    def __init__(self, caller, datamgr):
        self._builder = gtk.Builder()
        self._builder.add_from_file(os.path.join(defs.APP_DATA_PATH,
                                    self.GTK_BUILDER_FILENAME))
        self._builder.connect_signals(self)
        #set up some instance names & objects
        self._map_fields_to_instance_names()
        self._caller = caller
        self._data_lumbergh = datamgr
        self._magical = MagicMachine(datamgr)

    def _get_priority(self):
        text = self._priority_w.get_selected_label()
        return ui.PRIORITY_LABELS_TO_VALUES[text]

    def _set_date_w_values(self, dt, widget):
        # FIXME: refactor - call it "set_date_w_text" or something, make it apply
        # both to this and queue_to (Goodo.  hehe.)
        try:
            #this will fail and thus short-circuit if the date is 'None'
            date_text = dt.strftime(defs.GTK_DATE_TEXT_TEMPLATE)
            widget.set_text(date_text)
            widget.date = dt
        except:
            widget.date = None

    def _set_valid_date_w(self, widget):
        if widget.get_text() == "":
            widget.date = None
        else:
            # get_magic_date() returns None on failure, so we're safe either way here
            widget.date = self._magical.get_magic_date(widget.get_text())
            if widget.date == None:
                # get_magic_date() didn't understand the mystery meat you fed it.
                widget.set_text(defs.UNRECOGNIZED_DATE_TEXT)
            else:
                #FIXME: hmm... that's kinda... goofy.  review later
                self._set_date_w_values(widget.date, widget)


class NewProjectDialog(GeeTeeDeeDialog):

    GTK_BUILDER_FILENAME = 'new_prj_dialog.ui'

    def __init__(self, caller, datamgr):
        super(NewProjectDialog, self).__init__(caller, datamgr)
        self._note = None

    def add_files_to_files_list(self, file_path=None):
        if file_path is None:
            chooser = gtk.FileChooserDialog(
                              action=gtk.FILE_CHOOSER_ACTION_OPEN,
                              buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                       gtk.STOCK_ADD, gtk.RESPONSE_OK))
            chooser.set_property("select-multiple", True)
            response = chooser.run()
            if response == gtk.RESPONSE_OK:
                for f in chooser.get_filenames():
                    row = ui.ProjectSupportFileRow(f)
                    self._files_list_w.append(row)
            chooser.destroy()
            chooser = None
        else:
            row = ui.ProjectSupportFileRow(file_path)
            self._files_list_w.append(row)
        self._files_list_w.sort_by_attribute("isdir", order=gtk.SORT_ASCENDING)
        self._files_list_w.sort_by_attribute("name_lowercase", order=gtk.SORT_ASCENDING)

    def fill_na_list_w(self, fuck_you):
        self._new_prj_na_list_w.clear()
        for n in self._prj.next_actions:
            self._new_prj_na_list_w.append(n)
        last_item = len(self._new_prj_na_list_w) - 1
        self._new_prj_na_list_w.select_paths([last_item])

    def open_new_prj_dialog(self, prj, status, aofs, prj_notes=None, on_exit=None):
        """Open a new Project dialog.

        Args:
            prj: the new Project instance you want to build up
            status: project status - must be one of: "active"... (bleh)
            .....  finishing this later.
            on_exit: a dict to hold various options when we close the dialog
        """
        self._prj = prj
        self._prj.status = status
        self.on_exit_hooks = on_exit
        #FIXME: this is incongruent with how I start up the NA dialog
        self._init_ui(prj.summary, aofs)
        self._do_magic(prj.summary)
        self._dialog.show()
        if prj_notes:
            self._note = ProjectNote(prj=self._prj, notes_for_new_prj=prj_notes)
            self._note.show()

    def _build_aof_list(self):
        if self._aof_w.get_selected() == defs.NO_AOF_ASSIGNED:
            return []
        else:
            return [app_utils.format_for_dict_key(self._aof_w.get_selected())]

    def _build_due_date(self):
        return self._magical.get_magic_date(self._due_date_w.get_text())

    def _build_file_list(self):
        file_list = []
        # ZOMG I am so in love with Kiwi right now
        for f in self._files_list_w:
            file_list.append(f.full_path)
        return file_list

    def _build_prj(self, prj):
        for a in self._build_aof_list():      # set aofs
            prj.aofs.append(a)
        prj.summary = self._name_w.get_text()
        due = self._build_due_date()          # set due date
        if due:
            prj.due_date = due
        if len(self._prj.next_actions) == 0:  # set next_actions
            self._set_na_list()
        prj.priority = self._get_priority()   # set priority
        qd = self._build_queue_date()         # set queue_date
        if qd:
            prj.queue_date = qd
        if prj.queue_date:                    # set status - **must be set
            prj.status = "queued"             # *after* queue_date, or this
        return prj                            # could be inaccurate!

    def _build_queue_date(self):
        #FIXME: gotta make this actually do something, too...
        #self._queue_date_w.get_text()
        return None

    def _cancel_prj(self):
        self._dialog.hide()
        if self._note:
            self._note.delete()

    def _create_prj(self, prj):
        if self._validate_me_please_i_needs_it():
            prj = self._build_prj(prj)
            prj.file_list = self._build_file_list()
            self._dialog.hide()
            #FIXME: gawd, this is awful.  must fiiiix.
            self._data_lumbergh.prjs[prj.key_name] = prj
            for a in prj.aofs:
                if a != "":
                    #FIXME: surely this can't be what I intended with DataManager ;P
                    self._data_lumbergh.aofs[a]['projects'].append(prj.key_name)
            for f in prj.file_list:
                self._data_lumbergh.copy_to_project_folder(f, prj)
#                if f.full_path.startswith(defs.INBOX_FOLDER):
#                    gio.File(f).trash()
            # handle on_exit hooks
            if self.on_exit_hooks:
                if 'queued' in self.on_exit_hooks:
                    self._caller.queue_project(prj)
                elif 'waiting_for' in self.on_exit_hooks:
                    self._caller.mark_project_as_waiting_for(prj)
            # prj.file_list is intended to be "disposable", soooo...
            del(prj.file_list)
            self._data_lumbergh.save_data()
            self._caller.fill_prj_list_w()
# FIXME: re-enable this at some point... *sigh*
#            selected = self._caller.prj_list_w.index(prj)
#            self._caller.prj_list_w.select_paths([selected])
            # i.e.: are we on the Review tab?
            if self._caller.workflow_nb.get_current_page() == "1":
                gobject.idle_add(self._caller.prj_list_w.grab_focus)

    def _do_magic(self, prj_name):
        #get magic task (i.e.: 'mt')
        mt = self._magical.get_magic_task(prj_name)
        self._name_w.set_text(mt['summary'])
        #FIXME: this is hackish, might break eventually if I don't clean it up
        if 'priority' in mt:
            plabel = ui.PRIORITY_VALUES_TO_LABELS[mt['priority']]
            self._priority_w.select_item_by_label(plabel)
        if 'due_date' in mt:
            dtext = mt['due_date'].strftime(defs.GTK_DATE_TEXT_TEMPLATE)
            self._due_date_w.set_text(dtext)

    def _init_files_list_w(self, obj_list):
        #I have no idea why 23 worked best.
        obj_list.set_columns(
            [Column('icon', width=23, data_type=gtk.gdk.Pixbuf),
             Column('file_name', data_type=str, searchable=True, expand=True),
             Column('full_path', data_type=str, visible=False),
             Column('name_lowercase', data_type=str, visible=False),
             Column('isdir', data_type=bool, visible=False)])
        obj_list.set_headers_visible(False)

    def _init_ui(self, prj_name, aof):
        #set the prj name and the areas of focus
        self._name_w.set_text(prj_name)
        #HACK: oh god...  so, so sad.  One day I'll learn proper OO design.  *sigh*
        self._caller.fill_aofs_w(self._aof_w, self._data_lumbergh.aof_names(), False)
        if aof != "":
            self._aof_w.select_item_by_label(aof)
        self._init_files_list_w(self._files_list_w)
        self._init_new_prj_na_list_w(self._new_prj_na_list_w)
        self._new_prj_na_summary_w.grab_focus()
        self._priority_w.select_item_by_label("Normal")

    def _init_new_prj_na_list_w(self, obj_list):
        obj_list.set_columns([Column('uuid', data_type=str, visible=False),
                              Column('context', data_type=str),
                              Column('formatted_summary', data_type=str,
                                     use_markup=True, searchable=True),
                              Column('due_date', data_type=str)])
        obj_list.set_headers_visible(False)

    def _map_fields_to_instance_names(self):
        self._dialog = self._builder.get_object("new_prj_dialog")
        self._name_w = self._builder.get_object("new_prj_name_w")
        self._new_prj_na_summary_w = self._builder.get_object("new_prj_na_summary_w")
        self._priority_w = self._builder.get_object("new_prj_priority_w")
        self._due_date_w = self._builder.get_object("new_prj_due_date_w")
        self._files_list_w = self._builder.get_object("files_list_w")
        self._aof_w = self._builder.get_object("new_prj_aof_w")
        self._new_prj_na_list_w = self._builder.get_object("new_prj_na_list_w")

    def _set_na_list(self):
        if self._new_prj_na_summary_w.props.text:
            # i.e.: we haven't appended our NA yet
            n = gee_tee_dee.NextAction(self._new_prj_na_summary_w.props.text, 
                                       self._data_lumbergh)
            mt = self._magical.get_magic_task(n.summary)
            for name in mt.keys():
                try:
                    n.__setattr__(name, mt[name])
                except:
                    pass
            # and finally...
            self._prj.next_actions.append(n)

    def _type_ahead_combo(self, combo, gdk_keyval):
        ui.type_ahead_combo(combo, gdk_keyval)

    def _validate_me_please_i_needs_it(self):
        # check that name line isn't blank
        if self._name_w.get_text() == "":
            return False
        # then verify that the due date isn't fucked
        if self._due_date_w.get_text() == defs.UNRECOGNIZED_DATE_TEXT:
            self._due_date_w.grab_focus()
            return False
        #FIXME: add immediate prj queueing here
#        if self._queue_to_w.get_text() == defs.UNRECOGNIZED_DATE_TEXT:
#            self._queue_to_w.grab_focus()
#            return False
        return True

#CALLBACKS
    def files_list_w_key_press_event_cb(self, widget, data=None):
        if gtk.gdk.keyval_name(data.keyval) == "Delete":
            self._files_list_w.remove(self._files_list_w.get_selected())

    def files_list_w_row_activated_cb(self, widget, data=None):
        uri_header = "file://"
        selected = widget.get_selected_rows()
        # don't do anything if multiple files are selected
        if len(selected) == 1:
            path = selected[0].full_path
            gtk.show_uri(gtk.gdk.Screen(), uri_header + path, int(time.time()))

    def new_prj_add_w_clicked_cb(self, widget, data=None):
        widget.grab_focus()
        self._create_prj(self._prj)

    def new_prj_aof_w_content_changed_cb(self, widget, data=None):
        pass

    def new_prj_aof_w_key_press_event_cb(self, widget, data=None):
        self._type_ahead_combo(widget, data)

    def new_prj_cancel_w_clicked_cb(self, widget, data=None):
        self._cancel_prj()

    def new_prj_due_date_w_focus_out_event_cb(self, widget, data=None):
        self._set_valid_date_w(widget)

    def new_prj_files_add_w_clicked_cb(self, widget, data=None):
        self.add_files_to_files_list()

    def new_prj_files_remove_w_clicked_cb(self, widget, data=None):
        for f in self._files_list_w.get_selected_rows():
            self._files_list_w.remove(f)

    def new_prj_na_edit_w_clicked_cb(self, widget, data=None):
        na = self._new_prj_na_list_w.get_selected()
        if na:
            nad = NewNextActionDialog(self, self._data_lumbergh)
            nad.edit_extant_na(na)

    def new_prj_na_remove_w_clicked_cb(self, widget, data=None):
        self._new_prj_na_list_w.remove(self._new_prj_na_list_w.get_selected())

    def new_prj_na_summary_w_activate_cb(self, widget, data=None):
        if self._new_prj_na_summary_w.get_text() != "":
            nad = NewNextActionDialog(self, self._data_lumbergh)
            nad.start_new_na(self._new_prj_na_summary_w.get_text(), self._prj)
            self._new_prj_na_summary_w.set_text("")

    def new_prj_notes_w_clicked_cb(self, widget, data=None):
        # FIXME: shit, what happens when a user changes the name of the project
        # after creating their notes?  I should probably write a "rename prj"
        # method somewhere...
        if not  self._note:
            self._note = ProjectNote(prj=self._prj)
        self._note.show()

    def new_prj_priority_w_key_press_event_cb(self, widget, data=None):
        self._type_ahead_combo(widget, data)


class NewNextActionDialog(GeeTeeDeeDialog):
# FIXME: this whole class is a fucking mess now.  fix it. ...grumble grumble...
# ..stupid asynchronous operations... grumble...grumble... bah!

    GTK_BUILDER_FILENAME = 'new_na_dialog.ui'

    def __init__(self, caller, datamgr):
        super(NewNextActionDialog, self).__init__(caller, datamgr)
        self._init_ui()
        # FIXME: see notes in main app module about the idea that this might be
        # a really stupid thing to do.
        # FIXME: surely there's a better way to do this.  Someone smarter than me
        # can figure it out, I'm sure. ;-P
        self._evil_global_variable_indicating_that_this_is_an_extant_na = False

    def edit_extant_na(self, na):
        """Edit a given NextAction in-place"""
        #just set up the dialog...
        #ZOMG this is so ghettotastic.  Must fix soon.
        label_text = """<span size="x-large"><b>Edit Next Action</b></span>"""
        self._title_label.set_text(label_text)
        self._title_label.set_use_markup(True)
        self._na = na
        self._evil_global_variable_indicating_that_this_is_an_extant_na = True
        #fill in the dialog fields from the given na
        self._populate_fields_from_na(self._na)
        if na.notes:
            self._builder.get_object("notes_expander").set_expanded(True)
        self._focus_first_editing_widget()
        self._dialog.show()

    def start_new_na(self, summary, prj, na_notes=None, status=None,
                     incubate=False, stuff=None):
        self._prj = prj
        self._na = gee_tee_dee.NextAction(summary, self._data_lumbergh)
        self.status = status
        self.incubate_flag = incubate
        self.stuff = stuff
        if na_notes:
            self._na.notes = na_notes
            self._notes_w.get_buffer().props.text = na_notes
            self._builder.get_object("notes_expander").set_expanded(True)
        if self._do_magic(self._na, prj):
            # if this passes,  we have nothing more to do, so we're safe to
            # just quit/do nothing
            prj.next_actions.append(self._na)
            self._caller.fill_na_list_w(prj)
        else:
            if not incubate and \
                (self._prj.summary == "singletons" or self.status == "queued"):
                self._queue_to_w.show()
                self._builder.get_object("queue_to_label").show()
            self._summary_w.set_text(summary)
            if isinstance(self.stuff, inbox_items.InboxFile):
                url = "file://" + os.path.join(defs.SINGLETON_FILES,
                                               self.stuff.summary)
                self._url_w.set_text(url)
            self._dialog.show()
            # And now, we sit in waiting for user input.  We're so lonely!

    def _autocomplete_context(self, widget):
        magic_context = self._magical.get_magic_context(widget.get_text())
        widget.set_text(magic_context)

    def _creates_na_for_realz(self):
        self._finish_editing_na_w.grab_focus()
        if self._validate_me_im_so_insecure():
            self._dialog.hide()
            self._set_na_properties_from_fields(self._na)
            if self._prj.summary == "singletons" and self._na.queue_date:
                print("queue date: ", self._na.queue_date,
                      type(self._na.queue_date))
                self._data_lumbergh.add_queued_singleton(self._na)
            elif self.incubate_flag:
                self._prj.incubating_next_actions.append(self._na)
            else:
                self._prj.next_actions.append(self._na)

    def _do_magic(self, na, prj):
        mt = self._magical.get_magic_task(na.summary)
        has_magic = False
        # if our dict doesn't have these keys, our magic failed, and we
        # should show the dialog instead
        magic_keys = ['context', 'time_est', 'energy_est', 'priority', 'due_date']
        for key in mt.keys():
            if key in magic_keys:
                has_magic = True
        # 'url' was left out of magic_keys before, since it doesn't really qualify
        # an integral part of a NextAction, but now that we've tested, add it back in
        magic_keys.append('url')
        if has_magic:
            for key in mt.keys():
                if key in magic_keys:
                    na.__setattr__(key, mt[key])
            na.summary = mt['summary']
            # and finally...
            return True
        else:
            return False

    def _extant_na_finalize_changes(self):
        self._finish_editing_na_w.grab_focus()
        #called from the "click the OK button" callback
        if self._validate_me_im_so_insecure():
            self._dialog.hide()
            # FIXME: perform magic here - turn the below into an 'if' between
            # using magic and using the fields which have been filled out
            self._set_na_properties_from_fields(self._na)
            #FIXME: and this is just plain /wrong/. Naughty naughty naughty.
            # this is why I have to learn some kind of signal creation techinque
            # OOOOH  OH OH OH , ORRRRRR, I can just pass in a single callback...?
            # pull in one particular method from the caller for the called object
            # to refer back to as a conduit back into that caller.  Is that crack?
            # ....orrrrrrrrrr.....  the data manager is the one that knows this shit
            # and can take care of the "your shit changed, so update it motherfucker"
            # kinds of tasks.
            #
            # Longest.  Comments.  Evar.
            self._caller.fill_na_list_w()

    def _focus_first_editing_widget(self):
        """Worst. Method name. Evar."""
        if self._summary_w.get_text() != "" and self._context_w.get_text() == "":
            self._dialog.set_focus(self._context_w)
        else:
            self._dialog.set_focus(self._summary_w)

    def _get_energy_est(self):
        text = self._energy_est_w.get_selected_label()
        return ui.ENERGY_LABELS_TO_VALUES[text] if text else None

    def _init_ui(self):
        #set up a few defaults...
        self._energy_est_w.select_item_by_label("Normal")
        self._priority_w.select_item_by_label("Normal")
        self._time_est_w.set_value(10)
        # each of these names will refer to the actual datetime.date object for
        # the widget it's attached to.  If the user enters no data, or if that
        # data is unrecognizable by MagicMachine, they'll stay 'None'
        self._queue_to_w.date = None
        self._due_date_w.date = None

    def _map_fields_to_instance_names(self):
        self._dialog = self._builder.get_object("new_na_dialog")
        self._summary_w = self._builder.get_object("summary_w")
        self._context_w = self._builder.get_object("context_w")
        self._time_est_w = self._builder.get_object("time_est_w")
        self._energy_est_w = self._builder.get_object("energy_w")
        self._priority_w = self._builder.get_object("priority_w")
        self._due_date_w = self._builder.get_object("due_date_w")
        self._url_w = self._builder.get_object("url_w")
        self._notes_w = self._builder.get_object("notes_w")
        self._queue_to_w = self._builder.get_object("queue_to_w")
        self._title_label = self._builder.get_object("dialog_title_label")
        self._finish_editing_na_w = self._builder.get_object("finish_editing_na_w")

    def _populate_fields_from_na(self, na):
        self._summary_w.set_text(na.summary)                    # set summary
        if na.context:                                          # set context
            self._context_w.set_text(na.context)
        self._time_est_w.set_value(na.time_est)                 # set time_est
        self._set_energy_est_w(na.energy_est)                   # set energy_est
        self._set_priority_w(na.priority)                       # set priority
        self._set_date_w_values(na.due_date, self._due_date_w)  # set due_date
        if na.url:
            self._url_w.set_text(na.url)                        # set url
        if na.notes:                                            # set notes
            self._notes_w.get_buffer().props.text = na.notes

    def _set_date_w_values(self, dt, widget):
        # FIXME: refactor - call it "set_date_w_text" or something, make it apply
        # both to this and queue_to (Goodo.  hehe.)
        try:
            #this will fail and thus short-circuit if the date is 'None'
            date_text = dt.strftime(defs.GTK_DATE_TEXT_TEMPLATE)
            widget.set_text(date_text)
            widget.date = dt
        except:
            widget.date = None

    def _set_energy_est_w(self, energy):
        etext = ui.ENERGY_VALUES_TO_LABELS[energy]
        self._energy_est_w.select_item_by_label(etext)

    def _set_na_properties_from_fields(self, na):
        na.summary = self._summary_w.get_text()         # set summary
        na.context = self._context_w.get_text()         # set context
        na.time_est = self._time_est_w.get_value()      # set time_est
        #FIXME: need to actually send the appropriate int, not the selected string
        na.energy_est = self._get_energy_est()          # set energy_est
        na.priority = self._get_priority()              # set priority
                                                        # set due_date
        na.due_date = self._due_date_w.date if self._due_date_w.date else None
        na.queue_date = self._queue_to_w.date if self._queue_to_w.date else None
        notes = self._notes_w.get_buffer().props.text  # set notes
        na.notes = notes if notes else None
        na.url = self._url_w.props.text

    def _set_priority_w(self, priority):
        ptext = ui.PRIORITY_VALUES_TO_LABELS[priority]
        self._priority_w.select_item_by_label(ptext)

    def _type_ahead_combo(self, combo, gdk_keyval):
        ui.type_ahead_combo(combo, gdk_keyval)

    def _validate_me_im_so_insecure(self):
        # this is just a final validating pass - the "focus out" event takes care
        # of the real validation, and it covers both interactive use and most of
        # what we would otherwise need to do here.
        #fuck it.  I don't care how unreadable, unmaintainable, or otherwise
        #shameful this is.  i just want it done.
        if self._summary_w.get_text() == "":
            self._summary_w.grab_focus()
            return False
        context = self._context_w.get_text()
        if context != "":
            # i.e.: if we *do* have an @ at the beginning, don't make that the "capitalize" char
            context = context[0] + context[1:].capitalize()
            self._context_w.set_text(context)
        if " " in context or not context.startswith('@'):
            self._context_w.grab_focus()
            return False
        if self._due_date_w.get_text() == defs.UNRECOGNIZED_DATE_TEXT:
            self._due_date_w.grab_focus()
            return False
        if self._queue_to_w.get_text() == defs.UNRECOGNIZED_DATE_TEXT:
            self._queue_to_w.grab_focus()
            return False
        #everything was fine, go ahead.
        return True

# CALLBACKS
    def cancel_w_clicked_cb(self, widget, data=None):
        self._dialog.hide()

    def context_w_focus_out_event_cb(self, widget, data=None):
        self._autocomplete_context(widget)

    def date_w_focus_out_event_cb(self, widget, data=None):
        self._set_valid_date_w(widget)

    def finish_editing_na_w_clicked_cb(self, widget, data=None):
        if self._evil_global_variable_indicating_that_this_is_an_extant_na:
            self._extant_na_finalize_changes()
        else:
            self._creates_na_for_realz()

    # hml, i.e.: "high, medium, low"
    def hml_combo_key_press_event_cb(self, widget, data=None):
        self._type_ahead_combo(widget, data)

    def notes_expander_activate_cb(self, widget, data=None):
        if self._builder.get_object("notes_expander").get_expanded():
            #FIXME: this is bad policy.
            self._summary_w.grab_focus()
        else:
            self._notes_w.grab_focus()

    def url_w_focus_out_event_cb(self, widget, data=None):
        url = widget.get_text()
        if "://" not in url and url != "":
            widget.set_text("http://" + url)

    def url_w_icon_press_cb(self, widget, icon=None, event=None):
        self.url_w_focus_out_event_cb(widget)
        print("URI: " + widget.get_text())
        gtk.show_uri(gtk.gdk.Screen(), widget.get_text(), int(time.time()))


class ReassignProjectCategoryDialog(object):

    GTK_BUILDER_FILENAME = None

    def __init__(self, set_entry_invalid=False):
        self._builder = gtk.Builder()
        self._builder.add_from_file(os.path.join(defs.APP_DATA_PATH,
                                                 self.GTK_BUILDER_FILENAME))
        self._builder.connect_signals(self)
        self._map_fields_to_instance_names()
        self._magical = MagicMachine()
        self._set_calendar_widget_date(self.calendar_w, datetime.date.today())
        self.valid = False

    def _set_calendar_widget_date(self, cal_widget, date_obj):
        for pair in (("year", date_obj.year),
                     ("month", date_obj.month - 1), # stupid fscking calendar widget
                     ("day", date_obj.day)):
            cal_widget.set_property(pair[0], pair[1])

    def _validate_date_entry_w(self, entry):
        self.date_result = self._magical.get_magic_date(entry.get_text())
        if self.date_result:
            self.valid = True
            entry.set_text(self.date_result.strftime(defs.GTK_DATE_TEXT_TEMPLATE))
            self._set_calendar_widget_date(self.calendar_w, self.date_result)
        else:
            self.valid = False
            entry.set_text(defs.UNRECOGNIZED_DATE_TEXT)


class QueueProjectDialog(ReassignProjectCategoryDialog):

    GTK_BUILDER_FILENAME = 'queue_prj_dialog.ui'

    def __init__(self, set_entry_invalid=False):
        super(QueueProjectDialog, self).__init__(set_entry_invalid)

        if set_entry_invalid:
            self.queue_date_entry_w.set_text(defs.UNRECOGNIZED_DATE_TEXT)
        else:
            self.queue_date_entry_w.set_text("")

    def get_datetime(self):
        self.date_result = None
        result = self._dialog.run()
        if result == gtk.RESPONSE_OK:
            self._dialog.hide()
            # causes the text field to validate, and if valid, set the date.  woo.
            # possibly an evil way to do it, but I really care.  I do! I do care!
            # Look how much. ... Look. Look how much I care.
            self._queue_w.grab_focus()
            return self.date_result
        else:
            self._dialog.hide()
            # we hit cancel and thus don't care if the result was valid.
            self.valid = True

    def _map_fields_to_instance_names(self):
        self._dialog = self._builder.get_object("queue_prj_dialog")
        self._queue_w = self._builder.get_object("queue_w")
        self.calendar_w = self._builder.get_object("queue_prj_calendar_w")
        self.queue_date_entry_w = self._builder.get_object("queue_prj_date_entry_w")

# CALLBACKS
    def queue_prj_calendar_w_day_selected_cb(self, widget, data=None):
        self.date_result = _get_date_from_stupid_calendar_widget(widget)
        self.valid = True
        self.queue_date_entry_w.set_text(self.date_result.strftime(
            defs.GTK_DATE_TEXT_TEMPLATE))

    def queue_prj_calendar_w_day_selected_double_click_cb(self, widget, data=None):
        self.date_result = _get_date_from_stupid_calendar_widget(widget)
        self.valid = True
        # and close the dialog
        self._queue_w.activate()

    def queue_prj_date_entry_w_focus_out_event_cb(self, widget, data=None):
        if widget.get_text() != "":
            self._validate_date_entry_w(widget)


class WaitingForDialog(ReassignProjectCategoryDialog):

    GTK_BUILDER_FILENAME = 'waiting_for_dialog.ui'

    def __init__(self, set_entry_invalid=False):
        super(WaitingForDialog, self).__init__(set_entry_invalid)

        if set_entry_invalid:
            self.waiting_for_date_entry_w.set_text(defs.UNRECOGNIZED_DATE_TEXT)
        else:
            self.waiting_for_date_entry_w.set_text("")

    def get_waiting_for_info(self):
        self.date_result = None
        result = self._dialog.run()
        if result == gtk.RESPONSE_OK:
            self._dialog.hide()
            # causes the text field to validate, and if valid, set the date.  woo.
            # possibly an evil way to do it, but like I really care.  I do! I do care!
            # Look how much. ... Look. Look how much I care.
            self.mark_as_waiting_for_w.grab_focus()
            return (self.date_result, self.waiting_for_text_w.get_text())
        else:
            self._dialog.hide()
            # we hit cancel and thus don't care if the result was valid.
            self.valid = True

    def _map_fields_to_instance_names(self):
        self._dialog = self._builder.get_object("waiting_for_dialog")
        self.mark_as_waiting_for_w = self._builder.get_object("mark_as_waiting_for_w")
        self.calendar_w = self._builder.get_object("waiting_for_calendar_w")
        self.waiting_for_date_entry_w = self._builder.get_object("waiting_for_date_entry_w")
        self.waiting_for_text_w = self._builder.get_object("waiting_for_text_w")

# CALLBACKS
    def waiting_for_calendar_w_day_selected_cb(self, widget, data=None):
        self.date_result = _get_date_from_stupid_calendar_widget(widget)
        self.valid = True
        self.waiting_for_date_entry_w.set_text(self.date_result.strftime(
            defs.GTK_DATE_TEXT_TEMPLATE))

    def waiting_for_calendar_w_day_selected_double_click_cb(self, widget, data=None):
        self.date_result = _get_date_from_stupid_calendar_widget(widget)
        if self.waiting_for_text_w.get_text() != "":
            self.valid = True
            # and close the dialog
            self.mark_as_waiting_for_w.activate()

    def waiting_for_date_entry_w_focus_out_event_cb(self, widget, data=None):
        if widget.get_text() != "":
            self._validate_date_entry_w(widget)


class SearchBase(object):
    """Abstract class for search dialog."""
    # FIXME: MAKE THIS AN ACTUAL ABC

    def __init__(self, data_manager, caller):
        self._dm = data_manager
        self._builder = gtk.Builder()
        self._caller = caller

    def search(self, query):
        self._build_new_window()
        self._window.show_all()
        # this triggers the changed event for the gtk.Entry, thus kicking off the search
        self._query_box_w.set_text(query)

    def _arkless_flood(self, widgets): # pylint: disable-msg=W0611
        for i in reversed(range(len(self._ux_widgets))):
            try:
                self._ux_widgets[i].destroy()
                self._ux_widgets[i] = None
            except AttributeError:
                pass

    def _build_new_window(self):
        """I fail at teh GTK."""
        self._builder.add_from_file(os.path.join(defs.APP_DATA_PATH,
                                                 'search_dialog.ui'))
        self._builder.connect_signals(self)
        #set up some instance names & objects
        self._map_fields_to_instance_names()
        self._results_w.set_columns([Column('summary_formatted', data_type=str,
                                            ellipsize=pango.ELLIPSIZE_END,
                                            expand=True, searchable=True,
                                            use_markup=True),
                                     Column('result_type_formatted', data_type=str,
                                            use_markup=True),
                                     Column('prj_key', data_type=str, visible=False),
                                     Column('result_type', data_type=str, visible=False)])
        self._results_w.set_headers_visible(False)
        # pre-emptive optimization?  no idea.  I am a total hack.
        self._ux_widgets = [self._window, self._top_vbox, self._query_box_w,
                            self._include_completed_w, self._results_w,
                            self._include_nas_w]
        self._include_nas_w.props.active = True

    def _fill_results_list(self):
        if len(self._query_box_w.get_text()) > 2:
            self._results_w.clear()
            results = self._search()
            for r in results:
                self._results_w.append(r)
            if len(self._results_w) > 0:
                self._results_w.select_paths([0])
            del(results)

    def _map_fields_to_instance_names(self):
        self._window = self._builder.get_object('search_window_w')
        self._query_box_w = self._builder.get_object('query_box_w')
        self._include_completed_w = self._builder.get_object('include_completed_w')
        self._include_nas_w = self._builder.get_object('include_nas_w')
        self._open_result_w = self._builder.get_object('open_result_w')
        self._results_w = self._builder.get_object('results_w')
        self._top_vbox = self._builder.get_object('top_vbox')

    def _search(self):
        raise NotImplementedError

#CALLBACKS
    def include_completed_w_toggled_cb(self, widget, data=None):
        self._fill_results_list()

    def include_nas_w_toggled_cb(self, widget, data=None):
        self._fill_results_list()

    def open_result_w_clicked_cb(self, widget, data=None):
        raise NotImplementedError

    def query_box_w_changed_cb(self, widget, data=None):
        self._fill_results_list()

    def results_w_mnemonic_activate_cb(self, widget, data=None):
        gobject.idle_add(widget.grab_focus)

    def results_w_row_activated_cb(self, widget, data=None):
        self.open_result_w_clicked_cb(widget, data)

    def search_window_w_activate_default_cb(self, widget, data=None):
        # FIXME: ... I'm not exactly sure why this is here in the first place.
        pass

    def search_window_w_destroy_cb(self, widget, data=None):
        self._arkless_flood(self._ux_widgets)


class JumptoSearchDialog(SearchBase):

    def _jump_to_result(self):
        self._window.hide_all()
        #FIXME: this is stoopid but I'm too brain dead to do it The Right Way
        #right now, and I want it done and over with so I can release 0.1
        selected = self._results_w.get_selected()
        self._caller.jump_to_search_result(selected.prj_key, selected.na_uuid)
        gobject.idle_add(self._arkless_flood, self._ux_widgets)

    def _search(self):
        return self._dm.search(self._query_box_w.get_text(),
                               self._include_completed_w.get_active(),
                               self._include_nas_w.get_active())

#CALLBACKS
    def open_result_w_clicked_cb(self, widget, data=None):
        self._jump_to_result()


class ReferenceAttacherSearchDialog(SearchBase):

    def __init__(self, data_manager, caller, stuff):
        self._stuff = stuff
        super(ReferenceAttacherSearchDialog, self).__init__(data_manager, caller)

    def search(self, query):
        super(ReferenceAttacherSearchDialog, self).search(query)
        self._include_nas_w.hide()
        self._include_nas_w.props.visible = False

    def _attach_to_matching_project(self, match, stuff):
        self._window.hide_all()
        #FIXME: this is stoopid but I'm too brain dead to do it The Right Way
        #right now, and I want it done and over with so I can release 0.1
        self._caller.attach_stuff_to_prj(match.prj_key, stuff)
        gobject.idle_add(self._arkless_flood, self._ux_widgets)

    def _build_new_window(self):
        super(ReferenceAttacherSearchDialog, self)._build_new_window()
        self._open_result_w.set_label("_Attach to Project")

    def _search(self):
        return self._dm.search(self._query_box_w.get_text(),
                               self._include_completed_w.get_active(), False)

#CALLBACKS
    def open_result_w_clicked_cb(self, widget, data=None):
        match = self._results_w.get_selected()
        self._attach_to_matching_project(match, self._stuff)


def _get_date_from_stupid_calendar_widget(cal_widget):
    raw = cal_widget.get_date()
    #FIXME: ewwwwwww.  do this The Right Way (if there's a better one...)
    ts = time.mktime((raw[0], raw[1] + 1, raw[2], 0, 0, 0, 0, 0, 0))
    return datetime.date.fromtimestamp(ts)
