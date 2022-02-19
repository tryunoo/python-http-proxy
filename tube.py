from httpprocess import HttpProcess
from request import HttpRequest, HttpResponse
import socket


def recv_all(s):
    buf_size = 65536
    data = b''

    while True:
        try:
            recv_data = s.recv(buf_size)
            data += recv_data
            if len(recv_data) < buf_size:
                break
            else:
                s.settimeout(1)
        except socket.timeout:
            break

    s.settimeout(10)
        
    return data


def send_http_request(s, req: HttpRequest):
    hp = HttpProcess()
    
    req = hp.process_request(req)
    
    raw_request = req.get_raw_request()
    s.sendall(raw_request)

    return len(raw_request)


def recv_http_response(s):
    data = recv_all(s)

    res = HttpResponse(data)

    if 'Content-Length' in res.headers:
        content_length = int(res.headers['Content-Length'])

        while True:
            if len(res.raw_body) >= content_length:
                break

            data = recv_all(s)
            res.raw_body += data
    
    elif 'Transfer-Encoding' in res.headers and res.headers['Transfer-Encoding'] == 'chunked':
        while True:
            if data.endswith(b'0\r\n\r\n'):
                break

            data = recv_all(s)
            res.raw_body += data
    elif 'transfer-encoding' in res.headers and res.headers['transfer-encoding'] == 'chunked':
        while True:
            if data.endswith(b'0\r\n\r\n'):
                break

            data = recv_all(s)
            res.raw_body += data
    
    
    hp = HttpProcess()
    res = hp.process_response(res)
    
    return res




