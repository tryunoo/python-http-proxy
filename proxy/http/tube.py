import socket
import ssl
import h11

class Tube:    
    def __init__(self) -> None:
        pass

    def send(self, msg):
        self.socket.sendall(msg)

    def recv_http_body(self, conn) -> bytes:
        raw_body = b''

        while True:
            event = conn.next_event()

            if event is h11.NEED_DATA:
                received_data = self.socket.recv(4096)
                conn.receive_data(received_data)
                raw_body += received_data

            if not event:
                break
            if type(event) is h11.EndOfMessage:
                break
            if type(event) is h11.ConnectionClosed:
                break

        return raw_body


    def recv_http_header(self, conn) -> bytes:
        raw_header = b""
        while True:
            event = conn.next_event()

            if event is h11.NEED_DATA:
                received_data = self.socket.recv(4096)
                conn.receive_data(received_data)
                raw_header += received_data
            else:
                return raw_header


    def recv_raw_http_msg(self, conn) -> bytes:
        raw_header = self.recv_http_header(conn)
        raw_body = self.recv_http_body(conn)

        raw_msg = raw_header + raw_body

        return raw_msg


    def recv_raw_http_response(self) -> bytes:
        return self.recv_raw_http_msg(h11.Connection(our_role=h11.CLIENT))


    def recv_raw_http_request(self) -> bytes:
        return self.recv_raw_http_msg(h11.Connection(our_role=h11.SERVER))


    def send_recv(self, raw_request: bytes) -> bytes | None:
        self.socket.sendall(raw_request)

        try:
            raw_response = self.recv_raw_http_response()
        except ConnectionResetError:
            return None

        return raw_response

    def open_connection(self, host: str, port: int, is_ssl: bool, timeout: int = 20) -> None:
        self.host = host
        self.port = port
        self.is_ssl = is_ssl
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(timeout)

        if is_ssl:
            ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            ctx.check_hostname = False
            ctx.verify_mode = 0
            self.socket = ctx.wrap_socket(self.socket, server_hostname=host)

    def close(self) -> None:
        self.socket.close()

    def set_timeout(self, timeout: int):
        self.socket.settimeout(timeout)

    def upgrade_ssl(self, ctx):
        self.socket = ctx.wrap_socket(self.socket, server_side=True)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)