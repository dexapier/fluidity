#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2012 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
#
"""Sketch of a new data manager design, possibly only used to clarify my thinking on the subject."""
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'


import abc

import pathlib

from fluidity import defs
from fluidity.incubator import perdi


_SHOVE_PATH = pathlib.Path(defs.USER_DATA_PATH).join('DataManagerNG_testing.shove')


class DataManagerNG(object):
    """DataManager, reborn."""

    def __init__(self):
        """Initialize DataManagerNG object."""
        self._datastore = perdi.PerdiShove(_SHOVE_PATH)



class LifecycleManaged(object):
    
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def on_create(self):
        pass
    
    @abc.abstractmethod
    def on_update(self):
        pass

    @abc.abstractmethod
    def on_delete(self):
        pass
    
