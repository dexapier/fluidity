#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


try:
    import cPickle as pickle
except ImportError:
    import pickle
import os
import shutil
import sys
import time

import yaml

from textwrap import dedent


ORIGINAL_WORKING_DIR = os.path.abspath(os.curdir)
# no idea why these are both needed, but I have seen both of them break, 
# depending on the situation.  bah.
sys.path.append("/home/jensck/workspace/Fluidity")
import fluidity.defs as defs
import fluidity.gee_tee_dee  #@UnusedImport  # pylint: disable-msg=W0611

DEFAULT_FILE_BASE_NAME = 'fity_data'
DEFAULT_YAML_FNAME = DEFAULT_FILE_BASE_NAME + '.yaml'
DEFAULT_PKL_FNAME = DEFAULT_FILE_BASE_NAME + '.pkl'
DEFAULT_YAML_PATH, DEFAULT_PKL_PATH = [os.path.join(ORIGINAL_WORKING_DIR, name) 
                                       for name in
                                       DEFAULT_YAML_FNAME, DEFAULT_PKL_FNAME]
COWARDLY_REFUSAL = ("{0} found in current folder: "
                    "cowardly refusing to overwrite it.")
USAGE_MESSAGE = dedent("""\
    Usage:
    fity_data_debug_converter.py [fity_data.ext]
    
    If fity_data.ext is a yaml file, you'll get back a pkl in your current working 
    directory, or vice versa.
    
    SPECIAL CASES:
        If you feed it a yaml file, and $HOME/.local/share/fluidity/fluidity.pkl 
        doesn't exist, the resulting pickle file will get dumped to that latter 
        path instead of the current working directory.
        
        If you give it no args, you'll get $HOME/.local/share/fluidity/fluidity.pkl
        copied as a yaml file to your current working directory (provided there 
        isn't already one there).
        """)


def back_up_fity_data_file():
    backup_path = os.path.join(defs.BACKUPS_PATH,
                               defs.USER_DATA_MAIN_FNAME + str(time.time()))
    shutil.copy(defs.USER_DATA_MAIN_FILE, backup_path)

def fail():
    print(USAGE_MESSAGE)
    sys.exit(1)

def convert_fity_data_file(orig_path, new_path, delete_original=False):
    """Convert orig_path YAML to pickle or vice-versa, unless new_path exists."""
    if os.path.exists(new_path):
        print(COWARDLY_REFUSAL.format(new_path))
#    print "well, we got this far...."
    if orig_path.endswith('.yaml') and new_path.endswith('.pkl'):
        with open(orig_path, 'r') as orig_file:
            fity_data = yaml.load(orig_file, Loader=defs.YAML_LOADER)
        with open(new_path, 'w') as new_file:
            pickle.dump(fity_data, new_file, protocol=pickle.HIGHEST_PROTOCOL)
    elif orig_path.endswith('.pkl') and new_path.endswith('.yaml'):
        with open(orig_path, 'r') as orig_file:
            fity_data = pickle.load(orig_file)
        with open(new_path, 'w') as new_file:
            yaml.dump(fity_data, new_file, Dumper=defs.YAML_DUMPER,
                      default_flow_style=False)
    else:
        fail()
    if delete_original:
        os.remove(orig_path)


def main():
    yaml_exists, fity_data_exists = [os.path.exists(p) for p in
                                     DEFAULT_YAML_PATH, defs.USER_DATA_MAIN_FILE]
    orig, new = None, None
    delete_orig = False

    if len(sys.argv) == 1:
        if not fity_data_exists or yaml_exists:
            fail()
        else:
            orig = defs.USER_DATA_MAIN_FILE
            new = DEFAULT_YAML_PATH
    elif len(sys.argv) == 2:
        orig = sys.argv[1]
        base = "".join(orig.split('.')[:-1])
        orig = os.path.join(ORIGINAL_WORKING_DIR, orig)
        if orig.endswith('.yaml'):
            if not fity_data_exists:
                new = defs.USER_DATA_MAIN_FILE
                delete_orig = True
            ext = '.pkl'
        else:
            ext = '.yaml'
        if not new:
            new = os.path.join(ORIGINAL_WORKING_DIR, base + ext)
    else:
        fail()

    if fity_data_exists:
        back_up_fity_data_file()
#    print orig, new, delete_orig
    convert_fity_data_file(orig, new, delete_orig)


if __name__ == '__main__':
    main()
