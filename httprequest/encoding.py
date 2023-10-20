import gzip
import zlib
from io import BytesIO

import brotli


def decode(content: bytes, encoding: str) -> bytes:
    decoders = {"gzip": decode_gzip, "deflate": decode_deflate, "br": decode_brotli}

    if encoding in decoders:
        content = decoders[encoding](content)

    return content


def decode_gzip(content: bytes) -> bytes:
    if not content:
        return b""
    gfile = gzip.GzipFile(fileobj=BytesIO(content))
    return gfile.read()


def decode_deflate(content: bytes) -> bytes:
    if not content:
        return b""
    try:
        return zlib.decompress(content)
    except zlib.error:
        return zlib.decompress(content, -15)


def decode_brotli(content: bytes) -> bytes:
    if not content:
        return b""
    res: bytes = brotli.decompress(content)
    return res
