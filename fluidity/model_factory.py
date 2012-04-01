#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Copyright (C) 2012 - Jens Knutson <jens.knutson at gmail dot com>
# This software is licensed under the GNU General Public License
# version 3 or later (see the file COPYING).
from __future__ import absolute_import, division, print_function, unicode_literals


__author__ = 'Jens Knutson'


# renamed so I can have params named "uuid" without ambiguity
import uuid as uuid_lib

from fluidity import defs
from fluidity import models
from fluidity import utils


_PROJECT_STATUS_TO_PROTO_VALUE = {
    defs.ProjectStatus.ACTIVE: models.Project.ACTIVE,
    defs.ProjectStatus.INCUBATING: models.Project.INCUBATING,
    defs.ProjectStatus.WAITING_FOR: models.Project.WAITING_FOR,
    defs.ProjectStatus.QUEUED: models.Project.QUEUED,
    defs.ProjectStatus.COMPLETED: models.Project.COMPLETE
}
_PROJECT_STATUS_FROM_PROTO_VALUE = utils.invert_dict(_PROJECT_STATUS_TO_PROTO_VALUE)

_PRIORITY_TO_PROTO_VALUE = {
     defs.Priority.HIGH: models.HIGH,
     defs.Priority.MEDIUM: models.MEDIUM,
     defs.Priority.LOW: models.LOW,
}
_PRIORITY_FROM_PROTO_VALUE = utils.invert_dict(_PRIORITY_TO_PROTO_VALUE)

_ENERGY_TO_PROTO_VALUE = {
     defs.EnergyEstimate.HIGH: models.NextAction.HIGH,
     defs.EnergyEstimate.MEDIUM: models.NextAction.MEDIUM,
     defs.EnergyEstimate.LOW: models.NextAction.LOW,
}
_ENERGY_FROM_PROTO_VALUE = utils.invert_dict(_ENERGY_TO_PROTO_VALUE)









# ACTUALLY INTERESTING CODE STARTS HERE


def next_action_to_proto(na, uuid_map):
    """Convert a gee_tee_dee.NextAction to a fully populated models.NextAction object"""
    proto = models.NextAction()
    proto.metadata.uuid.raw_bytes = _new_proto_uuid().bytes
    proto.metadata.creation_time.timestamp = utils.to_timestamp(na.creation_date)
    # FIXME: include tags, when we start using them
    proto.summary = unicode(na.summary)
    proto.priority = _PRIORITY_TO_PROTO_VALUE[na.priority]
    proto.complete = na.complete
    
    if na.completion_date:
        proto.completion_time.timestamp = utils.to_timestamp(na.completion_date)
    
    if na.queue_date:
        proto.queue_time.timestamp = utils.to_timestamp(na.queue_date)
    
    if na.due_date:
        proto.due_time.timestamp = utils.to_timestamp(na.due_date)
    
    proto.context = uuid_map.contexts[na.context]
    
    proto.time_estimate_minutes = int(na.time_est)
    proto.energy_estimate = _ENERGY_TO_PROTO_VALUE[na.energy_est]
    
    if na.notes:
        proto.notes = unicode(na.notes)
    
    if na.url:
        proto.related_resources.add().uri = na.url
    
    return proto


def project_to_proto(prj, uuid_map, na_lists):
    """Convert a gee_tee_dee.Project to a models.Project object
    
    Args:
        prj: gee_tee_dee.Project to convert
        uuid_map: a fully populated UUIDMap object
        
    Returns: a fully populated models.Project
    """
    proto = models.Project()
    # metadata
    proto.metadata.uuid.raw_bytes = uuid_map.projects[prj.key_name].raw_bytes
    # FIXME: we don't do creation dates in Projects yet
    proto.metadata.creation_time.timestamp = defs.CREATION_EPOCH

    proto.summary = prj.summary
    proto.priority = _PRIORITY_TO_PROTO_VALUE[prj.priority]

    if prj.completion_date:
        proto.completion_time.timestamp = utils.to_timestamp(prj.completion_date)
    if prj.queue_date:
        proto.queue_time.timestamp = utils.to_timestamp(prj.queue_date)
    if prj.due_date:
        proto.due_time.timestamp = utils.to_timestamp(prj.due_date)

    proto.status = _PROJECT_STATUS_TO_PROTO_VALUE[prj.status]
    if proto.status == models.Project.WAITING_FOR:
        proto.waiting_for_data.summary = prj.waiting_for_text
        proto.waiting_for_data.waiting_since = utils.to_timestamp(prj.waiting_for_since)

    proto.subprojects.extend((uuid_map.projects[subprj_key].uuid
                              for subprj_key in prj.subprojects))
    
    proto.areas_of_focus.extend((uuid_map.areas_of_focus[aof_key].uuid
                                 for aof_key in prj.aofs))

    proto.active_actions.ordered_actions.extend(na_lists.active)
    proto.incubating_actions.ordered_actions.extend(na_lists.inactive)
    
    return proto

def aof_to_proto(aof_display_name):
    proto = models.AreaOfFocus()
    proto.metadata.uuid.raw_bytes = _new_proto_uuid().raw_bytes
    # FIXME: we never did creation dates for AOFs
    proto.metadata.creation_time.timestamp = defs.CREATION_EPOCH
    proto.name = aof_display_name
    return proto

def context_to_proto(context_str):


def _build_uuid_map(data_mgr):
    # NOTE: this just generates new UUIDs for everything on every run - it doesn't bother with any
    # kind of state persistence between runs, so it's only good for one-time conversions!
    umap = UUIDMap()
    umap.projects = {prj_key: _new_proto_uuid() for prj_key in data_mgr.prjs}
    umap.areas_of_focus = {aof_key: _AreaOfFocus(aof_key, _new_proto_uuid(), **aof_dict) 
                           for aof_key, aof_dict in data_mgr.aofs.iteritems()}
    
    return umap

def _new_proto_uuid():
    return models.UUID(raw_bytes=uuid_lib.uuid4().bytes)


# projects = {gee_tee_dee.Project.key_name: models.UUID}
# areas_of_focus = {area of focus key (per datamanager): model_factory._AreaOfFocus}
# contexts = { context name key (per datamanager): models.UUID}
_UUIDMap = namedtuple('_UUIDMap', 'projects', 'areas_of_focus', 'contexts')

# these fields are the models versions, not the gee_tee_dee ones
_NextActionLists = namedtuple('_NextActionLists', 'active', 'inactive')


class _AreaOfFocus(object):
    """For use in the UUIDMap.areas_of_focus dict's values"""
    
    def __init__(self, key_name, uuid, name="", projects=None):
        # `projects` arg default should be an iterable, but Python's weirdness around 
        # collections created in function/method definitions means that's a bad 
        # idea, so it's None instead.  bleh.
        self.key_name = key_name
        self.uuid = uuid
        self.name = name
        self.project_keys = projects if projects else set()
    
    def __getitem__(self, name):
        return self.__dict__.__getitem__(name)
