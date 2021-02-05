"""
Exception definitions.
"""

import json

class CommandError(Exception):
    pass


class NoTokenLookupException(Exception):
    """This form of authentication does not support looking up
       endpoints from an existing token."""
    pass


class EndpointNotFound(Exception):
    """Could not find Service or Region in Service Catalog."""
    pass


class SchemaNotFound(KeyError):
    """Could not find schema"""
    pass


class ClientException(Exception):
    """
    The base exception class for all exceptions this library raises.
    """
    def __init__(self, code, message=None, details=None):
        self.code = code
        self.message = message or self.__class__.message
        self.details = details

    def __str__(self):
        return "%s (HTTP %s): %s" % (self.message, self.code, self.details)

class BadRequest(ClientException):
    """
    HTTP 400 - Bad request: you sent some malformed data.
    """
    http_status = 400
    message = "Bad request"


class Unauthorized(ClientException):
    """
    HTTP 401 - Unauthorized: bad credentials.
    """
    http_status = 401
    message = "Unauthorized"

class Forbidden(ClientException):
    """
    HTTP 403 - Forbidden: your credentials don't give you access to this
    resource.
    """
    http_status = 403
    message = "Forbidden"


class NotFound(ClientException):
    """
    HTTP 404 - Not found
    """
    http_status = 404
    message = "Not found"


class NotAcceptable(ClientException):
    """
    HTTP 406 - Not Acceptable
    """
    http_status = 406
    message = "Not acceptable"


class Conflict(ClientException):
    """
    HTTP 409 - Conflict
    """
    http_status = 409
    message = "Conflict"


class OverLimit(ClientException):
    """
    HTTP 413 - Over limit: you're over the API limits for this time period.
    """
    http_status = 413
    message = "Over limit"

class HTTPInternalError(ClientException):
    """
    HTTP 500 - Internal error
    """
    http_status = 500
    message = "Internal error"

# NotImplemented is a python keyword.
class HTTPNotImplemented(ClientException):
    """
    HTTP 501 - Not Implemented: the server does not support this operation.
    """
    http_status = 501
    message = "Not Implemented"


# In Python 2.4 Exception is old-style and thus doesn't have a __subclasses__()
# so we can do this:
#     _code_map = dict((c.http_status, c)
#                      for c in ClientException.__subclasses__())
#
# Instead, we have to hardcode it:
_code_map = dict((c.http_status, c) for c in [BadRequest, Unauthorized,
                   Forbidden, NotFound, NotAcceptable, Conflict, OverLimit,
                    HTTPInternalError, HTTPNotImplemented])


def from_response(response, body):
    """
    Return an instance of an ClientException or subclass
    based on an httplib2 response.

    Usage::

        resp, body = http.request(...)
        if resp.status != 200:
            raise exception_from_response(resp, body)
    """
    from lib import utils
    cls = _code_map.get(response.status, ClientException)
    body_json = None
    if body is not None and len(body) > 0 and body[0] == '{':
        body_json = json.loads(body)
    if body_json:
        if 'code' in body_json and 'details' in body_json:
            details = utils.ensure_ascii(body_json['details'])
            return cls(code=response.status, details=details)
        elif 'error' in body_json and 'code' in body_json['error'] and \
                'message' in body_json['error'] and \
                'title' in body_json['error']:
            return cls(code=body_json['error']['code'],
                        message=body_json['error']['title'],
                        details=body_json['error']['message'])
    if body:
        message = "Unable to communicate with API service: %s." % body
        details = None
        return cls(code=response.status, message=message, details=details)
    return cls(code=response.status)
