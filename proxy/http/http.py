import email
import io
import json
import urllib.parse
from cgi import FieldStorage
from collections.abc import Iterator, MutableMapping

from . import exceptions


class Headers(MutableMapping):
    """
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

    def __init__(self, data: bytes | list[tuple[str, str]]) -> None:
        fields: list[tuple[str, str]]
        if type(data) == bytes:
            message = email.message_from_string(data.decode("utf-8"))
            fields = message.items()
        elif type(data) == list:
            fields = data

        self.fields: dict[str, list] = {}
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
            del self.fields[key]

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


class Queries(MutableMapping):
    """
    >>> q = Queries("value=a&value=b&num=3")

    >>> q = Queries(
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

    def __init__(self, queries: str | dict) -> None:
        self.queries: dict[str, list]

        if type(queries) is dict:
            self.queries = queries
        elif type(queries) is str:
            self.queries = urllib.parse.parse_qs(queries)

    def __str__(self) -> str:
        return urllib.parse.urlencode(self.queries, doseq=True)

    def __conteins__(self, key: str) -> bool:
        if key in self.queries:
            return True

        return False

    def __getitem__(self, key: str | int) -> list[str]:
        if type(key) is int:
            key = str(key)

        for _key, values in self.queries.items():
            if _key == key:
                return values

        raise KeyError

    def __setitem__(self, key: str, values: str | list) -> None:
        if type(values) is str:
            values = [values]
        elif type(values) is int:
            values = [str(values)]

        self.queries[key] = list(values)

    def __delitem__(self, key: str) -> None:
        del self.queries[key]

    def __iter__(self) -> Iterator:
        seen = set()
        for key, _ in self.queries.items():
            if key not in seen:
                seen.add(key)
                yield key

    def __len__(self) -> int:
        return len(self.queries)


class RequestBody:
    pass


class RequestMessage:
    """
    RFC9112
    https://datatracker.ietf.org/doc/html/rfc9112
    """
    method: str
    http_version: str
    scheme: str
    netloc: str
    path: str
    queries: Queries
    fragment: str
    headers: Headers
    raw_body: bytes

    def __init__(self, msg: bytes):
        if b"\r\n" in msg:
            request_line, remained = msg.split(b"\r\n", 1)
        else:
            raise exceptions.NotHttp11RequestMessageError

        if b"\r\n\r\n" in remained:
            raw_header, raw_body = remained.split(b"\r\n\r\n", 1)
            self.raw_body = raw_body.strip()
        else:
            raw_header = remained.strip()
            self.raw_body = b""

        try:
            self.method, request_target, self.http_version = request_line.decode(
                "utf-8").split(" ")
        except ValueError:
            raise exceptions.NotHttp11RequestMessageError

        self.headers = Headers(raw_header)

        o = urllib.parse.urlparse(request_target)
        self.scheme = o.scheme
        self.netloc = o.netloc
        self.path = o.path
        self.queries = Queries(o.query)
        self.fragment = o.fragment

    def __bytes__(self) -> bytes:
        msg: bytes = self.get_request_line().encode("utf-8")
        msg += bytes(self.headers)
        msg += b"\r\n"
        msg += self.raw_body

        return msg

    def __str__(self) -> str:
        try:
            return self.__bytes__().decode("utf-8")
        except UnicodeDecodeError:
            msg: str = self.get_request_line()
            msg += str(self.headers)
            msg += "\r\n"
            msg += str(self.raw_body)[2:-1]
            return msg

    def get_origin_form(self) -> str:
        origin_form = "%s" % self.path
        if len(self.queries):
            origin_form += "?%s" % str(self.queries)
        if self.fragment:
            origin_form += "#%s" % self.fragment

        return origin_form

    def get_request_line(self) -> str:
        request_target = ""
        if self.scheme and self.netloc:
            request_target += "%s://%s" % (self.scheme, self.netloc)

        request_target += self.get_origin_form()

        request_line = "%s %s %s\r\n" % (
            self.method, request_target, self.http_version)

        return request_line

    def update_content_length(self) -> None:
        if "Contetn-Length" in self.headers:
            self.headers["Content-Length"] = str(len(self.raw_body))

    def parse_body(self) -> dict | None:
        try:
            content_type = self.headers["Content-Type"]
        except KeyError:
            content_type = None

        if len(self.raw_body) == 0:
            return None

        # application/json
        try:
            body_parameters = json.loads(self.raw_body)
            res = {}
            res["content-type"] = "application/json"
            res["data"] = body_parameters
            return res
        except json.JSONDecodeError:
            pass

        # application/x-www-form-urlencoded
        try:
            body_parameters = urllib.parse.parse_qs(self.raw_body)
            res = {}
            res["content-type"] = "application/x-www-form-urlencoded"
            res["data"] = body_parameters
            if len(body_parameters) > 0:
                return res
        except ValueError:
            pass

        if content_type and "multipart/form-data" in content_type.lower():
            environ = {"REQUEST_METHOD": "POST"}
            headers = {
                "content-type": content_type,
            }

            fp = io.BytesIO(self.raw_body)
            fs = FieldStorage(fp=fp, environ=environ, headers=headers)

            dic = {"content-type": content_type, "data": {}}

            if not fs.list:
                return None

            data = {}
            for f in fs.list:
                data[f.name] = f.value
            dic["data"] = data
            return dic

        return None


class ResponseMessage:
    """
    RFC9112
    https://datatracker.ietf.org/doc/html/rfc9112
    """

    http_version: str
    status_code: str
    status_message: str | None
    headers: Headers
    raw_body: bytes

    def __init__(self, msg: bytes) -> None:
        if b"\r\n" in msg:
            response_line, remained = msg.split(b"\r\n", 1)
        else:
            raise exceptions.NotHttp11ResponseMessageError

        if b"\r\n\r\n" in remained:
            raw_header, self.raw_body = remained.split(b"\r\n\r\n", 1)
        else:
            raw_header = remained.strip()
            self.raw_body = b""

        try:
            items = response_line.decode("utf-8").split(" ", 2)
        except ValueError:
            raise exceptions.NotHttp11RequestMessageError

        if len(items) == 3:
            self.http_version, self.status_code, self.status_message = items
        elif len(items) == 2:
            self.http_version, self.status_code = items

        self.headers = Headers(raw_header)

    def __bytes__(self) -> bytes:
        msg: bytes = self.get_status_line().encode("utf-8")
        msg += bytes(self.headers)
        msg += b"\r\n"
        msg += self.raw_body

        return msg

    def __str__(self) -> str:
        try:
            return self.__bytes__().decode("utf-8")
        except UnicodeDecodeError:
            msg: str = self.get_status_line()
            msg += str(self.headers)
            msg += "\r\n"
            msg += str(self.raw_body)[2:-1]
            return msg

    def get_status_line(self) -> str:
        status_line = " ".join((self.http_version, self.status_code))
        if self.status_message:
            status_line += " " + self.status_message
        status_line += "\r\n"

        return status_line
