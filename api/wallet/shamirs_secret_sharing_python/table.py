from __future__ import annotations
from .constants import BIT_SIZE, PRIMITIVE_POLYNOMIAL, MAX_SHARES

zeroes = '0' * (4 * BIT_SIZE)

logs = [0] * BIT_SIZE
exps = [0] * BIT_SIZE

x = 1
for i in range(BIT_SIZE):
    exps[i] = x
    logs[x] = i
    x = x << 1
    if x >= BIT_SIZE:
        x = x ^ PRIMITIVE_POLYNOMIAL
        x = x & MAX_SHARES
