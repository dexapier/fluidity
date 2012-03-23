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


def next_action_to_protobuf(na):
    """Convert a gee_tee_dee.NextAction to Protobuf-encoded bytes"""
    proto = models.NextAction()
    proto.metadata.uuid.raw_bytes = uuid_lib.UUID(na.uuid).bytes
    proto.metadata.creation_time.timestamp = utils.to_timestamp(na.creation_date)
    # FIXME: include tags, when we start using them
    proto.summary = na.summary
    proto.priority = _PRIORITY_TO_PROTO_VALUE[na.priority]
    proto.complete = na.complete
    
    if na.completion_date:
        proto.completion_time.timestamp = utils.to_timestamp(
                na.completion_date)
    
    if na.queue_date:
        proto.queue_time.timestamp = utils.to_timestamp(na.queue_date)
    
    if na.due_date:
        proto.due_time.timestamp = utils.to_timestamp(na.due_date)
    
    # WHEREWELEFTOFF: mapping contexts to their values
    # I think the solution here is to get a value from some dict 
    # we've built up, and if it's not found, create one.
    proto.context = na.context
    
    proto.time_estimate_minutes = int(na.time_est)
    proto.energy_estimate = _ENERGY_TO_PROTO_VALUE[na.energy_est]
    
    if na.notes:
        proto.notes = unicode(na.notes)
    
    if na.url:
        proto.related_resources.add().uri = na.url
    
    return proto


def project_to_protobuf(prj, uuid_map):
    """Convert a gee_tee_dee.Project to Protobuf-encoded bytes
    
    Args:
        prj: gee_tee_dee.Project to convert
        uuid_map: a fully populated UUIDMap object
        
    Returns: a fully populated models.Project
    """
    proto = models.Project()
    # metadata
    # FIXME: are we sure that every project is going to have this?  I bit no. it won't
    proto.metadata.uuid.raw_bytes = uuid_map.projects[prj.key_name].uuid.raw_bytes
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

    proto.subprojects.extend((models.UUID(raw_bytes=uuid.bytes) for uuid in prj.subprojects))

    proto.areas_of_focus.extend((uuid_map.areas_of_focus[aof_key].uuid for aof_key in prj.aofs))

    # FIXME: AOFs: see next_action_to_protobuf() notes re: contexts


def build_aof_dict_to_proto_mapping(data_mgr):
    """Returns: {aof_name: model_factory.AreaOfFocus}"""
    # NOTE: this just generates new UUIDs on every run - it doesn't bother with any
    # kind of state persistence between runs
    mapping = {aof_key: AreaOfFocus(aof_key, uuid_lib.uuid4(), **aof_dict) 
               for aof_key, aof_dict in data_mgr.aofs.iteritems()}
    return mapping



class UUIDMap(object):

    def __init__(self, projects_dict, areas_of_focus_dict):
        self.projects = projects_dict
        self.areas_of_focus = areas_of_focus_dict


class AreaOfFocus(object):
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
