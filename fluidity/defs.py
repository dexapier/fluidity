#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2010 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""Misc. app-wide constants."""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


import os
import string
import sys
import uuid

import pathlib

from xdg import BaseDirectory


# Py3K compat.
if not hasattr(string, 'ascii_lowercase'):
    # yep, we're monkey patching.  deal with it.
    string.ascii_lowercase = string.lowercase


def _find_app_data_path():
    """Determine (hackishly) if we're running from a proper install or not."""
    data_path = ""
    exec_path = os.path.dirname(os.path.realpath(sys.modules[__name__].__file__))
    uninstalled_data_path = os.path.join(os.path.dirname(exec_path), 'data')
    if os.path.exists(uninstalled_data_path):
        data_path = uninstalled_data_path
    else:
        data_path = os.path.join(sys.prefix, "share", "fluidity")
    return data_path


def _get_read_review_path():
    # This is rather primitive, but I refuse to do more than this
    # for now - it'll work fine in 90%+ of cases.
    path = ""
    dirs_file = os.path.join(os.getenv('HOME'), BaseDirectory.xdg_config_dirs[0],
                             'user-dirs.dirs')
    with open(dirs_file, 'r') as dirs:
        for line in dirs:
            if "XDG_DOCUMENTS_DIR" in line:
                path = line
    path = path.strip()
    path = path.replace("$HOME", os.getenv('HOME'))
    path = path.replace('"', '')
    path = path.split('=')[1]
    path = os.path.join(path, "Read-Review")
    return path


def _get_yaml_loader_dumper():
    # WTF?  How can a Fedora install NOT have the YAML C dumper?!
    # I can't wait for the day when Android is usable as a full workstation.
    # Desktop Linux: the only things that suck even harder than this are 
    # the alternatives.
    try:
        return yaml.CLoader, yaml.CDumper
    except AttributeError:
        return yaml.Loader, yaml.Dumper


APP_NAME = 'Fluidity'
DBUS_BUS_NAME = 'org.solemnsilence.Fluidity'
DBUS_OBJECT_PATH = '/org/solemnsilence/Fluidity'
UUID_NAMESPACE_URL = "http://solemnsilence.org/fluidity" 
# FIXME: should be datetime objs.  grr.
FITY_EPOCH = 1230768000.0
CREATION_EPOCH = 1262325600.0

# this just indicates "this is not a real context UUID, it's 'faked-out'"
FAKE_CONTEXT_UUID = uuid.UUID(
       bytes='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xDE\xAD\xBE\xEF')

YAML_LOADER, YAML_DUMPER = _get_yaml_loader_dumper()

### NOTES APP STUFF ###
# FIXME: this is lame.  Figure out /real/ Tomboy vs. Gnote handling later
# For now, the value below must be either "tomboy" or "gnote" (all in lowercase)
NOTES_APP = "Tomboy"
NOTES_BUS_NAME = 'org.gnome.' + NOTES_APP
NOTES_OBJECT_PATH = '/org/gnome/' + NOTES_APP + '/RemoteControl'
NEW_PROJECT_NOTE_TEMPLATE_NOTE_TITLE = "Projects - active Notebook Template"


### MISC TEXT FIELD VALUES AND TEMPLATES ###
# FIXME: almost all of these should go somewhere else as I refactor Fity
AUTOSAVE_INTERVAL = int(60 * 1)   # minutes between autosaves of the data file
GTK_DATE_TEXT_TEMPLATE = "%B %d, %Y"
DEFAULT_TIME_EST = 10.0
UNRECOGNIZED_DATE_TEXT = "(date unrecognized)"
# represents "there is no AOF assigned to this project", i.e.: "unfiled"
NO_AOF_ASSIGNED = "No AOF Assigned"
ENGAGE_TOTALS_TEMPLATE = "Tasks shown: {0}   Total time: {1}h:{2}m"
ARCHIVED_SINGLETONS_TIME_TMPLT = '-%Y-%m-%d-%H:%M'
SANITARY_CHARS = string.ascii_lowercase + string.digits + " "

### PATHS ###
HOME_DIR = os.path.expanduser("~")
HOME_PATH = pathlib.Path(HOME_DIR)
APP_DATA_PATH = _find_app_data_path()
USER_DATA_PATH = BaseDirectory.save_data_path("fluidity")
LOG_FILE_PATH = os.path.join(USER_DATA_PATH, 'fluidity_debug.log')
RECURRENCE_DATA = os.path.join(USER_DATA_PATH, 'recurring_tasks.yaml')
USER_DATA_MAIN_FNAME = 'fluidity.pkl'
USER_DATA_MAIN_FILE = os.path.join(USER_DATA_PATH, USER_DATA_MAIN_FNAME)
PROCESSED_STUFF_FILE_NAME = 'processed_stuff.pkl'
BACKUPS_PATH = os.path.join(USER_DATA_PATH, "backups")
ARCHIVED_SINGLETONS_FNAME = 'archived_singletons{0}.pkl'

DROPBOX_PATH = pathlib.Path(HOME_PATH, 'Dropbox')
DROPBOX_INBOX_PATH = pathlib.Path(DROPBOX_PATH, 'Inbox')


HACK_HACK_HACK_DROPBOX_PATH = pathlib.Path(DROPBOX_PATH, "Fluidity")

# PROJECT SUPPORT FILE PATHS
READ_REVIEW_PATH = _get_read_review_path()
INBOX_FOLDER = os.path.join(HOME_DIR, "Inbox")
NOTE_SLIDER_FOLDER = os.path.join(USER_DATA_PATH, 'slider-inbox')
MAIN_PRJ_SUPPORT_FOLDER = os.path.join(HOME_DIR, "Projects")
ACTIVE_FOLDER = os.path.join(MAIN_PRJ_SUPPORT_FOLDER, "Active")
COMPLETED_FOLDER = os.path.join(MAIN_PRJ_SUPPORT_FOLDER, "Completed")
INCUBATING_FOLDER = os.path.join(MAIN_PRJ_SUPPORT_FOLDER, "Incubating")
QUEUED_FOLDER = os.path.join(MAIN_PRJ_SUPPORT_FOLDER, "Queued")
WAITING_FOR_FOLDER = os.path.join(MAIN_PRJ_SUPPORT_FOLDER, "Waiting For")
SINGLETON_FILES = os.path.join(ACTIVE_FOLDER, "singletons")
PROJECT_FOLDER_DELETION_WARNING_FILE_NAME = "DO_NOT_DELETE_THIS_FOLDER.txt"
PROJECT_FOLDER_DELETION_WARNING_PATH = os.path.join(
    APP_DATA_PATH, PROJECT_FOLDER_DELETION_WARNING_FILE_NAME)

# doesn't include USER_DATA_PATH since BaseDirectory.save_data_path takes
# care of ensuring that path exists
# FIXME: once a global Inbox folder is implemented for people other than me
ALL_DATA_FOLDERS = [
    NOTE_SLIDER_FOLDER,
    MAIN_PRJ_SUPPORT_FOLDER,
    ACTIVE_FOLDER,
    COMPLETED_FOLDER,
    INCUBATING_FOLDER,
    QUEUED_FOLDER,
    WAITING_FOR_FOLDER,
    BACKUPS_PATH,
    INBOX_FOLDER,
]

IGNORED_INBOX_PATHS = [
    "0 - Eventually sort.  bah",
    "1 - To be processed when Fity is ready",
    "3 - Torrents",
    "2 - Receipts to process",
    "90 Day Storage",
]


# ugh, this file is getting INSANE.

# These are basically enums.  Gotta find one of the better solutions to this though.
class Priority:
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class EnergyEstimate:
    LOW = 0
    MEDIUM = 1
    HIGH = 2

class ProjectStatus:
    # this is an "enum" - if you write to these values, I will hurt you.
    # (eventually we should pick a Python enum class that's useful and 
    # agreeable, but until then, just *pretend* those are read-only values.
    ACTIVE = 'active'
    INCUBATING = 'incubating'
    WAITING_FOR = 'waiting_for'
    QUEUED = 'queued'
    COMPLETED = 'completed'
