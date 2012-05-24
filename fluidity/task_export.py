#-*- coding:utf-8 -*-
#
# Copyright (C) 2009 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
"""Total hack to export Fity tasks to a Tomboy note."""
from __future__ import absolute_import, division, print_function


__author__ = "Jens Knutson"


import subprocess

import pathlib

from fluidity import defs
from fluidity import models
from fluidity import proto_converter


class ProtoExporter(object):

    _DUMP_FNAME = 'next_action_data.protobytes'
    _LOCAL_DUMP_PATH = defs.HACK_HACK_HACK_DROPBOX_PATH.join(_DUMP_FNAME)
    _REMOTE_HOST = "anvil.solemnsilence.org"
    _REMOTE_DUMP_PATH = pathlib.Path("/home/jensck/workspace/FluidityMobile").join(_DUMP_FNAME)
    _UPLOAD_COMMAND = "scp {0} {1}:{2}"

    def export_next_actions(self, na_list, data_mgr):
        uuid_map = proto_converter._build_uuid_map(data_mgr)

        exports_proto = models.HACK_ExportedNextActions()
        exports_proto.contexts.extend(
              [models.HACK_Context(name=context_name, 
                                   uuid=uuid_map.contexts[context_name].metadata.uuid)
               for context_name in uuid_map.contexts])
        exports_proto.next_actions.extend([proto_converter._next_action_to_proto(gtd_na, uuid_map)
                                           for gtd_na in na_list])

        with open(self._LOCAL_DUMP_PATH.as_posix(), 'w') as bytes_file:
            print("Dumping NEW HACK_ExportedNextActions protobytes to:", self._LOCAL_DUMP_PATH)
            bytes_file.write(exports_proto.SerializeToString())

        command = self._UPLOAD_COMMAND.format(self._LOCAL_DUMP_PATH.as_posix(), 
                                              self._REMOTE_HOST,
                                              self._REMOTE_DUMP_PATH.as_posix())
        print("Running:", command)
        subprocess.call(command, shell=True)
