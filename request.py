"""
リクエスト、レスポンスオブジェクト
"""
import email
import io
import json
import re
import string
import urllib
import tube
from cgi import FieldStorage
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from dateutil import tz  # type: ignore
from httpprocess import HttpProcess

TIME_ZONE = "Asia/Tokyo"

class HttpRequest:
    """
    リクエストオブジェクト
    """

    request_time: float | None = None
    response_object = None

    def __init__(self, raw_request: bytes, host: str | None = None, port: int | None = None, is_ssl: bool | None = None):
        self.host = host
        self.port = port
        self.is_ssl = is_ssl

        if is_ssl is None:
            self.scheme = None
        elif is_ssl:
            self.scheme = "https"
        else:
            self.scheme = "http"

        if b"\r\n" in raw_request:
            self.__raw_request_line, remained = raw_request.split(b"\r\n", 1)
        else:
            raise ValueError("")

        if b"\r\n\r\n" in remained:
            raw_header, raw_body = remained.split(b"\r\n\r\n", 1)
            self.__raw_header = raw_header.strip()
            self.__raw_body = raw_body
        else:
            self.__raw_header = remained.strip()
            self.__raw_body = b""


    def get_raw_request(self) -> bytes:
        return b"%s\r\n%s\r\n\r\n%s" % (self.__raw_request_line, self.__raw_header, self.__raw_body)

    def set_host(self, host: str) -> bool:
        self.host = host
        return True

    def set_port(self, port: int) -> bool:
        self.port = port
        return True

    def set_is_ssl(self, is_ssl: bool) -> bool:
        self.is_ssl = is_ssl
        if is_ssl:
            self.scheme = "https"
        else:
            self.scheme = "http"

        return True

    def set_request_time(self, request_time: float) -> bool:
        self.request_time = request_time
        return True

    def set_response_object(self, response_object: "HttpResponse") -> bool:
        self.response_object = response_object
        return True

    def get_target_from_raw_request(self) -> str | None:
        host, port = None, None
        request_uri = self.get_request_uri()
        if not request_uri:
            return None

        o = urllib.parse.urlparse(request_uri)
        netloc = o.netloc

        if not netloc:
            netloc = o.scheme

        if netloc:
            target = netloc
            if '@' in netloc:
                target = netloc.split('@')[1]

            if ':' in target:
                host, port = target.split(':')
                port = int(port)
            else:
                host = target
                if self.scheme == 'http':
                    port = 80
                elif self.scheme == 'https':
                    port = 443
        else:
            header = self.get_header()
            if header:
                header_keys = " ".join(header.keys())
                res = re.search(r" host ", header_keys, re.IGNORECASE)

                if res:
                    key = res.group().strip()
                    host = self.headers[key]

        return host, port


    def get_raw_request_line(self) -> bytes:
        return self.__raw_request_line

    def get_raw_header(self) -> bytes:
        return self.__raw_header

    def get_raw_body(self) -> bytes:
        return self.__raw_body

    def get_url(self) -> str | None:
        request_uri = self.get_request_uri()
        if not request_uri:
            return None

        o = urllib.parse.urlparse(request_uri)

        if not self.scheme:
            return None

        res = o._replace(
            scheme=self.scheme,
            netloc="%s:%s" % (self.host, self.port),
        )

        return res.geturl()

    def get_request_line(self) -> list[str] | None:
        if not self.__raw_header:
            return None

        request_line = self.__raw_request_line.decode("utf-8").split(" ")

        if len(request_line) != 3:
            return None

        return request_line

    def get_method(self) -> str | None:
        request_line = self.get_request_line()

        if not request_line:
            return None

        return request_line[0]

    def get_request_uri(self) -> str | None:
        request_line = self.get_request_line()

        if not request_line:
            return 

        uri = request_line[1]
        if not request_line[1].startswith('http://') or request_line[1].startswith('https://'):
            uri = '%s://%s' % (self.scheme, request_line[1])

        return uri

    def get_http_version(self) -> str | None:
        request_line = self.get_request_line()

        if not request_line:
            return None

        return request_line[2]

    def get_url_path(self) -> str | None:
        request_uri = self.get_request_uri()
        if not request_uri:
            return None

        o = urllib.parse.urlparse(request_uri)
        url_path = o.path

        return url_path

    def get_url_queries(self) -> dict | None:
        request_uri = self.get_request_uri()
        if not request_uri:
            return None

        o = urllib.parse.urlparse(request_uri)
        query_strings = o.query

        return urllib.parse.parse_qs(query_strings)

    def get_header(self) -> dict | None:
        message = email.message_from_string(self.__raw_header.decode("utf-8"))
        header = dict(message.items())

        return header

    def set_queries(self, queries: dict) -> bool | None:
        query_strings = urllib.parse.urlencode(queries, doseq=True, safe=string.punctuation)

        request_uri = self.get_request_uri()
        if not request_uri:
            return None

        o = urllib.parse.urlparse(request_uri)
        res = o._replace(query=query_strings)
        new_request_uri = res.geturl()

        method = self.get_method()
        http_version = self.get_http_version()

        self.__raw_request_line = ("%s %s %s" % (method, new_request_uri, http_version)).encode("utf-8")

        return True

    def get_content_type(self) -> str | None:
        header = self.get_header()
        if not header:
            return None
        header_keys = " ".join(header.keys())
        res = re.search(r" content-type ", header_keys, re.IGNORECASE)

        if not res:
            return None

        content_type_name = res.group().strip()
        content_type = header[content_type_name]

        return str(content_type)

    def set_header(self, headers: dict) -> bool:
        if type(headers) != dict:
            return False

        self.__raw_header = "\r\n".join(["%s: %s" % (name, value) for (name, value) in headers.items()]).encode(
            "utf-8"
        )

        return True

    def add_header(self, key: str, value: str) -> bool:
        headers = self.get_header()
        if not headers:
            headers = {}
        headers[key] = value
        self.__raw_header = "\r\n".join(["%s: %s" % (name, value) for (name, value) in headers.items()]).encode(
            "utf-8"
        )

        return True

    def alter_query_value(self, name: str, value: str) -> bool:
        queries = self.get_url_queries()

        if not queries:
            return False
        if name not in queries:
            return False

        queries[name] = value

        self.set_queries(queries)

        return True

    def alter_header_value(self, name: str, value: str) -> bool:
        header = self.get_header()

        if not header:
            return False
        if name not in header:
            return False

        header[name] = value
        self.set_header(header)

        return True

    def set_content_length(self) -> bool:
        header = self.get_header()
        raw_body = self.get_raw_body()

        if len(raw_body) == 0:
            return False

        if not header:
            header = {"Content-Length": len(raw_body)}
        else:
            header_keys = " ".join(header.keys())
            res = re.search(r" content-length ", header_keys, re.IGNORECASE)

            if res:
                key = res.group().strip()
                header[key] = len(raw_body)
            else:
                header["Content-Length"] = len(raw_body)

        self.set_header(header)

        return True

    def set_http_version(self, http_version: str) -> bool:
        request_line = self.get_request_line()
        if not request_line:
            return False

        method, request_uri, _ = request_line
        self.__raw_request_line = ("%s %s %s" % (method, request_uri, http_version)).encode("utf-8")
        return True

    def send(self) -> Optional["HttpResponse"]:
        hp = HttpProcess()
        hp.process_request(self)

        self.set_content_length()

        raw_request = self.get_raw_request()
        retry = 3
        for x in range(retry):
            _ = x
            self.request_time = datetime.now(tz.gettz(TIME_ZONE)).timestamp()
            raw_response = tube.send_recv(self.host, self.port, self.is_ssl, raw_request)
            if raw_response:
                break
            print("retring...")

        if not raw_response:
            return None

        response_time = datetime.now(tz.gettz(TIME_ZONE)).timestamp()
        response_object = HttpResponse(self, raw_response, response_time)

        hp.process_response(response_object)

        return response_object

    def parse_body(self) -> dict | None:
        raw_body = self.__raw_body
        content_type = self.get_content_type()

        if len(raw_body) == 0:
            return None

        # application/json
        try:
            body_parameters = json.loads(raw_body)
            res = {}
            res["content-type"] = "application/json"
            res["data"] = body_parameters
            return res
        except json.JSONDecodeError:
            pass

        # application/x-www-form-urlencoded
        try:
            body_parameters = urllib.parse.parse_qs(raw_body)
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

            fp = io.BytesIO(raw_body)
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


@dataclass
class HttpResponse:
    request_object: HttpRequest | None = None
    response_time: float | None = None
    http_version: str | None = None
    status_code: str | None = None
    raw_header: bytes | None = None
    raw_body: bytes | None = None
    headers: dict | None = None
    body_len: int = 0
    res_len: int = 0

    def __init__(self, request_object: HttpRequest, raw_response: bytes, response_time: float):
        if b"\r\n\r\n" in raw_response:
            self.raw_header, self.raw_body = raw_response.split(b"\r\n\r\n", 1)
            self.body_len = len(self.raw_body)
        else:
            self.raw_header = raw_response.strip()

        self.res_len = len(self.raw_header)
        response_line, headers = self.raw_header.decode("utf-8").split("\r\n", 1)

        message = email.message_from_file(io.StringIO(headers))
        self.headers = dict(message.items())

        try:
            self.http_version, self.status_code, _ = response_line.split(" ", 2)
        except ValueError:
            self.http_version, self.status_code = response_line.split(" ", 2)

        self.response_time = response_time
        self.request_object = request_object
        request_object.set_response_object(self)

    def set_response_time(self, response_time: float) -> None:
        self.response_time = response_time

    def set_request_object(self, request_object: HttpRequest) -> None:
        self.request_object = request_object

    def get_roundtrip_time(self) -> float | None:
        if not self.request_object or not self.request_object.request_time or not self.response_time:
            return None

        roundtrip_time_timedelta = self.response_time - self.request_object.request_time
        return roundtrip_time_timedelta

    def get_raw_response(self) -> bytes:
        if not self.raw_header:
            return b""
        if not self.raw_body:
            return self.raw_header + b"\r\n\r\n"

        raw_response = self.raw_header + b"\r\n\r\n" + self.raw_body
        return raw_response
