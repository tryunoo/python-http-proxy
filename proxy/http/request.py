from datetime import datetime
from typing import Optional
from dateutil import tz  # type: ignore
from proxy.http.http import RequestMessage, ResponseMessage
from proxy.http.tube import Tube
from proxy.http import util
from proxy.http import encoding
from proxy.http.httpprocess import HttpProcess

TIME_ZONE = "Asia/Tokyo"


class Request:
    request_time: float | None = None
    response = None

    def __init__(self, host, port, is_ssl, message: RequestMessage = None) -> None:
        self.host = host
        self.port = port
        self.is_ssl = is_ssl

        if is_ssl:
            self.scheme = "https"
        else:
            self.scheme = "http"

        self.message = message
        self.url = '%s://%s:%s%s' % (self.scheme, self.host, self.port, self.message.get_origin_form())

    # http2への対応
    def alter_request_line(self) -> bool:
        if self.message.http_version == "HTTP/2":
            self.message.http_version = "HTTP/1.1"
        if 'Host' not in self.message.headers:
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
        raw_response = tube.send_recv(raw_request)

        if not raw_response:
            return None

        response_time = datetime.now(tz.gettz(TIME_ZONE)).timestamp()
        response_message = ResponseMessage(raw_response)

        # chunkedされているボディを変換
        if 'Transfer-Encoding' in response_message.headers:
            if response_message.headers['Transfer-Encoding'] == 'chunked':
                response_message.raw_body = util.chunked_conv(response_message.raw_body)
                del response_message.headers['Transfer-Encoding']

        # エンコーディングされているボディをデコード
        if 'Content-Encoding' in response_message.headers:
            content_encoding = response_message.headers['Content-Encoding']
            response_message.raw_body = encoding.decode(response_message.raw_body, content_encoding)
            response_message.headers['Content-Length'] = str(len(response_message.raw_body))
            del response_message.headers['Content-Encoding']

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