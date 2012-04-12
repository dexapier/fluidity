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


class JSONEncoder(object):

    _DUMP_FNAME = 'fity_engage_data.json'
    _LOCAL_DUMP_PATH = defs.USER_DATA_PATH + '/fity_engage_data.json'
    _REMOTE_HOST = "anvil.solemnsilence.org"
    _REMOTE_DUMP_PATH = "/home/jensck/workspace/FluidityMobile" + "/" + _DUMP_FNAME
    _UPLOAD_COMMAND = "scp {0} {1}:{2}"
    
    def export_next_actions(self, na_list):
        contexts = sorted(set([na.context for na in na_list]))
        nas_as_json = [na.to_json() for na in na_list]
        
        json_data = {'contexts': contexts, 'nas': nas_as_json}
        
        with open(self._LOCAL_DUMP_PATH, 'w') as jsonfile:
            json.dump(json_data, jsonfile)
        
        command = self._UPLOAD_COMMAND.format(self._LOCAL_DUMP_PATH, self._REMOTE_HOST,
                                             self._REMOTE_DUMP_PATH)
        print("Running: ", command)
        subprocess.call(command, shell=True)


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
