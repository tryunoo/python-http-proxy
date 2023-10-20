from . import exceptions
from .http import URI, Headers, MediaType, RequestBody, RequestMessage, Response

TIME_ZONE = "Asia/Tokyo"


def send(method: str, url: str, headers: dict | None = None, raw_body: bytes | None = None) -> Response | None:
    uri = URI(url)
    scheme = uri.scheme
    if scheme.lower() == "http":
        is_ssl = False
    if scheme.lower() == "https":
        is_ssl = True
    else:
        raise exceptions.NotHttpSchemeError

    host = uri.host
    port = uri.port

    if not port:
        if is_ssl:
            port = 443
        else:
            port = 80

    request_target = uri.get_from_path()
    if not request_target:
        request_target = "/"

    message = RequestMessage(method=method, request_target=request_target, http_version="HTTP/1.1")

    message.headers = Headers(headers)

    if raw_body:
        if type(raw_body) != bytes:
            raise TypeError

        if "Content-Type" in message.headers:
            media_type = MediaType(message.headers["Content-Type"])
        else:
            media_type = None

        message.body = RequestBody(raw_body, media_type)
    else:
        message.body = None

    return message.send(host, port, is_ssl)


def get(url: str, headers: dict | None = None, body: bytes | None = None) -> Response | None:
    return send("GET", url, headers, body)


def post(url: str, headers: dict | None = None, body: bytes | None = None) -> Response | None:
    return send("POST", url, headers, body)


def put(url: str, headers: dict | None = None, body: bytes | None = None) -> Response | None:
    return send("PUT", url, headers, body)


def delete(url: str, headers: dict | None = None, body: bytes | None = None) -> Response | None:
    return send("DELETE", url, headers, body)


def patch(url: str, headers: dict | None = None, body: bytes | None = None) -> Response | None:
    return send("PATCH", url, headers, body)
