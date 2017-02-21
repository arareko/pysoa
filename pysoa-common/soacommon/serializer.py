
class InvalidMessage(Exception):
    pass


class InvalidField(Exception):
    pass


class Serializer(object):

    def dict_to_blob(self, message_dict):
        """
        Take a message in the form of a dict and return a serialized message
        in the form of bytes (string).

        returns: string
        raises: InvalidField
        """
        raise NotImplementedError

    def blob_to_dict(self, blob):
        """
        Take a serialized message in the form of bytes (string) and return a
        dict.

        returns: dict
        raises: InvalidMessage
        """
        raise NotImplementedError