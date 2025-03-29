from __future__ import annotations
from .horner import horner

def points(a0, opts):
    prng = opts['random']
    a = [a0]
    p = []
    t = opts['threshold']
    n = opts['shares']
    for i in range(1, t):
        a.append(int(prng(1).hex(), 16))
    for i in range(1, 1 + n):
        p.append({
            'x': i,
            'y': horner(i, a)
        })
    return p
