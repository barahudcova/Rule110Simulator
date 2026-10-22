"""Finite static Y/N words, including garbage and moving-data crossings."""
from dataclasses import dataclass
from functools import lru_cache
from .catalogue import load_catalogue


@dataclass(frozen=True, slots=True)
class StaticCrossingPattern:
    bits: str
    symbol: str
    anchor_offset: int
    source_id: int
    source_tick: int


@lru_cache(maxsize=1)
def static_crossing_patterns():
    payload = load_catalogue('static_crossing_patterns.json')
    patterns = tuple(StaticCrossingPattern(**entry) for entry in payload['patterns'])
    if payload['schema'] != 1 or len(patterns) != 764 or max(len(p.bits) for p in patterns) != 161:
        raise ValueError('Invalid static-symbol catalogue')
    for p in patterns:
        if (not p.bits or set(p.bits)-{'0','1'} or p.symbol not in ('Y','N')
                or not -14 <= p.anchor_offset < len(p.bits)+14):
            raise ValueError('Invalid static-symbol word or anchor')
    return patterns
