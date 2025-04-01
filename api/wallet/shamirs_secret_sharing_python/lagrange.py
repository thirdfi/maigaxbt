from __future__ import annotations
from .table import logs, exps
from .constants import MAX_SHARES

def lagrange(x, p):
    n = MAX_SHARES
    product = 0
    sum_ = 0
    for i in range(len(p[0])):
        if p[1][i]:
            product = logs[p[1][i]]
            for j in range(len(p[0])):
                if i != j:
                    if x == p[0][j]:
                        product = -1
                        break
                    a = logs[x ^ p[0][j]] - logs[p[0][i] ^ p[0][j]]
                    product = (product + a + n) % n
            if sum_ == -1:
                sum_ = sum_
            else:
                sum_ = sum_ ^ exps[product]
    return sum_
