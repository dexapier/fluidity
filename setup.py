#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2010 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).

import os

import fluidity

from distutils.core import setup
from textwrap import dedent


DATA_DIR = os.path.join("share", "fluidity")
DOCS_DIR = os.path.join("share", "doc", "fluidity-" + fluidity.__version__)


def build_data_files():
    data_files = [(os.path.join("share", "applications"), ["fluidity.desktop"]), ]

    docs = ['AUTHORS', 'ChangeLog', 'FAIL-METER', 'LICENSE', 'NEWS',
            'COPYING', 'README', 'INSTALL', 'THANKS']
    data_files.append((DOCS_DIR, docs))

    misc_data = [os.path.join('data', fname) for fname in os.listdir('data')
                 if fname is not 'Glade_and_Kiwi_integration']
        
    data_files.append((DATA_DIR, misc_data))

    for size in ('16', '24', '32', '48'):
        data_files.append(
                ('share/icons/hicolor/{0}x{0}/apps'.format(size),
                 ['icons/hicolor/{0}x{0}/apps/fluidity.png'.format(size)]))
    return data_files


setup(
    name = 'Fluidity',
    description = "Black belt GTD for Linux",
    long_description = (dedent("""\
        Black belt GTD for Linux

        Before you get your hopes up, I should warn you, Fluidity is not
        really for The Cool Kids:
            * It's not Web-based (2.0 or otherwise).  At all.
            * It doesn't sync with Remember The Milk.
            * It doesn't support arbitrary tagging.
            * It doesn't do Javascript plugins.
            * It doesn't integrate with Twitter.

        On the other hand, if...:
            * you are serious about getting to the "mind like water" state,
              through a complete, painless-as-possible GTD system
            * you have ever spent an hour or more trying to process ALL your
              inboxes (like the sign says, this is for *black belts*, people!)
            * you have gotten frustrated with the nitpicky details of shuffling
              projects between your Active and Someday/Maybe lists while still
              keeping your system current and air-tight
            * you have actually read/listened to all of David Allen's "Getting
              Things Done" and have a reasonable understanding of it, or are
              working on getting there (if you don't understand what a project
              or next action really mean in GTD terms, Fluidity might seem a bit
              overwhelming.)

        ...then Fluidity might just be what you're looking for.  If you like it,
        or have any constructive feedback, I would love to hear it.""")),
    url = 'http://fluidity.googlecode.com',
    author = 'Jens Knutson',
    author_email = 'jens.knutson@gmail.com',
    license = "GPLv3+",
    version = fluidity.__version__,
    keywords = "GTD gnome gtk pygtk productivity office organization",
    classifiers = ['Intended Audience :: End Users/Desktop',
                   'License :: OSI Approved :: GNU General Public License (GPL)',
                   'Operating System :: POSIX',
                   'Operating System :: Unix',
                   'Programming Language :: Python :: 2.6',
                   'Programming Language :: Python :: 2.7',
                   'Topic :: Desktop Environment :: File Managers',
                   'Topic :: Desktop Environment :: Gnome',
                   'Topic :: Office/Business',],
    packages = ['fluidity', 'fluidity.ui', 'fluidity.incubator'],
    scripts = ["bin/fluidity", "bin/slider"],
    provides = ["fluidity"],
    data_files = build_data_files()
)
