'''
Created on Dec 13, 2011

@author: jensck
'''
import uuid

from fluidity import models
from fluidity import utils

#_PROJECT_STATUS_TO_PROTO_VALUE = {
#    'active': models.Project.ACTIVE,
#    'incubating': models.Project.INCUBATING,
#    'waiting_for': models.Project.WAITING_FOR,
#    'queued': models.Project.QUEUED,
#    'completed': models.Project.COMPLETE
#}
#_PROJECT_STATUS_FROM_PROTO_VALUE = utils.invert_dict(_PROJECT_STATUS_TO_PROTO_VALUE)


_PRIORITY_TO_PROTO_VALUE = {
     1: models.NextAction.HIGH,
     2: models.NextAction.MEDIUM,
     3: models.NextAction.LOW,
}
_PRIORITY_FROM_PROTO_VALUE = utils.invert_dict(_PRIORITY_TO_PROTO_VALUE)


_ENERGY_TO_PROTO_VALUE = {
     2: models.NextAction.HIGH,
     1: models.NextAction.MEDIUM,
     0: models.NextAction.LOW,
}
_ENERGY_FROM_PROTO_VALUE = utils.invert_dict(_ENERGY_TO_PROTO_VALUE)


def next_action_to_protobuf(na):
    """Convert a gee_tee_dee.NextAction to Protobuf-encoded bytes"""
    proto = models.NextAction()
    proto.metadata.uuid.raw_bytes = uuid.UUID(na.uuid).bytes
    proto.metadata.creation_time.timestamp = utils.to_timestamp(na.creation_date)
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
    
    proto.HACK_context = na.context
    
    proto.time_estimate_minutes = int(na.time_est)
    proto.energy_estimate = _ENERGY_TO_PROTO_VALUE[na.energy_est]
    
    if na.notes:
        proto.notes = unicode(na.notes)
    
    if na.url:
        proto.related_resources.add().uri = na.url
    
    return proto


# NOT DONE:
#def project_to_protobuf(prj):
#    """Convert a gee_tee_dee.Project to Protobuf-encoded bytes"""
#    proto = models.Project()
#    proto.status = _PROJECT_STATUS_TO_PROTO_VALUE[prj.status]
#    if proto.status == models.Project.WAITING_FOR:
#        proto.waiting_for_data = 
