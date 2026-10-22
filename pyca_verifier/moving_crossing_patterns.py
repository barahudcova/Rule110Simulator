"""Finite moving Y/N words, including passages through static tape."""
from dataclasses import dataclass
from functools import lru_cache
from .catalogue import load_catalogue


@dataclass(frozen=True, slots=True)
class MovingCrossingPattern:
    bits: str
    symbol: str
    provenance: str


@lru_cache(maxsize=1)
def moving_crossing_patterns():
    payload = load_catalogue('moving_crossing_patterns.json')
    patterns = tuple(MovingCrossingPattern(**entry) for entry in payload['patterns'])
    if payload['schema'] != 1 or len(patterns) != 6816 or max(len(p.bits) for p in patterns) != 514:
        raise ValueError('Invalid moving-symbol catalogue')
    if any(not p.bits or set(p.bits)-{'0','1'} or p.symbol not in ('Y','N') for p in patterns):
        raise ValueError('Invalid moving-symbol word')
    return patterns
