from proxy.http.http import ResponseMessage
import socket
import ssl
import h11

server_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
server_ctx.check_hostname = False
server_ctx.verify_mode = 0


def recv_http_body(s, conn):
    raw_body = b''

    while True:
        event = conn.next_event()

        if event is h11.NEED_DATA:
            received_data = s.recv(4096)
            conn.receive_data(received_data)
            raw_body += received_data

        if not event:
            break
        if type(event) is h11.EndOfMessage:
            break
        if type(event) is h11.ConnectionClosed:
            break

    return raw_body


def recv_http_header(s, conn):
    raw_header = b""
    while True:
        event = conn.next_event()

        if event is h11.NEED_DATA:
            received_data = s.recv(4096)
            conn.receive_data(received_data)
            raw_header += received_data
        else:
            return raw_header


def recv_raw_http_msg(s: socket.socket, conn):
    raw_header = recv_http_header(s, conn)
    connection_reader = conn._reader
    raw_body = recv_http_body(s, conn)

    if type(connection_reader) == h11._readers.ChunkedReader:
        pass

    raw_msg = raw_header + raw_body

    return raw_msg


def recv_raw_http_response(s: socket.socket):
    return recv_raw_http_msg(s, h11.Connection(our_role=h11.CLIENT))


def recv_raw_http_request(s: socket.socket):
    return recv_raw_http_msg(s, h11.Connection(our_role=h11.SERVER))


def send_recv(host: str, port: int, is_ssl: bool, raw_request: bytes, timeout: int = 10) -> bytes | None:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((host, port))
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(timeout)

    if is_ssl:
        server_socket = server_ctx.wrap_socket(server_socket, server_hostname=host)

    server_socket.sendall(raw_request)

    try:
        raw_response = recv_raw_http_response(server_socket)
    except ConnectionResetError:
        return None

    server_socket.close()

    return raw_response
