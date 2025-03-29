from __future__ import annotations
from .constants import BIN_ENCODING
from .lagrange import lagrange
from .share import parse
from . import codec

def combine(shares):
    chunks = []
    x = []
    y = []
    t = len(shares)

    for i in range(t):
        share = parse(shares[i])
        if share['id'] not in x:
            x.append(share['id'])
            bin_str = codec.bin_encode(share['data'], 16)
            parts = codec.split_string(bin_str, 0, 2)
            for j in range(len(parts)):
                if len(y) <= j or y[j] is None:
                    while len(y) <= j:
                        y.append([])
                y[j].append(parts[j])

    for i in range(len(y)):
        p = lagrange(0, [x, y[i]])
        chunks.insert(0, codec.pad(format(p, 'b')))

    string = ''.join(chunks)
    binary = string[string.index('1') + 1:]
    hexed = codec.hex_encode(binary, BIN_ENCODING)
    value = codec.decode(hexed)
    return bytes(value)
