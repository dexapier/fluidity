#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2010 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""Misc. functions for use throughout Fluidity."""
from __future__ import absolute_import, division, print_function


__author__ = 'Jens Knutson'


import calendar


def invert_dict(orig):
    zippy = zip(orig.values(), orig.keys())
    return dict(zippy)

def to_timestamp(date_obj):
    """Convert `date_obj` to a UNIX timestamp.
    
    Args:
        date_obj: a datetime.datetime or datetime.date obj. or anything else 
            with a .timetuple() method
    
    Returns: a UNIX timestamp, as an int
    """
    # how is this not part of the stdlib?
    return calendar.timegm(date_obj.timetuple())
