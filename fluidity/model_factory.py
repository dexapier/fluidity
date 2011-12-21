'''
Created on Dec 13, 2011

@author: jensck
'''
import uuid

from fluidity import app_utils
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
    return _NextActionToProtoConverter(na).convert()


# NOT DONE:
#def project_to_protobuf(prj):
#    """Convert a gee_tee_dee.Project to Protobuf-encoded bytes"""
#    proto = models.Project()
#    proto.status = _PROJECT_STATUS_TO_PROTO_VALUE[prj.status]
#    if proto.status == models.Project.WAITING_FOR:
#        proto.waiting_for_data = 
    

class _NextActionToProtoConverter(object):
    
    def __init__(self, next_action):
        self._na = next_action

    def convert(self):
        proto = models.NextAction()
        proto.metadata = self._build_common_metadata()
        proto.summary = self._na.summary
        proto.priority = _PRIORITY_TO_PROTO_VALUE[self._na.priority]

        if self._na.completion_date:
            proto.completion_time = app_utils.to_model_datetimestamp(
                    self._na.completion_date)

        if self._na.queue_date:
            proto.queue_time = app_utils.to_model_datetimestamp(self._na.queue_date)
        
        if self._na.due_date:
            proto.due_time = app_utils.to_model_datetimestamp(self._na.due_date)
        
        proto.HACK_context = self._na.context
        
        proto.time_estimate_minutes = self._na.time_est
        proto.energy_estimate = _ENERGY_TO_PROTO_VALUE[self._na.energy_est]
        
        if self._na.notes:
            proto.notes = self._na.notes
        
        if self._na.url:
            proto.related_resources.add(models.URI(uri=self._na.url))

        return proto

    def _build_common_metadata(self):
        meta = models.CommonMetadata()
        meta.uuid = models.UUID(raw_bytes=uuid.UUID(self._na.uuid).bytes)
        meta.creation_time = app_utils.to_model_datetimestamp(self._na.creation_date)
        return meta
