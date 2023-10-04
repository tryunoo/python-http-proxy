import email
import io
import json
import urllib.parse
from cgi import FieldStorage
from collections.abc import Iterator, Mapping, MutableMapping
from typing import Any

from . import exceptions


class Query(MutableMapping):
    """
    RFC 3986: Uniform Resource Identifier (URI): Generic Syntax
                Section 3.4. Query
    https://datatracker.ietf.org/doc/html/rfc3986#section-3.4

    >>> q = Query("value=a&value=b&num=3")

    >>> q = Query(
            {'value': ['a', 'b'], 'num': ['3']}
        )

    >>> q
    value=a&value=b&num=3

    >>> q['value']
    ['a', 'b']

    >>> q['num'] = 1
    >>> q['test'] = ['A', 'B']
    >>> q
    value=a&value=b&num=1&test=A&test=B

    >>> del q['value']
    >>> q
    num=3
    """

    query: dict[str, list] = {}

    def __init__(self, query: str | dict) -> None:
        if type(query) is dict:
            self.query = query
        elif type(query) is str:
            self.query = urllib.parse.parse_qs(query, keep_blank_values=True)

    def __str__(self) -> str:
        return urllib.parse.urlencode(self.query, doseq=True)

    def __conteins__(self, key: str) -> bool:
        if key in self.query:
            return True

        return False

    def __getitem__(self, key: str | int) -> list[str]:
        if type(key) is int:
            key = str(key)

        for _key, values in self.query.items():
            if _key == key:
                return values

        raise KeyError

    def __setitem__(self, key: str, values: str | list) -> None:
        if type(values) is str:
            values = [values]
        elif type(values) is int:
            values = [str(values)]

        self.query[key] = list(values)

    def __delitem__(self, key: str) -> None:
        del self.query[key]

    def __iter__(self) -> Iterator:
        seen = set()
        for key, _ in self.query.items():
            if key not in seen:
                seen.add(key)
                yield key

    def __len__(self) -> int:
        return len(self.query)


class URI:
    r"""
    RFC 3986: Uniform Resource Identifier (URI): Generic Syntax
    https://datatracker.ietf.org/doc/html/rfc3986

     foo://example.com:8042/over/there?name=ferret#nose
     \_/   \______________/\_________/ \_________/ \__/
      |           |            |            |        |
   scheme     authority       path        query   fragment
      |   _____________________|__
     / \ /                        \
     urn:example:animal:ferret:nose

    relative-ref  = relative-part [ "?" query ] [ "#" fragment ]
    """

    scheme: str
    authority: str
    path: str
    query: Query
    fragment: str

    def __init__(self, uri: str) -> None:
        o = urllib.parse.urlparse(uri)
        self.scheme = o.scheme
        self.authority = o.netloc
        self.path = o.path
        self.query = Query(o.query)
        self.fragment = o.fragment

    def __str__(self) -> str:
        uri = ""
        if self.scheme and self.authority:
            uri += f"{self.scheme}://{self.authority}"

        uri += self.get_from_path()

        return uri

    def get_from_path(self) -> str:
        from_path = ""
        if self.path:
            from_path += self.path

        if len(self.query):
            from_path += f"?{str(self.query)}"
        if self.fragment:
            from_path += f"#{self.fragment}"
        return from_path


class RequestLine:
    """
    RFC 9112: HTTP/1.1
                Section 3. Request Line
    https://datatracker.ietf.org/doc/html/rfc9112#section-3

    request-line   = method SP request-target SP HTTP-version
    """

    scheme: str
    request_target: URI
    http_version: str

    def __init__(self, start_line: bytes | None = None, **kwargs: Any) -> None:
        if start_line is None:
            self.method = kwargs["method"]
            self.http_version = kwargs["http_version"]
            self.scheme = kwargs["request_target"]

            if "request_target" in kwargs:
                request_target = kwargs["request_target"]
                if type(request_target) is URI:
                    self.request_target = request_target
                else:
                    self.request_target = URI(request_target)
        else:
            try:
                self.method, request_target, self.http_version = start_line.decode(
                    "utf-8").split(" ")
            except ValueError:
                raise exceptions.NotHttp11RequestMessageError

            self.request_target = URI(request_target)

    def __str__(self) -> str:
        return f"{self.method} {self.request_target} {self.http_version}\r\n"


class StatusLine:
    def __init__(self, start_line: bytes) -> None:
        try:
            items = start_line.decode("utf-8").split(" ", 2)
        except ValueError:
            raise exceptions.NotHttp11RequestMessageError

        if len(items) == 3:
            self.http_version, self.status_code, self.status_message = items
        elif len(items) == 2:
            self.http_version, self.status_code = items
            self.status_message = None


class Headers(MutableMapping):
    """
    RFC 9112: HTTP/1.1
                Section 5. Field Syntax
    https://datatracker.ietf.org/doc/html/rfc9112#section-5

    >>> h = Headers(
            b"".join(
            [
                b"Host: example.com\r\n",
                b"Accept: text/html\r\n",
                b"accept: application/xml\r\n",
                b"Accept-Encoding: gzip, deflate\r\n",
                b"\r\n",
            ]
        )
    )

    >>> h = Headers([
        ("Host", "example.com"),
        ("Accept", "text/html"),
        ("accept", "application/xml"),
        ("Accept-Encoding", "gzip, deflate"),
    ])

    >>> h.get_fields()
    {'Host': ['example.com'], 'Accept': ['text/html', 'application/xml'], 'Accept-Encoding': ['gzip', 'deflate']}

    >>> h
    Host: example.com
    Accept: text/html, application/xml
    Accept-Encoding: gzip, deflate


    >>> bytes(h)
    b'Host: example.com\r\nAccept: text/html, application/xml\r\nAccept-Encoding: gzip, deflate\r\n'

    >>> h["Host"]
    'example.com'

    >>> h["host"]
    'example.com'

    >>> h["Accept"]
    'text/html, application/xml'

    >>> h.get_as_list("Accept")
    ["text/html", "application/xml"]

    >>> h["Accept"] = 'application/text'
    >>> h["Accept"]
    'application/text'

    >>> h["Accept"] = ["application/text", "application/json"]

    >>> del h["Accept"]
    >>> h
    Host: example.com
    Accept-Encoding: gzip, deflate
    """

    fields: dict[str, list]

    def __init__(self, data: bytes | list[tuple[str, str]]) -> None:
        fields: list[tuple[str, str]]
        if type(data) == bytes:
            message = email.message_from_string(data.decode("utf-8"))
            fields = message.items()
        elif type(data) == list:
            fields = data

        self.fields = {}
        for field in fields:
            key, value = field

            key = self.__conv_key(key)
            if key not in self.fields:
                self.fields[key] = []

            values = value.split(",")
            for value in values:
                self.fields[key].append(value.strip())

    def __repr__(self) -> str:
        return str(self.fields)

    def __conteins__(self, key: str) -> bool:
        key = self.__conv_key(key)

        return key in self.fields

    def __getitem__(self, key: str) -> str:
        key = self.__conv_key(key)

        values = self.fields[key]

        if len(values) == 0:
            raise KeyError
        else:
            return ", ".join(values)

    def __setitem__(self, key: str, values: str | list) -> None:
        key = self.__conv_key(key)
        if key in self.fields:
            if type(values) is str:
                values = values.split(",")
            self.fields[key] = list(values)
        else:
            self.add(key, values)

    def __delitem__(self, key: str) -> None:
        key = self.__conv_key(key)
        del self.fields[key]

    def __str__(self) -> str:
        if self.fields:
            return "\r\n".join("%s: %s" % (key, ", ".join(values)) for key, values in self.fields.items()) + "\r\n"
        else:
            return ""

    def __bytes__(self) -> bytes:
        return self.__str__().encode("utf-8")

    def __iter__(self) -> Iterator:
        seen = set()
        for key, _ in self.fields.items():
            key = self.__conv_key(key)
            if key not in seen:
                seen.add(key)
                yield key

    def __len__(self) -> int:
        return len(self.fields)

    def __conv_key(self, key: str) -> str:
        new_key = ""
        splitted = key.split("-")

        for i, s in enumerate(splitted, 1):
            new_key += s[0].upper()
            new_key += s[1:].lower()
            if i < len(splitted):
                new_key += "-"

        return new_key

    def get_fields(self) -> dict:
        return self.fields

    def add(self, key: str, values: str | list) -> None:
        if type(values) is str:
            values = values.split(",")

        key = self.__conv_key(key)
        if key not in self.fields:
            self.fields[key] = []

        for value in values:
            self.fields[key].append(value.strip())

    def get_as_list(self, key: str) -> list[str]:
        key = self.__conv_key(key)
        return self.fields[key]


class MediaType:
    """
    RFC 6838: Media Type Specifications and Registration Procedures
    https://datatracker.ietf.org/doc/html/rfc6838
    """

    type_: str
    subtype: str
    suffix: str
    parameter: str

    def __init__(self, media_type: str) -> None:
        if ";" in media_type:
            media_type, self.parameter = list(
                x.strip() for x in media_type.split(";", 1))

        if "/" in media_type:
            self.type_, self.subtype = media_type.split("/", 1)
        else:
            self.type_ = media_type
            self.subtype = ""

        if "+" in self.subtype:
            self.suffix = self.subtype.split("+", 1)[1]

    def __str__(self) -> str:
        media_type = self.get_main_section()
        if hasattr(self, "parameter"):
            media_type += f"; {self.parameter}"

        return media_type

    def get_main_section(self) -> str:
        if self.subtype:
            return f"{self.type_}/{self.subtype}"
        else:
            return self.type_


class Body:
    media_type: MediaType | None
    _raw_body: bytes

    def __init__(self, raw_body: bytes, media_type: MediaType | None = None) -> None:
        self._raw_body = raw_body
        self.media_type = media_type

    def __bytes__(self) -> bytes:
        return self._raw_body

    def __str__(self) -> str:
        return self._raw_body.decode("utf-8")

    def __len__(self) -> int:
        return len(self._raw_body)

    def set_body(self, raw_body: bytes, media_type: MediaType | None = None) -> None:
        self._raw_body = raw_body
        if media_type:
            self.media_type = media_type


class RequestBody(Body):
    def __init__(self, raw_body: bytes, media_type: MediaType | None = None) -> None:
        super().__init__(raw_body, media_type)

    def guess_media_type(self) -> MediaType | None:
        try:
            json.loads(self._raw_body)
            return MediaType("application/json")
        except json.JSONDecodeError:
            pass

        try:
            urllib.parse.parse_qs(self._raw_body, keep_blank_values=True)
            return MediaType("application/x-www-form-urlencoded")
        except ValueError:
            pass

        environ = {"REQUEST_METHOD": "POST"}
        headers: Mapping = {
            "content-type": self.media_type,
        }

        fp = io.BytesIO(self._raw_body)
        fs = FieldStorage(fp=fp, environ=environ, headers=headers)

        if fs.list:
            return MediaType("multipart/form-data")

        return None

    def parse(self, media_type: MediaType | None = None) -> dict | None:
        if len(self._raw_body) == 0:
            return None

        if not media_type:
            if self.media_type:
                media_type = self.media_type
            else:
                media_type = self.guess_media_type()

        if not media_type:
            return None

        if media_type.subtype == "json" or (hasattr(media_type, "suffix") and media_type.suffix == "json"):
            try:
                body_parameters = json.loads(self._raw_body)
                return dict(body_parameters)
            except json.JSONDecodeError:
                pass

        if media_type.subtype == "x-www-form-urlencoded":
            try:
                body_parameters = urllib.parse.parse_qs(
                    self._raw_body, keep_blank_values=True)
                res = body_parameters
                if len(body_parameters) > 0:
                    return dict(res)
            except ValueError:
                pass

        if media_type.subtype == "form-data":
            """
            RFC 7578: Returning Values from Forms: multipart/form-data
            https://datatracker.ietf.org/doc/html/rfc7578
            """
            environ = {"REQUEST_METHOD": "POST"}
            headers: Mapping = {
                "content-type": str(self.media_type),
            }

            fp = io.BytesIO(self._raw_body)
            fs = FieldStorage(fp=fp, environ=environ, headers=headers)

            if not fs.list:
                return None

            data = {}
            for f in fs.list:
                data[f.name] = f.value
            return data

        return None


class ResponseBody(Body):
    def __init__(self, raw_body: bytes, media_type: MediaType | None = None) -> None:
        super().__init__(raw_body, media_type)


class RequestMessage:
    """
    RFC 9112: HTTP/1.1
    https://datatracker.ietf.org/doc/html/rfc9112

    HTTP-message = start-line CRLF
                 *( field-line CRLF )
                 CRLF
                 [ message-body ]
    start-line = request-line / status-line

    request-line = method SP request-target SP HTTP-version
    """

    method: str
    http_version: str
    request_target: URI
    headers: Headers
    body: RequestBody

    def __init__(self, msg: bytes):
        if b"\r\n" in msg:
            start_line, remained = msg.split(b"\r\n", 1)
        else:
            raise exceptions.NotHttp11RequestMessageError

        request_line = RequestLine(start_line)

        if b"\r\n\r\n" in remained:
            raw_header, raw_body = remained.split(b"\r\n\r\n", 1)
        else:
            raw_header = remained.strip()
            raw_body = b""

        self.method = request_line.method
        self.http_version = request_line.http_version
        self.request_target = request_line.request_target
        del request_line

        self.headers = Headers(raw_header)
        if "Content-Type" in self.headers:
            media_type = MediaType(self.headers["Content-Type"])
        else:
            media_type = None

        self.body = RequestBody(raw_body, media_type)

    def __bytes__(self) -> bytes:
        msg: bytes = self.get_request_line().encode("utf-8")
        msg += bytes(self.headers)
        msg += b"\r\n"
        msg += bytes(self.body)

        return msg

    def __str__(self) -> str:
        try:
            return self.__bytes__().decode("utf-8")
        except UnicodeDecodeError:
            msg: str = self.get_request_line()
            msg += str(self.headers)
            msg += "\r\n"
            msg += str(self.body)[2:-1]
            return msg

    def get_request_line(self) -> str:
        request_line = RequestLine(
            method=self.method, request_target=self.request_target, http_version=self.http_version
        )

        return str(request_line)

    def update_content_length(self) -> None:
        if "Content-Length" in self.headers:
            self.headers["Content-Length"] = str(len(self.body))

    def set_headers(self, raw_header: bytes) -> None:
        self.headers = Headers(raw_header)

    def set_body(self, raw_body: bytes) -> None:
        self.body = RequestBody(raw_body)


class ResponseMessage:
    """
    RFC 9112: HTTP/1.1
    https://datatracker.ietf.org/doc/html/rfc9112

    HTTP-message = start-line CRLF
             *( field-line CRLF )
             CRLF
             [ message-body ]
    start-line = request-line / status-line

    status-line = HTTP-version SP status-code SP [ reason-phrase ]
    """

    http_version: str
    status_code: str
    status_message: str | None
    headers: Headers
    body: ResponseBody

    def __init__(self, msg: bytes) -> None:
        if b"\r\n" in msg:
            start_line, remained = msg.split(b"\r\n", 1)
        else:
            raise exceptions.NotHttp11ResponseMessageError()

        if b"\r\n\r\n" in remained:
            raw_header, raw_body = remained.split(b"\r\n\r\n", 1)
        else:
            raw_header = remained.strip()
            raw_body = b""

        status_line = StatusLine(start_line)

        self.http_version = status_line.http_version
        self.status_code = status_line.status_code
        self.status_message = status_line.status_message
        del status_line

        self.headers = Headers(raw_header)
        self.body = ResponseBody(raw_body)

    def __bytes__(self) -> bytes:
        msg: bytes = self.get_status_line().encode("utf-8")
        msg += bytes(self.headers)
        msg += b"\r\n"
        msg += bytes(self.body)

        return msg

    def __str__(self) -> str:
        try:
            return self.__bytes__().decode("utf-8")
        except UnicodeDecodeError:
            msg: str = self.get_status_line()
            msg += str(self.headers)
            msg += "\r\n"
            msg += str(self.body)[2:-1]
            return msg

    def __len__(self) -> int:
        return len(self.__bytes__())

    def get_status_line(self) -> str:
        status_line = " ".join((self.http_version, self.status_code))
        if self.status_message:
            status_line += " " + self.status_message
        status_line += "\r\n"

        return status_line

    def set_headers(self, raw_header: bytes) -> None:
        self.headers = Headers(raw_header)

    def set_body(self, raw_body: bytes) -> None:
        self.body = ResponseBody(raw_body)
