from __future__ import annotations
import os

def random(size):
    r = os.urandom(32 + size)
    return r[32:]
