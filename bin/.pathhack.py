#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).


__author__ = 'Jens Knutson'


import os
import sys


# my attempt at determining if we're running from a source tarball extract, or
# from a proper install
launcher_path = os.path.realpath(sys.modules[__name__].__file__)
parent_dir = os.path.dirname(launcher_path)
grandparent = os.path.dirname(parent_dir)

for path in (parent_dir, grandparent):
    fitypath = os.path.join(path, 'fluidity')
    if os.path.isdir(fitypath) and fitypath not in sys.path:
        sys.path.insert(0, path)
        break

try:
    import fluidity
except ImportError:
    sys.exit("Sorry, I can't find the package `fluidity`. Please install "
             "using the included setup.py, or run `launch_fluidity`.")
