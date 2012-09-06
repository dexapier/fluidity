#-*- coding:utf-8 -*-
#
# Copyright (C) 2012 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
#pylint: disable-msg=W0201
"""Collection of "manager" classes, which handle various aspects of Fluidity."""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


try:
    import cPickle as pickle
except ImportError:
    import pickle
import datetime
import glob
import operator
import os
import shutil
import time

import gio
import gobject
import pango
import yaml

from kiwi.ui.objectlist import Column
from xdg import BaseDirectory

from fluidity import defs
from fluidity import gee_tee_dee
from fluidity import inbox_items
from fluidity import magic_machine
from fluidity import app_utils
from fluidity.first_time import FirstTimeBot
from fluidity.note import ProjectNote


class DataManager(object):

    def __init__(self):
        self.pickle_path = defs.USER_DATA_MAIN_FILE
        #first, make sure we have our data file - if not, invoke FirstTimeBot
        if (not os.path.exists(self.pickle_path) or
            not os.path.exists(defs.NOTE_SLIDER_FOLDER)):
            bot = FirstTimeBot()
            bot.create_initial_files_and_paths()
            del(bot)  # Thank you for your service, bot.  Rest in peace.
        try:
            with open(self.pickle_path, 'r') as pfile:
                self.top_data = pickle.load(pfile)
        except EOFError:
            # probably the main app in the middle of saving its file.
            # Wait a couple seconds, then try again.
            time.sleep(2)
            # If it _still_ fails, something is really screwed - not
            # accommodating this, at least not yet.
            with open(self.pickle_path, 'r') as pfile:
                self.top_data = pickle.load(pfile)
        self.aofs = self.top_data['areas_of_focus']
        self.prjs = self.top_data['projects']
        self.single_notes = self.top_data['single_notes']
        self.queued_singletons = self.top_data['queued_singletons']

        self._file_toady = FileSystemManager()
        self._magic_maker = magic_machine.MagicMachine()
        self.rebuild_aof_cache()

# PUBLIC METHODS
    def activate_due_queued(self):
        app_utils.log_line("Running activate_due_queued()", datetime.datetime.now())
        for p in self.prjs:
            prj = self.prjs[p]
            if prj.status == "queued":
                # FIXME: if the status is queued, we should /always/ have a
                # queue date.  What's the fallback?
                if prj.queue_date:
                    if datetime.date.today() >= prj.queue_date:
                        self.change_project_status(prj, "active")
        for na in self.queued_singletons:
            if na.queue_date <= datetime.date.today():
                self.prjs['singletons'].next_actions.append(na)
                self.queued_singletons.remove(na)

    def activate_nas(self, nas, prj_key):
        """Move the given NextActions to the Project's next_actions list"""
        project = self.prjs[prj_key]
        self.__move_na(nas, project.next_actions, 
                       (project.unordered_next_actions, 
                        project.incubating_next_actions))

    def add_na_to_prj(self, na, prj_key):
        self.prjs[prj_key].next_actions.append(na)

    def add_queued_singleton(self, na):
        self.queued_singletons.append(na)
        self.save_data()

    def aof_names(self):
        return [self.aofs[k]['name'] for k in self.aofs.keys()]

    def archive_completed_singletons(self):
        #FIXME: total crap.  fix later.

        # the .format("") below is on purpose - look at the path for
        # defs.USER_DATA_PATH in your filesystem, it'll make more sense.
        pkl_path = os.path.join(defs.USER_DATA_PATH,
                                defs.ARCHIVED_SINGLETONS_FNAME.format(""))
        try:
            with open(pkl_path, 'r') as pkl_read:
                nas_to_archive = pickle.load(pkl_read)
            now = datetime.datetime.now().strftime(
                          defs.ARCHIVED_SINGLETONS_TIME_TMPLT)
            # back up the old data file, just in case...
            backup_file_name = defs.ARCHIVED_SINGLETONS_FNAME.format(now)
            shutil.copy2(pkl_path, os.path.join(defs.BACKUPS_PATH, backup_file_name))
        except IOError:
            nas_to_archive = []

        singletons = self.prjs['singletons'].next_actions
        for na in singletons:
            if na.complete:
                nas_to_archive.append(na)
        for na in nas_to_archive:
            if na in singletons:
                singletons.remove(na)

        with open(pkl_path, 'wb') as pkl_write:
            pickle.dump(nas_to_archive, pkl_write, pickle.HIGHEST_PROTOCOL)
        self.save_data()

    def autosave(self):
        # FIXME: ZOMG this is so ghetto-tastic.  fix it.  srsly.
        self.save_data()
        return True

    def change_project_status(self, prj, new_status, queue_date=None):
        self._file_toady.move_project_folder(prj.summary, prj.status, new_status)
        prj_ = prj
        note = ProjectNote(prj=prj_)
        note.change_prj_status(new_status)
        if new_status == "queued":
            prj.queue_date = queue_date
        prj.status = new_status
        self.save_data()

    def cleanup_before_exit(self):
        self.save_data()

    def copy_to_project_folder(self, file_name, prj):
        self._file_toady.copy_to_project_folder(file_name, prj.summary, prj.status)

    def create_new_aof(self, new_name):
        key_name = app_utils.format_for_dict_key(new_name)
        self.aofs[key_name] = {'name': new_name, 'projects': []}
        self.rebuild_aof_cache()
        self.save_data()
        return self.aofs

    def delete_na(self, na, prj):
        prj.next_actions.remove(na)
        self.save_data()

    def delete_prj(self, prj):
        app_utils.log_line("Deleting project: " + str(prj), datetime.datetime.now())
        # trash the folders first
        self._file_toady.trash_project_folder(prj.summary, prj.status)
        # then ditch the project notes
        prj_ = prj
        ProjectNote(prj=prj_).delete()
        #this is /almost certainly/ The Hard Way...
        for a in self.aofs.keys():
            matches = []
            # Welcome to my entry in the "Obfuscated Python" contest!
            for p in xrange(len(self.aofs[a]['projects'])):
                if self.aofs[a]['projects'][p] == prj.key_name:
                    matches.append({'aof': a, 'p_index': p})
            for i in matches:
                del(self.aofs[i['aof']]['projects'][i['p_index']])
        del(self.prjs[prj.key_name])
        self.save_data()

    def delete_stuff_note(self, note_obj):
        DUHLETED = False
        i = 0
        while not DUHLETED and i < len(self.single_notes):
            if self.single_notes[i]['summary'] == note_obj.summary:
                del(self.single_notes[i])
                DUHLETED = True
            i += 1

    def dump_processed_stuff_notes(self, stuff_list):
        # cull out the InboxFile items - unneeded.
        real_list = []
        for stuff in stuff_list:
            if not isinstance(stuff, inbox_items.InboxFile):
                real_list.append(stuff)
        processed_path = \
                os.path.join(defs.USER_DATA_PATH,
                             defs.PROCESSED_STUFF_FILE_NAME + str(time.time()))
        with open(processed_path, 'wb') as pfile:
            pickle.dump(real_list, pfile, pickle.HIGHEST_PROTOCOL)
        gf = gio.File(processed_path)
        gf.trash()

    def file_stuff_as_read_review(self, stuff, rr_path):
        stuff_path = os.path.split(stuff.path)[1]
        shutil.move(stuff.path, os.path.join(rr_path, stuff_path))

    def get_contexts(self):
        contexts = []
        for pk in self.prjs.keys():
            p = self.prjs[pk]
            if p.status == "active":
                for na in p.next_actions:
                    if na.context != "" and na.context != None:
                        if not na.context in contexts:
                            contexts.append(na.context)
        contexts.sort()
        return contexts

    def get_file_list_for_prj(self, prj):
        return self._file_toady.get_file_list_for_prj(prj.summary, prj.status)

    def get_inbox_files(self):
        hiddens = os.path.join(defs.INBOX_FOLDER, ".hidden")
        if os.path.exists(hiddens):
            with open(hiddens, 'r') as dot_hidden:
                hidden = dot_hidden.read()
        else:
            hidden = ""
        hidden += "\n".join(defs.IGNORED_INBOX_PATHS)
        for file_ in os.listdir(defs.INBOX_FOLDER):
            if file_ not in hidden and not file_.startswith('.'):
                yield inbox_items.InboxFile(os.path.join(defs.INBOX_FOLDER,
                                                         file_))

    def get_inbox_notes(self):
        return self.single_notes

    def get_na_for_each_active_prj(self):
        active_nas = []
        for p in self.prjs.keys():
            prj = self.prjs[p]
            if prj.status == "active" and prj.summary != 'singletons':
                for na in prj.next_actions:
                    if not na.complete:
                        active_nas.append(na)
                        break
        for na in self.prjs['singletons'].next_actions:
            if not na.complete:
                active_nas.append(na)
        return active_nas

    def get_nas_for_prj(self, prj_key):
        try:
            return self.prjs[prj_key].next_actions
        except AttributeError:
            return []

    def get_prj_aof_names(self, prj):
        aof_list = []
        if len(prj.aofs) == 0:
            aof_list.append(defs.NO_AOF_ASSIGNED)
        else:
            for a in prj.aofs:
                aof_list.append(self.aofs[a]['name'])
        return sorted(aof_list)

    def get_prjs_by_aof(self, area, review_filter):
        prj_list = []
        # "incomplete" is just used by Slider, so far"
        if review_filter == "incomplete":
            for p in sorted(self.prjs.keys()):
                prj = self.prjs[p]
                if prj.status != "completed":
                    prj_list.append(prj)
        else:
            if area == "All":                
                prj_list.extend([prj for prj in self.prjs.values() if prj.status == review_filter])
            elif area == defs.NO_AOF_ASSIGNED:
                for p in sorted(self.prjs.keys()):
                    prj = self.prjs[p]
                    if prj.status == review_filter and len(prj.aofs) == 0:
                        prj_list.append(prj)
            else:
                area_key = app_utils.format_for_dict_key(area)
                if self.aofs[area_key]['projects']:
                    prj_keys = self.aofs[area_key]['projects']
                    prj_list.extend([prj for prj in self.prjs.values() 
                                     if prj.status == review_filter and prj.key_name in prj_keys])
        return sorted(prj_list, key=operator.attrgetter('summary'))

    def get_project_folder_uri(self, prj):
        return self._file_toady.get_project_folder_uri(prj.summary, prj.status)

    def incubate_nas(self, nas, prj_key):
        """Move the given NextActions to the Project's incubating_next_actions."""
        project = self.prjs[prj_key]
        self.__move_na(nas, project.incubating_next_actions, 
                       (project.next_actions, project.unordered_next_actions))

    def move_nas_to_ordered_actions(self, nas, prj_key):
        project = self.prjs[prj_key]
        self.__move_na(nas, project.ordered_next_actions, 
                       (project.unordered_next_actions, project.incubating_next_actions))

    def move_nas_to_unordered_actions(self, nas, prj_key):
        project = self.prjs[prj_key]
        self.__move_na(nas, project.unordered_next_actions, 
                       (project.next_actions, project.incubating_next_actions))

    def __move_na(self, nas, add_to, remove_from):
        for na in nas:
            add_to.append(na)
            for na_list in remove_from:
                try:
                    na_list.remove(na)
                except ValueError:
                    # HACK to work around the fact that we don't know which
                    # list it's coming _from_.
                    pass

    def queue_singleton_na(self, na, queue_date_str):
        try:
            self.prjs['singletons'].next_actions.remove(na)
            na.queue_date = self._magic_maker.get_magic_date(queue_date_str)
            self.add_queued_singleton(na)
        except ValueError:
            # don't freak out if someone tries queuing a NA that isn't in singletons
            pass

    def rebuild_aof_cache(self):
        for aof in self.aofs:
            del(self.aofs[aof]['projects'][:])
        for prj in self.prjs.keys():
            for aof_key in self.prjs[prj].aofs:
                if prj not in self.aofs[aof_key]['projects']:
                    self.aofs[aof_key]['projects'].append(prj)

    def remove_file_from_prj(self, file_name, prj):
        self._file_toady.remove_from_project_folder(file_name, prj.summary,
                                                    prj.status)

    def reparent_project(self, prj, new_parent):
        """Make `new_parent` the parent object of `prj`."""
        new_parent.subprojects.append(prj.uuid)
        prj.parent_project = new_parent.uuid

    def save_data(self):
#        utils.log_line("Saving main data file.", datetime.datetime.now())
        backup_path = os.path.join(defs.BACKUPS_PATH,
                                   defs.USER_DATA_MAIN_FNAME + str(time.time()))
        shutil.copy(self.pickle_path, backup_path)
        with open(self.pickle_path, 'wb') as pfile:
            pickle.dump(self.top_data, pfile, pickle.HIGHEST_PROTOCOL)
        return True

    def search(self, query, include_completed=False, include_nas=False):
        query = query.lower()
        formatter = lambda x: "<b>{0}</b>".format(x) # pylint: disable-msg=W0108
        results = []
        for prj in self.prjs.values():
            if include_nas and (include_completed or prj.status != 'completed'):
                for na in prj.next_actions:
                    score = magic_machine.score(na.summary, query)
                    if score > 0.4:
                        # fuck me, this is ugly: "flat is better than nested."
                        summary_formatted = magic_machine.format_common_substrings(
                                na.summary, query, format_match=formatter)
                        results.append(
                                SearchResult(na.summary, summary_formatted,
                                             prj.key_name, score, na.uuid))
            if include_completed:
                score = magic_machine.score(prj.summary, query)
                if score > 0.4:
                    formatted = magic_machine.format_common_substrings(
                                        prj.summary, query, format_match=formatter)
                    results.append(SearchResult(prj.summary, formatted,
                                                prj.key_name, score))
            else:
                if prj.status != 'completed':
                    score = magic_machine.score(prj.summary, query)
                    if score > 0.4:
                        formatted = magic_machine.format_common_substrings(
                                            prj.summary, query,
                                            format_match=formatter)
                        results.append(SearchResult(prj.summary, formatted,
                                                    prj.key_name, score))
        results.sort(key=operator.attrgetter('score'), reverse=True)
        return results

    def set_prj_aofs(self, prj, aof_text):
        if aof_text == defs.NO_AOF_ASSIGNED:
            del(prj.aofs[:])
        else:
            for aof in self._parse_aof_text(aof_text):
                del(prj.aofs[:])
                if prj.key_name not in self.aofs[aof]['projects']:
                    self.aofs[aof]['projects'].append(prj.key_name)
                prj.aofs.append(aof)
        self.save_data()
        return self.get_prj_aof_names(prj)

    def add_slider_items(self, na_list, note_list, queued_list):
        self._take_these_fucking_nas(na_list)
        self._take_these_fucking_notes(note_list)
        self._take_these_fucking_queues(queued_list)
        #Confirm that we made it to the step of saving
        return self.save_data()

    def _take_these_fucking_nas(self, na_list):
        na_objs = [self._ploader(na_file) for na_file in na_list]
        for na in na_objs:
            self.prjs[na['prj_key']].next_actions.append(na['na_obj'])

    def _take_these_fucking_notes(self, note_list):
        note_objs = []
        for note in note_list:
            note_objs.append(self._ploader(note))
        for notey in note_objs:
            self.single_notes.append(notey)

    def _take_these_fucking_queues(self, queued_list):
        q_objs = []
        for q_file in queued_list:
            q_objs.append(self._ploader(q_file))
        for obj in q_objs:
            self.queued_singletons.append(obj['na_obj'])
        self.activate_due_queued()

    def _parse_aof_text(self, atext):
        if atext == '':
            return [app_utils.format_for_dict_key(defs.NO_AOF_ASSIGNED)]
        else:
            return [app_utils.format_for_dict_key(atext)]

    def _ploader(self, pfile_path):
        with open(pfile_path, 'r') as pfile:
            pcontent = pickle.load(pfile)
        return pcontent

# PROPERTIES
    def engage_na_deleter(self, uuid):
        """Find the NA with the UID of uid arg, and delete it."""
        for prj in self.prjs.values():
            # only look at active projects, since this is for Engage
            if prj.status == "active":
                for na in prj.next_actions:
                    if na.uuid == uuid:
                        prj.next_actions.remove(na)
                        return True
        # uh-oh.  we REALLY shouldn't have gotten here.
        # FIXME: this ought to throw an exception, really
        return False


class FileSystemManager(object):
    """Filesystem manager for Fluidity"""

    def __init__(self):
        pass

    def copy_to_project_folder(self, fname, prj_summary, prj_status):
        full_path = self._get_path_for_type(prj_status) + \
                    self._sanitize_path(prj_summary)
        # Does the project folder exist yet?  If not, create it.  If that fails,
        # return False right away.
        if not os.path.exists(full_path):
            # try creating the right folder.  if it fails, return False
            if not self._create_project_folder(full_path):
                return False
        if fname.startswith('/'):
            base_name = os.path.split(fname)[1]
        else:
            base_name = fname
        # We got this far; now we can try the copy or move operation - which
        # path will need to depend on if fname is a folder or not
        if os.path.isdir(fname):
            if fname.startswith(defs.INBOX_FOLDER):
                shutil.move(fname, os.path.join(full_path, base_name))
            else:
                shutil.copytree(fname, os.path.join(full_path, base_name))
        else:
            if fname.startswith(defs.INBOX_FOLDER):
                # more Evil(TM)...  to be fixed with the signals rewrite
                try:
                    shutil.move(fname, os.path.join(full_path, base_name))
                except IOError:
                    # this might have "completed processing" already,
                    # so maybe it's in the trash...
                    base_name = os.path.split(fname)[1]
                    trash_path = BaseDirectory.xdg_data_home + "/Trash/files"
                    fname = os.path.join(trash_path, base_name)
                    shutil.move(fname, os.path.join(full_path, base_name))
            else:
                shutil.copy(fname, os.path.join(full_path, base_name))
        return True

    def move_project_folder(self, prj_summary, old_status, new_status):
        sanitized_summary = self._sanitize_path(prj_summary)
        full_path = self._get_path_for_type(old_status) + sanitized_summary
        new_path = self._get_path_for_type(new_status) + sanitized_summary
        if os.path.exists(full_path):
            if full_path != new_path:
                shutil.move(full_path, new_path)

    def remove_from_project_folder(self, fname, prj_summary, prj_status):
        full_path = os.path.join(self._get_path_for_type(prj_status),
                                 self._sanitize_path(prj_summary), fname)
        gf = gio.File(full_path)
        gf.trash()
        gf = None
        del(gf)

    def get_project_folder_uri(self, prj_summary, prj_status, create=True):
        # this method assumes that if you're asking for the URI, you must want
        # there to be a prj folder, so if there isn't one yet, just make one.
        # However, if you don't want that, just set 'create' to False
        full_path = self._get_path_for_type(prj_status) + \
                    self._sanitize_path(prj_summary)
        if create:
            if not os.path.exists(full_path):
                # try creating the right folder.  if it fails, return False
                if not self._create_project_folder(full_path):
                    return ""
        uri = "file://" + full_path
        return uri

    def get_file_list_for_prj(self, prj_summary, prj_status):
        path = self.get_project_folder_uri(prj_summary, prj_status, create=False)
        path = path.replace("file://", '')
        path += os.sep
        if os.path.exists(path):
            return [path + f for f in os.listdir(path)]
        else:
            return []

    def trash_project_folder(self, prj_summary, prj_status):
        full_path = self._get_path_for_type(prj_status) + \
                    self._sanitize_path(prj_summary)
        if os.path.exists(full_path):
            gf = gio.File(full_path)
            gf.trash()
            gf = None
            del(gf)

    def _create_project_folder(self, path):
        os.mkdir(path)
        if os.path.exists(path):
            return True
        else:
            return False

    def _sanitize_path(self, fname):
        # I might want to extend this behavior later, which is why I made a custom
        # method instead of just doing the raw replacement below each time
        return fname.replace('/', '-')

    def _get_path_for_type(self, prj_status):
        if prj_status == "active":
            return defs.ACTIVE_FOLDER + os.sep
        elif prj_status == "queued":
            return defs.QUEUED_FOLDER + os.sep
        elif prj_status == "waiting_for":
            return defs.WAITING_FOR_FOLDER + os.sep
        elif prj_status == 'incubating':
            return defs.INCUBATING_FOLDER + os.sep
        elif prj_status == 'completed':
            return defs.COMPLETED_FOLDER + os.sep


class InboxManager(object):
    # CHOCK FULL OF PROFANITY!   I'm a juvenile, easily frustrated asshole.
    # Get used to it.

    def __init__(self, caller, obj_tree, fucdkingdatamanager):
        # I also write shitty code, get used to that, too.
        self._caller = caller
        self._tree = obj_tree
        self._fsm = FileSystemManager()
        self.dm = fucdkingdatamanager
        col = [Column('summary', data_type=str, searchable=True, 
                      ellipsize=pango.ELLIPSIZE_END, expand=True),]
        self._tree.set_columns(col)
        self._fill_rows()
        self._tree.set_headers_visible(False)
        # automagically import new Slider items
        inbox_monitor = gio.File(defs.NOTE_SLIDER_FOLDER).monitor_directory()
        inbox_monitor.connect('changed', self.process_slider_inbox_changes)

    def _fill_rows(self):
        # FIXME: fix this FFS, use some actual polymorphism
        #FIXME: reenable these later
        self._row_inbox_folder = CategoryRow("Inbox Folder")
#        self._row_email_inbox = CategoryRow("Emails")
        # i.e.: Tomboy, e-d-s inbox "tasks", & collected items from Slider
        self._row_single_notes = CategoryRow("Single notes")
        self._row_processed_stuff = CategoryRow("Processed Stuff")
        #FIXME: and re-enable these , too.
        self._tree.append(None, self._row_inbox_folder)
#        self._tree.append(None, self._row_email_inbox)
        self._tree.append(None, self._row_single_notes)
        self._tree.append(None, self._row_processed_stuff)

    def add_actual_shit_to_columns(self):
        notes = self.dm.get_inbox_notes()
        notes.sort(key=operator.itemgetter('summary'))
        # FIXME: this clears everything in "Processed Stuff", and it probably
        # shouldn't - that should live in its own method.
        self._tree.clear()
        self._fill_rows()
        for note in notes:
            self._tree.append(self._row_single_notes,
                inbox_items.InboxNote(note['summary'], note['details']))
        for file_ in sorted(self.dm.get_inbox_files(),
                            key=operator.attrgetter('summary')):
            self._tree.append(self._row_inbox_folder, file_)

#    def add_inbox_files_to_clarify(self):
#        note, file_, files = None, None, None
#        for file_ in files:
#            self._tree.append(self._row_single_notes,
#                inbox_items.InboxNote(note['summary'], note['details']))

    def complete_processing(self, obj):
        #FIXME: wtf is this doing in here?  this is GUI shit!
        if isinstance(obj, inbox_items.InboxStuff):
            selected_row = self._tree.get_selected_row_number()
            self._tree.remove(obj)
            self._tree.append(self._row_processed_stuff, obj)
            if isinstance(obj, inbox_items.InboxNote):
                self.dm.delete_stuff_note(obj)
            elif isinstance(obj, inbox_items.InboxFile):
                try:
                    obj.trash()
                except gio.Error as error:
                    msg = ("Can't trash file (called from InboxManager."
                           "complete_processing): {0} -- error: {1}")
                    app_utils.log_line(msg.format(obj.summary, error))
            self._tree.refresh()
            self._tree.select_paths((selected_row, 0))
            gobject.idle_add(self._tree.grab_focus)

    def gather_slider_items(self):
        na_list = []
        note_list = []
        queued_list = []
        filenames = [os.path.join(defs.NOTE_SLIDER_FOLDER, f) 
                     for f in os.listdir(defs.NOTE_SLIDER_FOLDER) 
                     if f.endswith('.pkl')]
        for n in filenames:
            if n.endswith('-note.pkl'):
                note_list.append(n)
            elif n.endswith('-na.pkl'):
                na_list.append(n)
            elif n.endswith("-queued_na.pkl"):
                queued_list.append(n)
        # only delete the actual files if we got confirmation that
        # the data from them was saved successfully
        if self.dm.add_slider_items(na_list, note_list, queued_list):
            for f in note_list + na_list + queued_list:
                gio.File(f).trash()

    def process_slider_inbox_changes(self, gfile_mon, gfile, other_file, event): # IGNORE:W0613
        if event.value_nick == 'changes-done-hint':
            self.gather_slider_items()
            self.add_actual_shit_to_columns()


class RecurrenceManager(object):

    def __init__(self, dm):
        self._data_lumbergh = dm

    def place_recurring_tasks(self):
        app_utils.log_line("Running place_recurring_tasks()", datetime.datetime.now())        
        self._load_data(defs.RECURRENCE_DATA)
        data = self._recur_data
        today = datetime.date.today()
        if self._recur_data['last_run'] < today:
            self._place_daily_tasks(today, data)
            self._place_monthly_tasks(today, data)
            self._place_weekly_tasks(today, data)
            self._recur_data['last_run'] = today
            self._save_data(defs.RECURRENCE_DATA)

    def _create_na(self, task):
        na = gee_tee_dee.NextAction(task['summary'])
        na_attrs = ('priority', 'context', 'notes', 'url', 'time_est',
                    'energy_est')
        for attr in na_attrs:
            if attr in task:
                na.__setattr__(attr, task[attr])
        if 'due_date' in task:
            na.due_date = datetime.date.today() + \
                          datetime.timedelta(task['due_date'])
        return na

#  everyXDays: 1 # integer
#- summary: # the task's description in e-d-s
#  priority:  # "gnite syntax": ! and + are high, - is low, blank is normal
#  context:  # String, enclosed in quotes
#  notes:  # probably ought to be a block I guess.  until then, string.
#  url: # url, enclosed in quotes
#  due_date: # integer - X days after placement

    def _load_data(self, data_file_path):
        self._recur_data = None
        self._recur_data = self._yloader(data_file_path)
        # FIXME: datamanager is a fucking mess.  clean it up.
        self._singleton_nas = self._data_lumbergh.get_nas_for_prj('singletons')

    def _place_daily_tasks(self, today, data):
        for t in data['daily']:
            if 'last_seen' not in t:
                na = self._create_na(t)
                self._data_lumbergh.add_na_to_prj(na, 'singletons')
                t['last_seen'] = today
            else:
                delta = datetime.timedelta(t['everyXDays'])
                found = False
                index = 0
                while found == False and index < len(self._singleton_nas):
                    if self._singleton_nas[index].summary == t['summary']:
                        if not self._singleton_nas[index].complete:
                            found = True
                            t['last_seen'] = today
                    index += 1
                if found == False and today >= t['last_seen'] + delta:
                    na = self._create_na(t)
                    self._data_lumbergh.add_na_to_prj(na, 'singletons')
                    t['last_seen'] = today

    def _place_monthly_tasks(self, today, data):
        last = data['last_run']
        for t in data['monthly']:
            for day in t['days']:
                # FIXME: make more generic wrt weekly tasks, too.
                task_date = datetime.date(today.year, today.month, day)
                if last < task_date <= today:
                    found = False
                    index = 0
                    while found == False and index < len(self._singleton_nas):
                        if self._singleton_nas[index].summary == t['summary']:
                            if not self._singleton_nas[index].complete:
                                found = True
                        index += 1
                    if found == False:
                        na = self._create_na(t)
                        self._data_lumbergh.add_na_to_prj(na, 'singletons')

    def _place_weekly_tasks(self, today, data):
        for t in data['weekly']:
            for day in t['weekdays']:
                # FIXME: make more generic wrt weekly tasks, too.
                if day == today.weekday():
                # FIXME: bah, I suck.  make this work properly when we haven't run
                # on a given day, make it run everything since the last time we ran.
                # the following should help I guess...
                # (today + datetime.timedelta(7 - (today - last_day).days)).weekday()
                    found = False
                    index = 0
                    while found == False and index < len(self._singleton_nas):
                        if self._singleton_nas[index].summary == t['summary']:
                            if not self._singleton_nas[index].complete:
                                found = True
                        index += 1
                    if found == False:
                        na = self._create_na(t)
                        self._data_lumbergh.add_na_to_prj(na, 'singletons')

    def _save_data(self, data_file_path):
        #FIXME: create a backup copy?
        with open(data_file_path, 'w') as yfile:
            print("Saving recurrence data")
            yaml.dump(self._recur_data, yfile, Dumper=yaml.CDumper,
                      default_flow_style=False)

    def _yloader(self, yfile_path):
        with open(yfile_path, 'r') as yfile:
            print("calling yaml.load()")
            ycontent = yaml.load(yfile, Loader=yaml.CLoader)
        return ycontent


class BackupJesus(object):
    """BackupJesus saaaaaaaaaaaves the righteous among thy backup files from the
       fiery damnation of the void which is /dev/null!

       (Actually, /dev/null has nothing to do with this code actually, I just
       use gio.File.delete(), but that wouldn't be as funny. ;P)
       """
    BACKUPS_PATH = defs.BACKUPS_PATH
    FITY_EPOCH = defs.FITY_EPOCH

    def __init__(self):
        self.now = datetime.datetime.now()
        # I'm lazy.
        delta = datetime.timedelta
        self.backup_policies = (# First four hours of *all* backups
                                {'start_time': self.now - delta(hours=4),
                                 'end_time': self.now,
                                 'interval': delta(0)},
                                # every hour of the past week
                                {'start_time': self.now - delta(weeks=1),
                                 'end_time': self.now - delta(hours=4),
                                 'interval': delta(hours=1)},
                                # every day of the past month
                                {'start_time': self.now - delta(weeks=4),
                                 'end_time': self.now - delta(weeks=1),
                                 'interval': delta(1)},
                                # every month since Fluidity's "epoch"
                                {'start_time': datetime.datetime.fromtimestamp(
                                                       defs.FITY_EPOCH),
                                 'end_time': self.now - delta(weeks=4),
                                 'interval': delta(weeks=4)})

    def kill_stale_backups(self, dry_run=False):
        pattern = os.path.join(defs.BACKUPS_PATH, 'fluidity*.pkl*')
        kill_list = sorted(glob.glob(pattern))
        the_book_of_life = []

        for policy in self.backup_policies:
            the_book_of_life += self._find_saved_indexes(kill_list, **policy)
        the_book_of_life.sort()

        doomed = self._delete_doomed_files(kill_list, the_book_of_life, dry_run)
        elderly = [d for d in sorted(doomed) if self._is_senior_citizen(d)]
        message = "Damned {0} backups to the void; {1} were senior citizens."
        app_utils.log_line(message.format(len(doomed), len(elderly)),
                           datetime.datetime.now())

    def _delete_doomed_files(self, klist, saved_indexes, keep_the_safety_on):
        doomed = []
        for idx, victim in enumerate(klist):
            if idx not in saved_indexes:
                doomed.append(self._get_creation_time(victim))
                if not keep_the_safety_on:
                    gfile = gio.File(victim)
                    gfile.trash()
        return doomed

    def _find_saved_indexes(self, klist, start_time, end_time, interval):
        saved = []
        for idx, backup_file in enumerate(klist):
            creation_time = self._get_creation_time(backup_file)
            if start_time < creation_time < end_time:
                saved.append(idx)
                start_time = creation_time + interval
        return saved

    def _get_creation_time(self, path):
        file_name = path.replace(defs.BACKUPS_PATH + '/', '')
        time_float = float(file_name.replace('fluidity.pkl', ''))
        return datetime.datetime.fromtimestamp(time_float)

    def _is_senior_citizen(self, dt):
        return dt < datetime.datetime.now() - datetime.timedelta(weeks=9)


class CategoryRow(object):

    def __init__(self, summary):
        self.summary = summary


class SearchResult(object):
    """Simple "row" class for use with Kiwi's ObjectList"""

    def __init__(self, summary, summary_formatted, prj_key, score, na_uuid=None):
        """Initialize this SearchResult.

        Args:
            summary: a plain-text string of the result content
            summary_formatted: a string formatted with pango markup
            prj_key: ...I can't even remember what this does anymore.  FML.
            score: the 'score' returned by the relevance module
            na_uuid: if this is a NextAction, give its uuid so we can jump to it;
                defaults to None
        """
        self.summary = summary
        self.prj_key = prj_key
        self.score = score
        self.summary_formatted = summary_formatted
        self.na_uuid = na_uuid
        if self.na_uuid:
            self.result_type = "na"
            self.result_type_formatted = "<i>Next Action</i>"
        else:
            self.result_type = "prj"
            self.result_type_formatted = "<i>Project</i>"
