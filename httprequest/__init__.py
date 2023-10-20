from .exceptions import (
    HeaderNotSetError,
    NotHttp11RequestMessageError,
    NotHttp11ResponseMessageError,
    NotHttpMethodError,
    NotHttpSchemeError,
    NotHttpVersionError,
    NotPortNumberError,
    NotRequestLineError,
    NotURIError,
)
from .http import (
    URI,
    Headers,
    PreparedRequest,
    Query,
    Request,
    RequestMessage,
    Response,
    ResponseMessage,
)
from .httprequest import delete, get, patch, post, put
from .tube import Tube

"""
import httprequest

httprequest.get(
        'https://example.com',
        headers={'host': 'example.com', 'Accept': 'text/html'},
        body=b'test'
    )

request_message = httprequest.RequestMessage(
        b'GET / http/1.1\r\nHost: example.com\r\nAccept: text/html\r\n\r\ntest'
    )

request_message = httprequest.RequestMessage(
        method='GET',
        request_target='/',
        http_version='HTTP/1.1',
        headers={'host': 'example.com', 'Accept': 'text/html'},
        body=b'test'
    )

response = request_message.send('host', port, is_ssl)

prepared_request = httprequest.PreparedRequest('host', port, is_ssl, request_message)
response = prepared_request.send()

"""
