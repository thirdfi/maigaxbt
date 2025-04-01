from __future__ import annotations
from .points import points
from .random_gen import random
from .codec import hex_encode, bin_encode, pad, split_string, encode
from .constants import MAX_SHARES, BIT_PADDING, BIT_COUNT, BIN_ENCODING
import copy

scratch = [None] * (2 * MAX_SHARES)

def split(secret, opts):
    if not secret or len(secret) == 0:
        raise TypeError('Secret cannot be empty.')
    if isinstance(secret, str):
        secret = secret.encode('utf-8')
    if not isinstance(secret, (bytes, bytearray)):
        raise TypeError('Expecting secret to be a buffer.')
    if not opts or not isinstance(opts, dict):
        raise TypeError('Expecting options to be an object.')
    if not isinstance(opts.get('shares'), int):
        raise TypeError('Expecting shares to be a number.')
    if opts['shares'] <= 0 or opts['shares'] > MAX_SHARES:
        raise ValueError(f"Shares must be 0 < shares <= {MAX_SHARES}.")
    if not isinstance(opts.get('threshold'), int):
        raise TypeError('Expecting threshold to be a number.')
    if opts['threshold'] <= 0 or opts['threshold'] > opts['shares']:
        raise ValueError(f"Threshold must be 0 < threshold <= {opts['shares']}.")
    if 'random' not in opts or not callable(opts['random']):
        opts['random'] = random

    hexed = hex_encode(secret)
    binary = bin_encode(hexed, 16)
    parts = split_string('1' + binary, BIT_PADDING, 2)

    for i in range(len(parts)):
        p = points(parts[i], opts)
        for j in range(opts['shares']):
            if not scratch[j]:
                scratch[j] = format(p[j]['x'], 'x')
            z = format(p[j]['y'], 'b')
            y = scratch[j + MAX_SHARES] or ''
            scratch[j + MAX_SHARES] = pad(z) + y

    for i in range(opts['shares']):
        x = scratch[i]
        y = hex_encode(scratch[i + MAX_SHARES], BIN_ENCODING)
        scratch[i] = encode(x, y)

    result = copy.deepcopy(scratch[:opts['shares']])
    for i in range(len(scratch)):
        scratch[i] = 0
    return result
