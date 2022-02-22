from distutils.debug import DEBUG
from email import header
from tracemalloc import start
from request import HttpRequest, HttpResponse
import tube
import tempfile
import cert
import socketserver
import socket
import time
import ssl



server_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
#server_ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
server_ctx.check_hostname = False
server_ctx.verify_mode = 0


# Multi Threading
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class TCPHandler(socketserver.BaseRequestHandler):

    def connect_server(self, host, port):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((host, port))
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        return server_socket
    

    def handle(self):
        client_socket = self.request
        raw_request = tube.recv_all(client_socket)
        if len(raw_request) == 0: return
        
        req = HttpRequest(raw_request)

        # SSL通信でない場合（HTTP）
        if req.method != 'CONNECT':
            server_socket = self.connect_server(req.host, req.port)

            tube.send_http_request(server_socket, req)

            res = tube.recv_http_response(server_socket, req)

            client_socket.sendall(res.get_raw_response())

        # SSL通信の場合（HTTPS）
        if req.method == 'CONNECT':
            # webプロキシ接続OKの応答をクライアントに返す
            client_socket.send(b"HTTP/1.0 200 Connection established\n\n")

            host = req.host
            port = req.port

            crt = cert.create_server_cert(req.host, req.port)
            
            cacrt_path = 'ssl/mitmproxy-ca-cert.pem'
            cacrt_fp = open(cacrt_path, 'r')
            cacrt = cacrt_fp.read().encode('utf-8')

            fp = tempfile.NamedTemporaryFile()

            fp.write(crt)
            fp.write(cacrt)
            fp.seek(0)

            client_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            client_ctx.load_cert_chain(certfile=fp.name, keyfile="ssl/mitmproxy-ca.pem")
            #client_ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1

            try:
                ssl_client_socket = client_ctx.wrap_socket(client_socket, server_side=True)
            except Exception as e:
                return
                
            raw_request = tube.recv_all(ssl_client_socket)
            if len(raw_request) == 0: return

            req = HttpRequest(raw_request)
            req.host = host
            req.port = port

            # 対象サーバにリクエストを送信する
            server_socket = self.connect_server(req.host, req.port)
            ssl_server_socket = server_ctx.wrap_socket(server_socket, server_hostname=req.host)
            tube.send_http_request(ssl_server_socket, req)

            res = tube.recv_http_response(ssl_server_socket, req)

            ssl_client_socket.sendall(res.get_raw_response())

            ssl_server_socket.close()
            ssl_client_socket.close()
            fp.close()
            
        return



if __name__ == "__main__":
    HOST, PORT = "localhost", 9999

    with ThreadedTCPServer((HOST, PORT), TCPHandler) as server:
        server.allow_reuse_address = True
        server.serve_forever()
