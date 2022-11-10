from distutils.debug import DEBUG
from tracemalloc import start
from OpenSSL import crypto
import tube
import tempfile
import cert
import util
import socketserver
import socket
import ssl
import json
import os


server_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
#server_ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
server_ctx.check_hostname = False
server_ctx.verify_mode = 0

class Config(): pass
config = Config()

class MyCert(): pass
mycert = MyCert()

class TCPHandler(socketserver.BaseRequestHandler):
    def connect_server(self, host, port):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((host, port))
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        return server_socket


    def handle(self):
        client_socket = self.request
        req = tube.recv_http_request(client_socket)
        
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

            _, server_cert_pem = cert.create_server_cert(req.host, req.port, mycert.private_key, mycert.cacert)
            
            fp = tempfile.NamedTemporaryFile()
            fp.write(server_cert_pem)
            fp.write(mycert.cacert_pem)
            fp.seek(0)

            client_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            client_ctx.load_cert_chain(certfile=fp.name, keyfile=config.private_key_path)
            fp.close()

            try:
                ssl_client_socket = client_ctx.wrap_socket(client_socket, server_side=True)
                ssl_client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except Exception as e:
                util.print_error("SSL connect error.")
                return
                
            req = tube.recv_http_request(ssl_client_socket)

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
            
        return


def read_config():
    if not os.path.isfile('config.json'):
        util.print_error_exit('"config.json" is not exist.')

    with open('config.json', 'rb') as f:
        try:
            json_config = json.load(f)
        except:
            util.print_error_exit('"config.json": JSON Parse Error.')

        config.host = json_config['host']
        config.port = json_config['port']
        config.private_key_path = json_config['private_key_path']
        config.cacert_path = json_config['cacert_path']


if __name__ == "__main__":
    HOST, PORT = "a", 9999
    read_config()

    mycert.private_key, mycert.private_key_pem = cert.get_private_key(config.private_key_path)
    mycert.cacert, mycert.cacert_pem = cert.get_cacert(config.cacert_path)
    
    with socketserver.ThreadingTCPServer((config.host, config.port), TCPHandler) as server:
        server.allow_reuse_address = True
        server.serve_forever()
