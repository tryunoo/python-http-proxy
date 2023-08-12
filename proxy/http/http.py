import email
import io
import json
import urllib
from cgi import FieldStorage
from collections.abc import Iterator
from collections.abc import MutableMapping
from proxy import exceptions


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
    [('Host', 'example.com'), ('Accept', 'text/html'), ('accept', 'application/xml'),
        ('Accept-Encoding', 'gzip, deflate')]

    >>> h
    Host: example.com
    Accept: text/html
    accept: application/xml
    Accept-Encoding: gzip, deflate

    >>> bytes(h)
    b'Host: example.com\r\nAccept: text/html\r\naccept: application/xml\r\nAccept-Encoding: gzip, deflate\r\n'

    >>> h["Host"]
    "example.com"

    >>> h["host"]
    "example.com"

    >>> h["Accept"]
    ["text/html", "application/xml"]

    >>> h["Accept"] = "application/text"
    >>> h["Accept"]
    "application/text"

    >>> h["Accept"] = ["application/text", "application/json"]

    >>> del headers['Accept']
    >>> h
    Host: example.com
    Accept-Encoding: gzip, deflate
    """

    def __init__(self, fields: bytes | list[tuple[str, str]]) -> None:
        if type(fields) == list:
            self.fields = fields
        elif type(fields) == bytes:
            message = email.message_from_string(fields.decode("utf-8"))
            self.fields = message.items()

    def __repr__(self) -> str:
        return str(self.fields)

    def __conteins__(self, key: str) -> bool:
        key_lower = key.lower()
        for field in self.fields:
            if field[0].lower() == key_lower:
                return True

        return False

    def __getitem__(self, key: str | int) -> str | list:
        if type(key) is int:
            key = str(key)

        values = []
        key_lower = key.lower()
        for field in self.fields:
            if field[0].lower() == key_lower:
                values.append(field[1])

        if len(values) == 0:
            raise KeyError
        elif len(values) == 1:
            return values[0]
        else:
            return values

    def __setitem__(self, key: str | int, values: str | list) -> None:
        if type(values) is str:
            values = [values]
        if type(values) is int:
            values = [str(values)]
        if type(key) is int:
            key = str(key)

        key_lower = key.lower()
        for i, field in enumerate(self.fields):
            if values and field[0].lower() == key_lower:
                self.fields[i] = (key, values.pop(0))
            elif field[0].lower() == key_lower:
                self.fields[i] = None

        while None in self.fields:
            self.fields.remove(None)

        while values:
            self.fields.append((key, values.pop(0)))

    def __delitem__(self, key: str):
        key_lower = key.lower()

        for i, field in enumerate(self.fields):
            if field[0].lower() == key_lower:
                self.fields[i] = None

        while None in self.fields:
            self.fields.remove(None)

    def __str__(self) -> str:
        if self.fields:
            return "\r\n".join(": ".join(field) for field in self.fields) + "\r\n"
        else:
            return ""

    def __bytes__(self) -> bytes:
        return self.__str__().encode('utf-8')

    def __iter__(self) -> Iterator:
        seen = set()
        for key, _ in self.fields:
            lower_key = key.lower()
            if lower_key not in seen:
                seen.add(lower_key)
                yield key

    def __len__(self) -> int:
        return len(self.fields)

    def get_fields(self) -> list:
        return self.fields

    def add(self, key: str, value: str):
        self.fields.append((key, value))

    def insert(self, index: int, key: str, value: str):
        self.fields.insert(index, (key, value))

    def keys(self) -> tuple:
        return tuple(field[0] for field in self.fields)


class Query(MutableMapping):
    """
    >>> q = Query("value=a&value=b&num=3")

    >>> q = Query(
            {'value': ['a', 'b'], 'num': ['3']}
        )

    >>> q
    value=a&value=b&num=3

    >>> q['num'] = 1
    >>> q['test'] = ['A', 'B']
    >>> q
    value=a&value=b&num=1&test=A&test=B

    >>> del q['value']
    >>> q
    num=3
    """

    def __init__(self, queries: str | dict):
        if type(queries) is dict:
            self.queries = queries
        elif type(queries) is str:
            self.queries = urllib.parse.parse_qs(queries)

    def __str__(self):
        return "&".join("&".join(("%s=%s" % (key, value)) for value in values) for key, values in self.queries.items())

    def __conteins__(self, key) -> bool:
        if key in self.queries:
            return True

        return False

    def __getitem__(self, key: str | int) -> str | list:
        if type(key) is int:
            key = str(key)

        for _key, values in self.queries.items():
            if _key == key:
                return values

    def __setitem__(self, key: str, values: str | list) -> None:
        if type(values) is str:
            values = [values]
        if type(values) is int:
            values = [str(values)]

        self.queries[key] = values

    def __delitem__(self, key: str):
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
            self.raw_body = b''

        self.method, request_target, self.http_version = request_line.decode(
            "utf-8").split(" ")

        self.headers = Headers(raw_header)

        o = urllib.parse.urlparse(request_target)
        self.scheme = o.scheme
        self.netloc = o.netloc
        self.path = o.path
        self.queries = Query(o.query)
        self.fragment = o.fragment

    def __bytes__(self) -> bytes:
        msg = self.get_request_line().encode("utf-8")
        msg += bytes(self.headers)
        msg += b"\r\n"
        msg += self.raw_body

        return msg

    def __str__(self) -> str:
        try:
            return self.__bytes__().decode('utf-8')
        except UnicodeDecodeError:
            msg = self.get_request_line()
            msg += str(self.headers)
            msg += '\r\n'
            msg += str(self.raw_body)[2:-1]
            return msg

    def get_origin_form(self):
        origin_form = "%s" % self.path
        if len(self.queries):
            origin_form += "%s" % str(self.queries)
        if self.fragment:
            origin_form += "#%s" % self.fragment

        return origin_form

    def get_request_line(self):
        request_target = ""
        if self.scheme and self.netloc:
            request_target += "%s://%s" % (self.scheme, self.netloc)

        request_target += self.get_origin_form()

        request_line = "%s %s %s\r\n" % (
            self.method, request_target, self.http_version)

        return request_line

    def update_content_length(self) -> bool:
        if 'Contetn-Length' in self.headers:
            self.headers["Content-Length"] = str(len(self.raw_body))

    def parse_body(self) -> dict | None:
        try:
            content_type = self.headers['Content-Type']
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

    def __init__(self, msg: bytes):
        if b"\r\n" in msg:
            response_line, remained = msg.split(b"\r\n", 1)
        else:
            raise exceptions.NotHttp11ResponseMessageError

        if b"\r\n\r\n" in remained:
            raw_header, self.raw_body = remained.split(b"\r\n\r\n", 1)
        else:
            raw_header = remained.strip()
            self.raw_body = b''

        items = response_line.decode('utf-8').split(" ", 2)
        if len(items) == 3:
            self.http_version, self.status_code, self.status_message = items
        elif len(items) == 2:
            self.http_version, self.status_code = items
            self.status_message = None

        self.headers = Headers(raw_header)

    def __bytes__(self) -> bytes:
        msg = self.get_status_line().encode("utf-8")
        msg += bytes(self.headers)
        msg += b"\r\n"
        msg += self.raw_body

        return msg

    def __str__(self) -> str:
        try:
            return self.__bytes__().decode('utf-8')
        except UnicodeDecodeError:
            msg = self.get_status_line()
            msg += str(self.headers)
            msg += '\r\n'
            msg += str(self.raw_body)[2:-1]
            return msg

    def get_status_line(self):
        status_line = ' '.join((self.http_version, self.status_code))
        if self.status_message:
            status_line += ' ' + self.status_message
        status_line += '\r\n'

        return status_line
