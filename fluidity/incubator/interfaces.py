import abc


class ProtobufEncodable(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def to_protobuf_bytes(self):
        """Return this object as Protobuf-serialized bytes.
        
        Returns: bytearray
        """

    @abc.abstractmethod
    def populate_from_protobuf_bytes(self, protobuf_bytes):
        """Populate this instance's fields from Protobuf-serialized bytes.
        
        Returns: None (just mutates the instance in place)
        """

