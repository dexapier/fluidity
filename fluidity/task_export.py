#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""Total hack to export Fity tasks to a Tomboy note."""
from __future__ import absolute_import, division, print_function


__author__ = "Jens Knutson"


import json
import operator
import os
import subprocess
import time

from xml.sax import saxutils

from fluidity import app_utils
from fluidity import dbus_misc
from fluidity import defs
from fluidity import models
from fluidity import model_factory


class ProtobufEncoder(object):

    _DUMP_FNAME = 'next_action_data.protobytes'
    _LOCAL_DUMP_PATH = os.path.join(defs.HACK_HACK_HACK_DROPBOX_PATH, 
                                    'next_action_data.protobytes')
    _REMOTE_HOST = "anvil.solemnsilence.org"
    _REMOTE_DUMP_PATH = os.path.join("/home/jensck/workspace/FluidityMobile", 
                                     _DUMP_FNAME)
    _UPLOAD_COMMAND = "scp {0} {1}:{2}"
    
    def export_next_actions(self, na_list):
        proto = models.HACK_ExportedNextActions(
            contexts=sorted(set([na.context for na in na_list])))
        proto.next_actions.extend([model_factory.next_action_to_protobuf(na) 
                                   for na in na_list])

        with open(self._LOCAL_DUMP_PATH, 'w') as bytes_file:
            print("Dumping Action proto bytes to:", self._LOCAL_DUMP_PATH)
            bytes_file.write(proto.SerializeToString())
        
#        command = self._UPLOAD_COMMAND.format(self._LOCAL_DUMP_PATH, 
#                                              self._REMOTE_HOST,
#                                              self._REMOTE_DUMP_PATH)
#        print("Running: ", command)
#        subprocess.call(command, shell=True)

    def _sort_na_list(self, na_list):
        # FIXME: sorting this list should live in ONE place - right now 
        # it's (at least) in 2 places.
        na_list = sorted(na_list, key=operator.attrgetter('context'))
        na_list = sorted(na_list, 
                         key=operator.attrgetter('age', 'time_est', 'energy_est'), 
                         reverse=True)
        na_list = sorted(na_list, key=operator.attrgetter('sort_date', 'priority'))
        return na_list

    def __fix_0h_loh_dotcom(self):
        pass  # just a hack to make Ohloh wake up.


class NoteMaker(object):
    """Create a Tomboy-format .note file to be sent to Conboy on a Maemo device

    Yep, it's that specific. ;P
    """
    # Set up some templates.  Hooray for hardcoded naughtiness!
    NOTE_TITLE = "@Next Actions from Fluidity__"
    # Note title, list
    NOTE_CONTENT_T = '<note-content version="0.1">{0}\n\n{1}\n\n\n</note-content>'
    SECTION_T = "\n\n<bold><size:large>{0}</size:large></bold>\n<list>{1}</list>"
    NA_STRING_T = '{0}  ---  {1} mins  .  {1}  .  {2}\n'
    BULLET_T = '<list-item dir="ltr">{0}</list-item>'
    BULLET_LIST_T = '<list>{0}</list>'

    def create_final_xml(self, na_list):
        sections_xml = ""
        context_sections = self._create_context_sections(na_list)
        for section in sorted(context_sections.keys()):
            section_title = "@" + section.capitalize()
            # wtf?  where are the newlines coming from?
            section_title = section_title.replace('\n', '')
            sections_xml += self.SECTION_T.format(section_title,
                                                  context_sections[section])
        final_xml = self.NOTE_CONTENT_T.format(self.NOTE_TITLE, sections_xml)
        return final_xml

    def set_tomboy_xml(self, final_xml):
        uri = dbus_misc.notes_proxy.FindNote(self.NOTE_TITLE)
        dbus_misc.notes_proxy.SetNoteContentsXml(uri, final_xml)
        # this is retarded, but apparently necessary... otherwise tomboy doesn't
        # write the new XML to disk.  *@!(*&$)##$(*&
        time.sleep(4)
        dbus_misc.notes_proxy.DisplayNote(uri)
        time.sleep(4)
        dbus_misc.notes_proxy.HideNote(uri)

    def _create_context_sections(self, na_list):
        sections = {}
        for na in na_list:
            task_str = self._create_task_string(na)
            task_str = self.BULLET_T.format(task_str)
            # just use the context name as the dict_key
            section_key = app_utils.format_for_dict_key(na.context)
            if section_key not in sections:
                sections[section_key] = ""
            sections[section_key] += task_str
        return sections

    def _create_task_string(self, na):
        clean_summary = saxutils.escape(na.summary)
        formatted_summary = self._set_priority(na, clean_summary)
        # save some space...
        if na.energy_est_word == "Normal":
            energy_est = "e= "
        elif na.energy_est_word == "High":
            energy_est = "e! "
        elif na.energy_est_word == "Low":
            energy_est = "e- "
        # we want it to look like this:
        # summary - time-est - energy-est - due date
        # where summary has been formatted according to priority
        task_str = self.NA_STRING_T.format(formatted_summary,
                                           str(int(na.time_est)),
                                           energy_est,
                                           str(na.due_date))
        task_str += self._set_notes_and_url(na, task_str)
        return task_str

    def _set_notes_and_url(self, na, task_str):
        if na.url or na.notes:
            sub_list = (self.BULLET_T.format("URL: " + saxutils.escape(na.url))
                        if na.url else "")
            if na.notes:
                # more cargo-culting - I have no fucking idea why I have to do
                # this, except that if I don't, I can't get newlines in my
                # notes field.  Bah!
                notes = saxutils.escape(na.notes)
#                if notes.startswith("* "):
#                    notes = notes[2:]
#                notes = notes.replace("\n* ", "\no ")
                # NOTE: Unicode is FUN!  ....and necessary.  Damned foreigners!
                # FURTHER NOTE: relax, spazzy-pants, I'm not actually hateful,
                # just very lazy.
                notes = notes.replace("\n", "&#x2028;")
                sub_list += self.BULLET_T.format(notes)
            return self.BULLET_LIST_T.format(sub_list) + '\n'
        else:
            return ""

    def _set_priority(self, na, task_str):
        if na.priority == 1:
            task_str = "<bold>" + task_str + "</bold>"
        elif na.priority == 3:
            task_str = "<italic>" + task_str + "</italic>"
        return task_str
