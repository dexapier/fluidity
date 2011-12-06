#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


import datetime
import os
import shutil

import yaml

from fluidity import defs


class FirstTimeBot(object):

    def __init__(self):
        pass

    def create_initial_files_and_paths(self):
        # check for initial data file - if missing, copy in the default one
        if not os.path.exists(defs.USER_DATA_MAIN_FILE):
            shutil.copy(os.path.join(defs.APP_DATA_PATH,
                                     defs.USER_DATA_MAIN_FNAME),
                        defs.USER_DATA_MAIN_FILE)
        # if no recurrence yaml file exists, create it
        if not os.path.exists(defs.RECURRENCE_DATA):
            self._create_initial_recurrence_file(defs.RECURRENCE_DATA)
        # and make everything else, too, if necessary.
        for folder in defs.ALL_DATA_FOLDERS:
            if not os.path.exists(folder):
                os.makedirs(folder)
        # now copy in a warning to the Projects folder
        prj_warning_msg_path = \
            os.path.join(defs.MAIN_PRJ_SUPPORT_FOLDER,
                         defs.PROJECT_FOLDER_DELETION_WARNING_FILE_NAME)
        if not os.path.exists(prj_warning_msg_path):
            shutil.copy(defs.PROJECT_FOLDER_DELETION_WARNING_PATH,
                        prj_warning_msg_path)
        # FIXME: once it's needed, copy in a note to the new Inbox folder

    def _create_initial_recurrence_file(self, full_path):
        data = {'daily': [], 'weekly': [], 'monthly': [],
                'last_run': datetime.date.today()}
        print("Creating initial recurrence file...")
        with open(full_path, 'w') as yfile:
            yaml.dump(data, yfile, Dumper=yaml.CDumper, default_flow_style=False)
