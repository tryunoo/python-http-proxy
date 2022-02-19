from httpprocess import HttpProcess
from request import HttpRequest, HttpResponse
import datetime
import socket
import time

def recv_all(s):
    buf_size = 65536
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


def send_http_request(s, req: HttpRequest):
    hp = HttpProcess()
    
    req = hp.process_request(req)

    req.send_time = datetime.datetime.now()
    
    raw_request = req.get_raw_request()
    s.sendall(raw_request)

    return len(raw_request)


def recv_http_response(s, req):
    start_time = time.perf_counter()

    data = recv_all(s)

    res = HttpResponse(data)

    if 'Content-Length' in res.headers:
        content_length = int(res.headers['Content-Length'])

        while True:
            if len(res.raw_body) >= content_length:
                break

            data = recv_all(s)
            res.raw_body += data
            res.res_len += len(data)
    
    elif 'Transfer-Encoding' in res.headers and res.headers['Transfer-Encoding'] == 'chunked':
        while True:
            if data.endswith(b'0\r\n\r\n'):
                break

            data = recv_all(s)
            res.raw_body += data
            res.res_len += len(data)
    elif 'transfer-encoding' in res.headers and res.headers['transfer-encoding'] == 'chunked':
        while True:
            if data.endswith(b'0\r\n\r\n'):
                break

            data = recv_all(s)
            res.raw_body += data
            res.res_len += len(data)

    end_time = time.perf_counter()
            
    res.round_trip_time = round(end_time - start_time, 3)

    hp = HttpProcess()
    res = hp.process_response(req, res)
    
    return res




