from httprequest import Tube, exceptions, RequestMessage, PreparedRequest, Request
from proxy import util
from proxy import cert
from typing import Callable

import base64
import tempfile
import socketserver
import traceback
import ssl
import json
import os
import re

class Config():
    host: str
    port: int
    auth: bool
    private_key_path: str
    cacert_path: str
    auth_base64: str

config: Config = Config()


class MyCert():
    private_key: str
    private_key_pem: str
    cacert: str
    cacert_pem: str


mycert: MyCert = MyCert()


class TCPHandler(socketserver.BaseRequestHandler):
    def communicate(self, prepared_request: PreparedRequest):
        self.server.request_process(prepared_request)
        response = prepared_request.send()
        self.server.response_process(response)

        return response

    def process_http(self, tube: Tube, request_message: RequestMessage):
        target = request_message.headers['Host']
        if ':' in target:
            host, port = target.split(':')
            port = int(port)
        else:
            host = target
            port = 80

        prepared_request = PreparedRequest(host, port, False, message=request_message)

        response = self.communicate(prepared_request)

        if not response:
            return

        tube.send(bytes(response.message))
        tube.close()
        return

    def process_https(self, tube: Tube, request_message: RequestMessage):
        # webプロキシ接続OKの応答をクライアントに返す
        tube.send(b"HTTP/1.0 200 Connection established\r\n\r\n")

        target = request_message.headers['Host']
        if ':' in target:
            host, port = target.split(':')
            port = int(port)
        else:
            host = target
            port = 443

        _, server_cert_pem = cert.create_server_cert(host, port, mycert.private_key, mycert.cacert)

        fp = tempfile.NamedTemporaryFile()
        fp.write(server_cert_pem)
        fp.write(mycert.cacert_pem)
        fp.seek(0)

        client_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        client_ctx.load_cert_chain(certfile=fp.name, keyfile=config.private_key_path)
        fp.close()

        try:
            tube.upgrade_socket(client_ctx)
        except (OSError, ssl.SSLEOFError, BrokenPipeError):
            return

        raw_request = tube.recv_raw_http_request()
        request_message = RequestMessage(raw_request)

        prepared_request = PreparedRequest(host, port, True, message=request_message)

        # 対象サーバにリクエストを送信する
        response = self.communicate(prepared_request)

        try:
            tube.send(bytes(response.message))
        except OSError as e:
            return

        tube.close()

        return

    def handle(self):
        tube = Tube()
        tube.socket = self.request

        try:
            raw_request = tube.recv_raw_http_request()
        except ConnectionResetError:
            return

        try:
            request_message = RequestMessage(raw_request)
        except exceptions.NotHttp11RequestMessageError:
            return

        if not request_message:
            return

        '''
        if config.auth:
            if 'Proxy-Authorization' not in request_object.headers:
                client_socket.send(b"HTTP/1.0 407 Proxy Authentication Required\r\nProxy-Authenticate: Basic realm=\"Access to proxy\"\r\n\r\n<html>Proxy Authentication Required.</html>")
                return

            if request_object.headers['Proxy-Authorization'].split()[-1] != config.auth_base64:
                client_socket.send(b"HTTP/1.0 403 Forbidden\r\nProxy-Authenticate: Basic realm=\"Access to proxy\"\r\n\r\n<html>Proxy Authentication Faild.</html>\r\n")
                return
        '''

        try:
            # SSL通信でない場合（HTTP）
            if request_message.method != 'CONNECT':
                self.process_http(tube, request_message)

            # SSL通信の場合（HTTPS）
            if request_message.method == 'CONNECT':
                self.process_https(tube, request_message)
        except Exception as e:
            verbose = traceback.format_exc()
            verbose += "".join([str(x) for x in e.args])
            print(verbose)

        return


def read_config():
    if not os.path.exists('proxy/proxy.conf'):
        util.print_error_exit('"proxy.conf" is not exist.')

    with open('proxy/proxy.conf', 'rt') as f:
        conf_text = f.read()
        conf_text = re.sub(r"#[^\n]*", "", conf_text)

        try:
            json_config = json.loads(conf_text)
        except:
            util.print_error_exit('"proxy.conf": JSON Parse Error.')

        config.host = json_config['host']
        config.port = json_config['port']
        config.private_key_path = json_config['private_key_path']
        config.cacert_path = json_config['cacert_path']
        try:
            config.auth = json_config['auth']
        except:
            config.auth = False
        
        if config.auth:
            if 'auth_user_name' not in json_config:
                util.print_error_exit('"proxy.conf: Need auth_user_name')
            if 'auth_password' not in json_config:
                util.print_error_exit('"proxy.conf: Need auth_password')

            config.auth_base64 = base64.b64encode(b'%s:%s' %(json_config['auth_user_name'].encode(), json_config['auth_password'].encode())).decode()


def run_proxy(request_process: Callable = lambda x: x, response_process: Callable = lambda x: x):
    read_config()

    print(f"Serving on %s %s" % (config.host, config.port))

    mycert.private_key, mycert.private_key_pem = cert.get_private_key(config.private_key_path)
    mycert.cacert, mycert.cacert_pem = cert.get_cacert(config.cacert_path)

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((config.host, config.port), TCPHandler) as server:
        server.request_process = request_process
        server.response_process = response_process
        server.serve_forever()
