from urllib import request
from httpprocess import HttpProcess
from request import HttpRequest, HttpResponse
import datetime
import socket
import time

def recv_all(s):
    buf_size = 32768
    data = b''

    while True:
        try:
            recv_data = s.recv(buf_size)
            data += recv_data
            if len(recv_data) < buf_size:
                break

        except socket.timeout:
            break
        
    return data


def recv_line(s):
    data = b''

    while True:
        recv_data = s.recv(1)
        data += recv_data
        if recv_data == b'\n':
            break
    
    return data


def send_http_request(s, req: HttpRequest):
    hp = HttpProcess()
    
    req = hp.process_request(req)

    req.send_time = datetime.datetime.now()
    
    raw_request = req.get_raw_request()
    
    s.sendall(raw_request)

    return len(raw_request)


def recv_http_header(s):
    data = b''
    
    while True:
        recv_data = recv_line(s)

        data += recv_data
        if recv_data == b'\r\n' or recv_data == b'\n':
            break
    
    return data


def recv_http_body(s, headers):
    raw_body = b''
    body_len = 0

    if 'Content-Length' in headers:
        content_length = int(headers['Content-Length'])-1

        while True:
            if body_len >= content_length:
                break
            data = recv_all(s)
            raw_body += data
            body_len += len(data)
    elif 'Transfer-Encoding' in headers and headers['Transfer-Encoding'] == 'chunked':
        while True:
            data = recv_all(s)
            raw_body += data
            body_len += len(data)
            if data.endswith(b'0\r\n\r\n'):
                break
    elif 'transfer-encoding' in headers and headers['transfer-encoding'] == 'chunked':
        while True:
            data = recv_all(s)
            raw_body += data
            body_len += len(data)
            if data.endswith(b'0\r\n\r\n'):
                break
    elif 'Content-Type' in headers:
        s.settimeout(3)
        data = recv_all(s)
        raw_body += data
        body_len += len(data)

    return raw_body


def recv_http_request(s):
    req = HttpRequest()

    raw_header = recv_http_header(s)
    req.set_header(raw_header)

    raw_body = recv_http_body(s, req.headers)
    req.set_body(raw_body)

    return req


def recv_http_response(s, req):
    start_time = time.perf_counter()
    
    raw_header = recv_http_header(s)

    res = HttpResponse()
    res.set_header(raw_header)

    raw_body = recv_http_body(s, res.headers)
    res.set_body(raw_body)

    end_time = time.perf_counter()
            
    res.round_trip_time = round(end_time - start_time, 3)

    hp = HttpProcess()
    res = hp.process_response(req, res)
    
    return res




