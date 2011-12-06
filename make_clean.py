#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2010 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'


import glob
import os
import shutil


rm_files = (glob.glob("/home/jensck/workspace/Fluidity/*/*.pyc") +
            glob.glob("/home/jensck/workspace/Fluidity/*/*/*.pyc") +
            glob.glob("/home/jensck/workspace/Fluidity/*.pyc"))
rm_files.extend(['/usr/bin/fluidity', '/usr/bin/slider'])
rm_files.extend(glob.glob('/usr/lib/python2.7/site-packages/Fluidity*.egg-info'))
rm_files.extend(glob.glob("/usr/share/icons/hicolor/*/apps/fluidity.png"))
rm_dirs = ['dist', 'build', '/usr/lib/python2.7/site-packages/fluidity']
rm_dirs.extend(glob.glob('/usr/share/doc/fluidity*'))


os.chdir('/home/jensck/workspace/Fluidity')
for path in rm_dirs:
    try:
        shutil.rmtree(path)
    except OSError as e:
        print(e)
for fname in rm_files:
    try:
        os.remove(fname)
    except OSError as e:
        print(e)

print("***\nDone.")
