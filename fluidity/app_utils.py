#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2011 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""App-specific utils"""
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'


import datetime
import os
import string  #IGNORE:W0402  # it is NOT deprecated. ;-P

from fluidity import defs, models, utils


def format_for_dict_key(orig_string):
    """Return a cleaned up version of `orig_string` which will work as a dict key.

    In line with Python's rules & guidelines about attribute naming, orig_string
    is stripped of everything but lowercase ascii characters a-z & digits 0-9,
    with spaces converted to underscores.
    """
    new = str(orig_string).decode('ascii', 'ignore').lower()
    new = "".join([i for i in new if i in defs.SANITARY_CHARS])
    new = new.replace(' ', '_')
    new = "_" + new if new[0] in string.digits else new
    return new


def log_line(message, msg_datetime=None, path=defs.LOG_FILE_PATH, debug=False):
    """Write `message` to log file at `path` with a timestemp of `msg_time`.

    Not intended for recording tracebacks; that's what ABRT is for.  ;-P
    """
    if not debug or os.getenv('USER') in ('jknutson', 'jensck'):
        if not msg_datetime:
            msg_datetime = datetime.datetime.now()
        timestamp = str(msg_datetime).split('.')[0]
        log_msg = timestamp + " -- " + message + "\n"
        with open(path, 'a') as log_file:
            log_file.write(log_msg)


def to_model_datetimestamp(date_obj):
    """Convert `date_obj` to a fluidity.models.DateTimeStamp.
    
    Args:
        date_obj: a datetime.datetime or datetime.date obj. or anything else 
            with a .timetuple() method
    
    Returns: a fluidity.models.DateTimeStamp
    """
    dts = models.DateTimeStamp()
    dts.timestamp = utils.to_timestamp(date_obj)
    return dts


def validate_paths():
    # main_prj_support_folder must be first in the list below - have to ensure
    # the main folder is created before trying to create the others
    for p in (defs.ALL_DATA_FOLDERS):
        if not os.path.exists(p):
            os.mkdir(p)
            if not os.path.exists(p):
                # FIXME: LAME!  Should define a proper exception instead
                raise Exception("Could not create folder {0}".format(p))
