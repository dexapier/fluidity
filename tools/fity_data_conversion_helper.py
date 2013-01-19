#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2010 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'


import cPickle as pickle
import datetime
import os
import sys
import uuid

import yaml

import fluidity

from collections import namedtuple
from fluidity import defs


GTD_NT = namedtuple("GTDDefaults", "default proper_type convert_func")

_DEFAULTS = {
    '_completion_date': GTD_NT(None, datetime.datetime,
                               datetime.datetime.fromordinal),
    '_creation_date': GTD_NT(datetime.datetime(2010, 1, 1, 0, 0), datetime.datetime,
                             datetime.datetime.fromordinal),
    '_due_date': GTD_NT(None, datetime.date, datetime.date.fromordinal),
    '_queue_date': GTD_NT(None, datetime.date, datetime.date.fromordinal),
    '_priority': GTD_NT(2, int, None)}

NA_DEFAULTS = {'_complete': GTD_NT(False, bool, None),
               '_context': GTD_NT("", basestring, None),
               '_energy_est': GTD_NT(1, int, None),
               '_notes': GTD_NT(None, basestring, None),
               '_time_est': GTD_NT(10.0, float, float),
               '_url': GTD_NT(None, basestring, None)}

PRJ_DEFAULTS = {
    '_aofs': GTD_NT([], list, None),
    '_incubating_next_actions': GTD_NT([], list, None),
    '_next_actions': GTD_NT([], list, None),
    '_status': GTD_NT('active', str, None),
    '_subprojects': GTD_NT([], list, None),
    '_waiting_for_since': GTD_NT(None, datetime.date,
                                  datetime.date.fromordinal),
    'waiting_for_text': GTD_NT(None, str, None)}

NA_DEFAULTS.update(_DEFAULTS)
PRJ_DEFAULTS.update(_DEFAULTS)


def dump(data, path, overwrite=False):
    """Format should be a string, either 'yaml' or 'pkl'."""
    ext = os.path.splitext(path)[1].strip('.')
    dumpers = {
        'yaml': lambda d, s: yaml.dump(d, s, defs.YAML_DUMPER, default_flow_style=False),
        'pkl': lambda d, s: pickle.dump(d, s, protocol=pickle.HIGHEST_PROTOCOL)}
    if not overwrite and os.path.exists(path):
        raise IOError("File already exists; cowardly refusing to overwrite")
    else:
        print("preparing to dump file in format {0}...".format(ext))
        with open(path, 'w') as dfile:
            dumpers[ext](data, dfile)

def get_dump_path(orig_path):
    base, ext = os.path.splitext(orig_path)
    new_ext = {'.yaml': '.pkl', '.pkl': '.yaml'}[ext]
    return base + new_ext

def load(path):
    """Format should be either 'yaml' or 'pkl'."""
    ext = os.path.splitext(path)[1].strip('.')
    loaders = {'yaml': lambda stream: yaml.load(stream, Loader=defs.YAML_LOADER),
               'pkl': lambda stream: pickle.load(stream)}
    with open(path, 'r') as lfile:
        data = loaders[ext](lfile)
    return data

def update_attrs(top):
    for na in top['queued_singletons']:
        _update_obj_attrs(na, NA_DEFAULTS)
    print("Done processing queued_singletons...")

    for i, prj in enumerate(top['projects'].values()):
        if not i % 30:
            print("Currently processing prj #{0}".format(i))

        _update_obj_attrs(prj, PRJ_DEFAULTS)
        big_na_list = prj.next_actions + prj.incubating_next_actions
        for na in big_na_list:
            _update_obj_attrs(na, NA_DEFAULTS)

def _update_obj_attrs(obj, defaults):
    for attr, ntuple in defaults.items():
        if hasattr(obj, attr):
            value = obj.__getattribute__(attr)
            if value and not isinstance(value, ntuple.proper_type):
                obj.__setattr__(attr, ntuple.convert_func(value))
        else:
            obj.__setattr__(attr, ntuple.default)
    # and give it a UUID
    _uuid_me(obj)

def _uuid_me(obj):
    """UUID me.
    
    You want me to....   give you a UUID?
    
    UUID me.
    
    Uhm, I'm sorry sir, I'm not sur...
    
    UUID me.
    """
    obj.__setattr__('uuid', str(uuid.uuid4()))


def main():
    if len(sys.argv) < 2:
        sys.exit("I need a file to operate on...")
    else:
        path = sys.argv[1]
        path = path if path.startswith('/') else os.path.realpath(path)

        top_data = load(path)
        update_attrs(top_data)
        dump(top_data, get_dump_path(path))
        print("DONE.")

if __name__ == '__main__':
    main()
