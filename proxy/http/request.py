from datetime import datetime
from typing import Optional

from dateutil import tz  # type: ignore

from . import encoding, util
from .http import URI, RequestMessage, ResponseMessage
from .httpprocess import HttpProcess
from .tube import Tube

TIME_ZONE = "Asia/Tokyo"


class Request:
    request_time: float | None
    response: "Response"

    def __init__(self, host: str, port: int, is_ssl: bool, message: RequestMessage) -> None:
        self.host = host
        self.port = port
        self.is_ssl = is_ssl
        self.message = message

    def get_scheme(self) -> str:
        return "https" if self.is_ssl else "http"

    def get_uri(self) -> URI:
        uri = "%s://%s:%s%s" % (self.get_scheme(), self.host, self.port, self.message.request_target.get_from_path())
        return URI(uri)

    # http2への対応
    def alter_request_line(self) -> bool:
        if self.message.http_version == "HTTP/2":
            self.message.http_version = "HTTP/1.1"
        if "Host" not in self.message.headers:
            self.message.headers.add("Host", self.host)

        return True

    def send(self) -> Optional["Response"]:
        hp = HttpProcess()
        hp.process_request(self)

        self.message.update_content_length()
        self.alter_request_line()

        raw_request = bytes(self.message)
        tube = Tube()
        tube.open_connection(self.host, self.port, self.is_ssl)

        self.request_time = datetime.now(tz.gettz(TIME_ZONE)).timestamp()
        tube.send(raw_request)

        try:
            raw_response = tube.recv_raw_http_response()
        except TimeoutError:
            return None

        response_time = datetime.now(tz.gettz(TIME_ZONE)).timestamp()
        response_message = ResponseMessage(raw_response)

        # chunkedされているボディを変換
        if "Transfer-Encoding" in response_message.headers:
            if response_message.headers["Transfer-Encoding"] == "chunked":
                raw_body = util.chunked_conv(bytes(response_message.body))
                response_message.set_body(raw_body)
                del response_message.headers["Transfer-Encoding"]

        # エンコーディングされているボディをデコード
        if "Content-Encoding" in response_message.headers:
            content_encoding = response_message.headers["Content-Encoding"]
            raw_body = encoding.decode(bytes(response_message.body), content_encoding)
            response_message.set_body(raw_body)
            response_message.headers["Content-Length"] = str(len(response_message.body))
            del response_message.headers["Content-Encoding"]

        response = Response(self, response_time, response_message)

        hp.process_response(response)

        return response


class Response:
    def __init__(self, request: Request, response_time: float, message: ResponseMessage):
        self.response_time = response_time
        self.message = message
        self.request = request
        request.response = self

    def set_response_time(self, response_time: float) -> None:
        self.response_time = response_time

    def set_request_object(self, request_object: Request) -> None:
        self.request = request_object

    def get_roundtrip_time(self) -> float | None:
        if not self.request or not self.request.request_time or not self.response_time:
            return None

        roundtrip_time_timedelta = self.response_time - self.request.request_time
        return roundtrip_time_timedelta
