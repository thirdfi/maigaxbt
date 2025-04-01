from __future__ import annotations
from .constants import BIT_SIZE
import re

def parse(input_):
    share = {'id': None, 'bits': None, 'data': None}

    if isinstance(input_, bytes):
        input_ = input_.hex()

    if input_[0] == '0':
        input_ = input_[1:]

    share['bits'] = int(input_[0], 36)
    max_bits = BIT_SIZE - 1
    id_length = len(hex(max_bits)[2:])
    regex = f"^([a-kA-K3-9]{{1}})([a-fA-F0-9]{{{id_length}}})([a-fA-F0-9]+)$"

    import re
    matches = re.match(regex, input_)
    if matches:
        share['id'] = int(matches.group(2), 16)
        share['data'] = matches.group(3)

    return share
