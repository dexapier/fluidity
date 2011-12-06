#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2010 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""Resets the age attribute on each Next Action for all active Projects."""
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'


try:
    import cPickle as pickle
except ImportError:
    import pickle
import datetime

from fluidity import defs


def main():
    with open(defs.USER_DATA_MAIN_FILE, 'r') as pkl:
        top_data = pickle.load(pkl)

    for prj in [p for p in top_data['projects'].values() if p.status == 'active']:
        for na in prj.next_actions:
            if not na.complete:
                na.creation_date = datetime.datetime.now()

    with open(defs.USER_DATA_MAIN_FILE, 'w') as pkl:
        pickle.dump(top_data, pkl, pickle.HIGHEST_PROTOCOL)


if __name__ == '__main__':
    main()

