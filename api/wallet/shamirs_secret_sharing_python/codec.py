from __future__ import annotations
from .constants import (
    BIT_COUNT,
    BYTES_PER_CHARACTER,
    BIT_SIZE,
    UTF8_ENCODING,
    BIN_ENCODING
)
from .table import zeroes
import binascii

def pad(text, multiple=None):
    missing = 0
    result = text
    if multiple is None:
        multiple = BIT_COUNT
    if text:
        missing = len(text) % multiple
    if missing:
        offset = -((multiple - missing) + len(text))
        result = (zeroes + text)[offset:]
    return result

def hex_encode(buffer, encoding=None):
    padding = 2 * BYTES_PER_CHARACTER
    if encoding is None:
        encoding = UTF8_ENCODING

    def from_string():
        chunks = []
        if encoding == UTF8_ENCODING:
            for c in buffer:
                chunk = format(ord(c), 'x')
                chunks.insert(0, pad(chunk, padding))
        if encoding == BIN_ENCODING:
            buffer_bin = pad(buffer, 4)
            for i in range(len(buffer_bin), 0, -4):
                bits = buffer_bin[i-4:i]
                chunk = format(int(bits, 2), 'x')
                chunks.insert(0, chunk)
        return ''.join(chunks)

    def from_buffer():
        chunks = []
        for byte in buffer:
            chunk = format(byte, 'x')
            chunks.insert(0, pad(chunk, padding))
        return ''.join(chunks)

    if isinstance(buffer, str):
        return from_string()
    if isinstance(buffer, (bytes, bytearray)):
        return from_buffer()
    raise TypeError('Expecting a string or buffer as input.')

def bin_encode(buffer, radix=16):
    chunks = []
    for i in range(len(buffer)-1, -1, -1):
        chunk = None
        if isinstance(buffer, (bytes, bytearray)):
            chunk = buffer[i]
        elif isinstance(buffer, str):
            chunk = int(buffer[i], radix)
        elif isinstance(buffer, list):
            chunk = buffer[i]
            if isinstance(chunk, str):
                chunk = int(chunk, radix)
        if chunk is None:
            raise TypeError('Unsupported type for chunk in buffer array.')
        chunks.insert(0, pad(format(chunk, 'b'), 4))
    return ''.join(chunks)

def encode(id_, data):
    id_ = int(id_, 16)
    padding = len(format(BIT_SIZE - 1, 'x'))
    header = bytes(
        BIT_COUNT.to_bytes(1, 'big') +
        int(pad(format(id_, 'x'), padding), 16).to_bytes((padding + 1) // 2, 'big')
    )
    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data, 'utf-8')
    return header + data

def decode(buffer, encoding='utf-8'):
    padding = 2 * BYTES_PER_CHARACTER
    offset = padding
    chunks = []

    if isinstance(buffer, (bytes, bytearray)):
        buffer = buffer.decode(encoding)
    buffer = pad(buffer, padding)

    for i in range(0, len(buffer), offset):
        bits = buffer[i:i + offset]
        chunk = int(bits, 16)
        chunks.insert(0, chunk)

    return bytes(chunks)

def split_string(string, padding=None, radix=2):
    chunks = []
    if isinstance(string, (bytes, bytearray)):
        string = string.decode()

    if padding:
        string = pad(string, padding)

    i = len(string)
    while i > BIT_COUNT:
        bits = string[i - BIT_COUNT:i]
        chunk = int(bits, radix)
        chunks.append(chunk)
        i -= BIT_COUNT

    chunks.append(int(string[:i], radix))
    return chunks
