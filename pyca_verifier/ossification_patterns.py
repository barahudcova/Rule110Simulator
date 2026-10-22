"""Finite words identifying the single symbol undergoing ossification.

These bounded words include approach and active conversion phases. A frontier
owns one static-sweep output and suppresses its alternative moving description.
The literal catalogue is frozen; decoding never evolves a CA neighborhood.

These words depend on the encoder's joins, not just the individual glider
shapes. The V4 extension records the productive-garbage separations induced
by the uniform program joins. Copying the V3 vocabulary alone omits reachable
partial conversions and can shift the moving sweep's packet alignment.
"""
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
from .catalogue import defect_span, load_catalogue


@dataclass(frozen=True, slots=True)
class FrontierPattern:
    bits: str
    symbol: str
    anchor_offset: int
    source_index: int
    source_start: int
    core_offset: int
    core_cells: int
    source_family: str = 'isolated'


@lru_cache(maxsize=1)
def frontier_patterns():
    payload = load_catalogue('ossification_patterns.json')
    digest = sha256(json.dumps(payload['patterns'],separators=(',',':')).encode()).hexdigest()
    if payload['format_version'] != 1 or digest != payload['patterns_sha256']:
        raise ValueError('Invalid ossification catalogue')
    result = []
    for width, hexadecimal, symbol, anchor, source, source_start, *extra in payload['patterns']:
        bits = format(int(hexadecimal,16),f'0{width}b')
        span = defect_span(bits)
        if symbol not in ('Y','N') or not span or span[1] != anchor:
            raise ValueError('Invalid ossification label or anchor')
        family = extra[0] if extra else ('compound' if source < 0 else 'isolated')
        result.append(FrontierPattern(bits,symbol,anchor,source,source_start,span[0],span[1]-span[0],family))
    return tuple(result)
