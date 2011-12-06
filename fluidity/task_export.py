#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""Total hack to export Fity tasks to a Tomboy note."""
from __future__ import absolute_import, division, print_function


__author__ = "Jens Knutson"


import json
import subprocess
import time

from xml.sax import saxutils

from fluidity import defs
from fluidity import dbus_misc
from fluidity import app_utils


class JSONEncoder(object):
    """Create a JSON array of objects with your mom."""
    
    DUMP_FNAME = '/fity_engage_data.json'
    LOCAL_DUMP_PATH = defs.USER_DATA_PATH + '/fity_engage_data.json'
    REMOTE_HOST = "anvil.solemnsilence.org"
    REMOTE_DUMP_PATH = "/home/jensck/workspace/FluidityMobile" + DUMP_FNAME
    UPLOAD_COMMAND = "scp {0} {1}:{2}"
    
    def export_next_actions(self, na_list):
        contexts = sorted(set([na.context for na in na_list]))
        nas_as_json = [na.to_json() for na in na_list]
        
        json_data = {'contexts': contexts, 'nas': nas_as_json}
        
        with open(self.LOCAL_DUMP_PATH, 'w') as jsonfile:
            json.dump(json_data, jsonfile)
        
        command = self.UPLOAD_COMMAND.format(self.LOCAL_DUMP_PATH, self.REMOTE_HOST,
                                             self.REMOTE_DUMP_PATH)
        print("Running: ", command)
        subprocess.call(command, shell=True)


class NoteMaker(object):
    """Create a Tomboy-format .note file to be sent to Conboy on a Maemo device

    Yep, it's that specific. ;P
    """
    # set up some templates.  Hooray for hardcoded naughtiness!
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


#class TomboyTest(object):
#    def __init__(self):
#        self.tb_remote = self._bus.get_object('org.gnome.Tomboy',
#                                             '/org/gnome/Tomboy/RemoteControl')
#        self.dm = managers.DataManager()
#
#        # set up some templates.  Hooray for hardcoded naughtiness!
#        self.NOTE_TITLE = "@Next Actions from Fluidity__"
#        # Note title, list
#        self.NOTE_CONTENT_T = ('<note-content version="0.1">{0}\n\n{1}\n\n\n'
#                               '</note-content>')
#        self.SECTION_T = ("\n\n<bold><size:large>{0}</size:large></bold>\n"
#                          "<list>{1}</list>")
#        self.NA_STRING_T = '{0}  ---  {1} mins  .  {2}  .  {3}\n'
#        self.BULLET_T = '<list-item dir="ltr">{0}</list-item>'
#        self.BULLET_LIST_T = '<list>{0}</list>'
#
#        #FIXME: REMOVE THIS LATER?
#        self.MAIN_INBOX = "/home/jensck/Inbox"
#        self.TOMBOY_NOTE_FOLDER = "/home/jensck/.local/share/tomboy"
#        self.FITY_SLIDER_INBOX = "/home/jensck/Inbox/.fity_note-slider"
#        self.SIDEARM_INBOX = "/media/FAMILIAR/sidearm-inbox"
#        self.CONBOY_NOTE_FOLDER = "/media/FAMILIAR/.conboy"
#        self.STARTHERE_BACKUP_FOLDER = ("/home/jensck/.local/share/boxidate/"
#                                        "start_here_backups")
#        # Tomboy "magic" - these really aren't the Right Way, but ElementTree
#        # was pissing me off, and seemed like overkill for something this small
#        #Also note: THE NEXT THREE LINES GET WRITTEN INTO START HERE,
#        #so don't screw with it unless you know what you're doing!
#        self.TB_CONTENT_START = "<note-content version=\"0.1\">"
#        self.TB_CONTENT_END = "</note-content>"
#        self.SH_CONTENT_START = self.TB_CONTENT_START + "Start Here"
#        self.NOTE_SUFFIX = ".note"
#        #what to put inbetween the chunks of content grabbed from each NOTD
#        self.PADDING = "\n\n\n"
#
#    def _back_up_note(self, uri, backup_path, use_unix_timestamp=False):
#        filename = uri.split('/')[-1] + self.NOTE_SUFFIX
#        full_path = self.TOMBOY_NOTE_FOLDER + os.sep + filename
#        if use_unix_timestamp:
#            timestamp = str(time.time())
#        else:
#            timestamp = str(datetime.date.today())
#        backup_file_path = backup_path + os.sep + timestamp + "_" + filename
#        shutil.copy2(full_path, backup_file_path)
#
#    def main(self):
#        note_maker = NoteMaker(self.tb_remote)
#        print "getting note URI"
#        note_uri = self.tb_remote.FindNote(self.NOTE_TITLE)
#        print "URI for " + self.NOTE_TITLE + " is: " + note_uri
#        print "Getting na_list"
#        na_list = self.dm.get_na_for_each_active_prj()
#        na_list.sort(key=operator.attrgetter('time_est', 'energy_est'),
#                                             reverse=True)
#        na_list.sort(key=operator.attrgetter('sort_date', 'priority', 'context'))
#
#        print "backing up file"
#        self._back_up_note(note_uri, '/home/jensck/tomboy-test', True)
#        new_note_xml = note_maker.create_final_xml(na_list)
#        print "setting new XML"
#        note_maker.set_tomboy_xml(new_note_xml)
#        print "backing up again, after."
#        self._back_up_note(note_uri, '/home/jensck/tomboy-test', True)


#if __name__ == '__main__':
#    tt = TomboyTest()
#    tt.main()
