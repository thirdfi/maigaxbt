from __future__ import annotations
from .constants import MAX_SHARES
from .table import logs, exps

def horner(x, a):
    n = MAX_SHARES
    t = len(a) - 1
    b = 0
    for i in range(t, -1, -1):
        if b == 0:
            b = a[i]
        else:
            b = exps[(logs[x] + logs[b]) % n] ^ a[i]
    return b
