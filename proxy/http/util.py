

def chunked_conv(raw_body) -> bytes:
    new_raw_body = b''
    head = 0
    while True:
        res = raw_body.find(b'\r\n', head)
        try:
            data_len = int(raw_body[head:res], 16)
        except ValueError:
            break
        if data_len == 0: break
        tail = res+2 + data_len
        new_raw_body += raw_body[res+2: tail]
        head = tail + 2

    return new_raw_body
