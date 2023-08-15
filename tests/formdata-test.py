import asyncio
from os.path import dirname, abspath
import sys
import copy

parent_dir = dirname(dirname(abspath(__file__)))
sys.path.append(parent_dir)
from proxy.http.http import RequestMessage, ResponseMessage, Headers, Query, MediaType, RequestLine
from proxy.http.request import Request, Response

raw_request = b"POST /test HTTP/1.1\r\n"
raw_request += b"Host: example.com\r\n"
raw_request += b"Accept-Encoding: gzip, deflate\r\n"
raw_request += b"Content-Type: multipart/form-data; boundary=---------------------------14244793736193916001666453247\r\n"
raw_request += b"Content-Length: 729\r\n"
raw_request += b"\r\n"
raw_request += b"\r\n"
raw_request += b'-----------------------------14244793736193916001666453247\r\n'
raw_request += b'Content-Disposition: form-data; name="impressionId"\r\n'
raw_request += b'\r\n'
raw_request += b'initial_load_attempt\r\n'
raw_request += b'-----------------------------14244793736193916001666453247\r\n'
raw_request += b'Content-Disposition: form-data; name="customData"\r\n'
raw_request += b'\r\n'
raw_request += b'{"mct":2,"nt":0,"gapi_version":null,"chat_no_gmail_storage":false}\r\n'
raw_request += b'-----------------------------14244793736193916001666453247\r\n'
raw_request += b'Content-Disposition: form-data; name="defaultData"\r\n'
raw_request += b'\r\n'
raw_request += b'{"inbox_type":"SECTIONED","hub_configuration":3,"delegation_request":false,"customer_type":"CONSUMER","browser":"FIREFOX","gapi_version":null,"compile_mode":"","is_cached_html":false,"build_label":"gmail.pinto-server_20230806.06_p1"}\r\n'
raw_request += b'-----------------------------14244793736193916001666453247--\r\n'


async def main():
    request_message = RequestMessage(raw_request)

    host = 'login.yahoo.co.jp'
    port = 443
    is_ssl = True
    request = Request(host, port, is_ssl, message=request_message)

    rl = request_message.body.media_type
    print(rl)

asyncio.run(main())
