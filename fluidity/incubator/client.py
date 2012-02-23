#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2012 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""module_docs"""
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'



class FityClient(object):
    """Base class for Fluidity clients.
    
    We're not using the standard REST HTTP verbs here for our method names, but because we're doing
    similar things, they do follow REST-like rules, e.g.: "get" is always "safe", i.e.:
    it has no side effects, "put" and "delete" are always idempotent, and "post" is its usual
    ill-defined, state-modifying self.
    """


