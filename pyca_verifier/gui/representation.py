"""Fast display matching of the original PyCA Rule 110 pattern catalogue.

These operations change display states only. Binary Rule 110 rows are untouched.
N matching preserves the original coarse_grain rules; Y uses the supplied middle
and full stationary-symbol templates. Candidate positions are compared as bitsets.
"""

import numpy as np
from functools import lru_cache
from types import SimpleNamespace
from ..patterns import GLIDERS, ETHER


def pattern_word(pattern):
    return "".join(map(str, pattern))


def match_starts(value, width, word):
    """Return a bitset of every exact match, with the leftmost start as bit 0."""
    count = width - len(word) + 1
    if count <= 0:
        return 0
    matches = (1 << count) - 1
    for i, symbol in enumerate(word):
        matches &= (value >> i) if symbol == "1" else ~(value >> i)
        if not matches:
            break
    return matches


@lru_cache(maxsize=256)
def _chunks(word):
    # The catalogue reuses a small set of four-cell words in long symbols.
    # Sharing their match masks avoids rescanning the same cells for every phase.
    return tuple((word[offset:offset+4], offset)
                 for offset in range(0, len(word), 4))


class _RowMatcher:
    """Exact matches sharing short-word masks within one display row."""
    def __init__(self, value, width):
        self.value, self.width = value, width
        self.short_matches = {}
        self.matches = {}

    def starts(self, word):
        if word in self.matches:
            return self.matches[word]
        count = self.width-len(word)+1
        starts = (1 << count)-1 if count > 0 else 0
        for chunk, offset in _chunks(word):
            if not starts:
                break
            if chunk not in self.short_matches:
                self.short_matches[chunk] = match_starts(self.value, self.width, chunk)
            starts &= self.short_matches[chunk] >> offset
        self.matches[word] = starts
        return starts


def positions(bits):
    while bits:
        first = bits & -bits
        yield first.bit_length() - 1
        bits ^= first


def unpack(value, width):
    data = np.frombuffer(value.to_bytes((width + 7) // 8, "little"), dtype=np.uint8)
    return np.unpackbits(data, bitorder="little")[:width]


class PyCARepresentation:
    def __init__(self, original=None):
        if original is None:
            # Legacy load_patterns pads middle templates before matching them.
            def padded(family):
                length = max(map(len, GLIDERS[family]))
                return [p + (GLIDERS['ether']*((length-len(p)+13)//14))[:length-len(p)]
                        for p in GLIDERS[family]]
            original = SimpleNamespace(ether=GLIDERS['ether'], Nouter=GLIDERS['Nouter'],
                Nmiddle=padded('Nmiddle'), Ymiddle=padded('Ymiddle'),
                Y=GLIDERS['Y'], N=GLIDERS['N'],
                strC2=[ETHER+pattern_word(p)+ETHER for p in GLIDERS['C2']])
        self.ether = pattern_word(original.ether)
        self.n_outer = [(pattern_word(a), pattern_word(b)) for a, b in original.Nouter]
        self.n_middle = [pattern_word(p) for p in original.Nmiddle]
        self.y_middle = [pattern_word(p) for p in original.Ymiddle]
        self.y_symbols = [pattern_word(p) for p in original.Y]
        self.n_symbols = [pattern_word(p) for p in original.N]
        self.c2 = original.strC2

    def color(self, value, width, *, color_y=True, full_symbols=True):
        states = unpack(value, width).copy()
        matches = _RowMatcher(value, width).starts
        starts = matches(self.ether)
        coverage = 0
        for offset in range(len(self.ether)):
            coverage |= starts << offset
        ether = unpack(coverage & ((1 << width) - 1), width).astype(bool)
        states[ether & (states == 1)] = 2

        def mark(starts, size, symbol=4):
            for start in positions(starts):
                region = states[start:min(width, start+size)]
                cells = region <= 1
                region[cells] = np.where(region[cells] == 1, symbol, 3)

        # These bounds and offsets are the original coarse_grain behaviour.
        for a, b in self.n_outer:
            count = width - len(a) + 1 - 130
            if count > 0:
                starts = matches(a) & (matches(b) >> 115)
                mark(starts & ((1 << count) - 1), len(a)+130)
        for word in self.n_middle:
            count = width - len(word) + 1 - 90
            if count > 0:
                starts = matches(word) >> 50
                mark(starts & ((1 << count) - 1), len(word)+90)
        if full_symbols:
            for word in self.n_symbols:
                mark(matches(word), len(word))
        if color_y:
            for word in self.y_middle:
                count = width - len(word) + 1 - 90
                if count > 0:
                    starts = matches(word) >> 50
                    mark(starts & ((1 << count) - 1), len(word)+90, 5)
            for word in self.y_symbols:
                mark(matches(word), len(word), 5)
        return states

    def tape_positions(self, row):
        candidates = 0
        for word in self.c2:
            candidates |= match_starts(row.value, row.width, word) << (len(word)//2)
        return [row.origin + index for index in positions(candidates)]
