#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2012 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""An "incubator" for classes which are still subject to significant change, but are 
intended to move into a proper, more permanent home within the app."""
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'



class FityUri(object):
    """Laziness-enabling subclass of urllib.urlparse.ParseResult.
    
    (I don't understand why it isn't just called "URL" or "URI"...  that's what it *is*.)
    """

    def __init__(self, params):
        """Initialize MyClass object."""
        
