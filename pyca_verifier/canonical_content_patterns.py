"""Finite words with one designated output position per tape symbol.

Static crossing words use the catalogue's C2 trajectory anchor. Incoming and
outgoing descriptions may put that anchor seven cells apart; the smaller
anchor is designated. This local rule assumes distinct static symbols never
have anchors seven cells apart, an obligation of the legal spacing invariant.

Moving crossing words designate their rightmost cell. All nested moving-word
descriptions in the frozen family have the same right edge and label. Thus
their output is deduplicated at one site without comparing ownership hulls.

Only semantic words are loaded here. Garbage and ether need no output; no
whole-row coverage condition or larger catalogue witness is imposed. These
rules establish uniqueness on the audited catalogue, not completeness for
every reachable Rule 110 row. Partial ossification is handled separately.
"""
from dataclasses import dataclass
from functools import lru_cache

from .literal_matcher import LiteralMatcher
from .catalogue import defect_span
from .moving_crossing_patterns import moving_crossing_patterns
from .static_crossing_patterns import static_crossing_patterns


@dataclass(frozen=True, slots=True)
class CanonicalPrimitive:
    bits: str
    kind: str
    symbol: str
    offset: int
    cells: int
    anchor_offset: int


@dataclass(frozen=True, slots=True)
class CanonicalHit:
    """A local description; coordinates may be bounded head-relative offsets."""

    kind: str
    symbol: str
    left: int
    right: int
    lo: int
    hi: int
    anchor: int


@lru_cache(maxsize=1)
def canonical_primitives():
    result = []
    for kind, family in (('static', static_crossing_patterns()),
                         ('moving', moving_crossing_patterns())):
        for pattern in family:
            lo, hi = defect_span(pattern.bits)
            anchor = (pattern.anchor_offset if kind == 'static'
                      else len(pattern.bits)-1)
            result.append(CanonicalPrimitive(pattern.bits, kind, pattern.symbol,
                                              lo, hi-lo, anchor))
    return tuple(result)


def _combine(descriptions, anchor):
    first = descriptions[0]
    return CanonicalHit(first.kind, first.symbol,
        min(h.left for h in descriptions), max(h.right for h in descriptions),
        min(h.lo for h in descriptions), max(h.hi for h in descriptions), anchor)


def canonicalize_symbols(hits):
    """Choose static/moving output sites from a bounded set of local matches.

    No absolute coordinates or semantic witness labels are needed. A finite
    transducer supplies hits from its bounded local window, then emits only
    a returned hit whose anchor is the designated current output position.
    Different matching words at the same position must agree on the bit.

    Static aliases are merged only over seven cells, never by unbounded
    connected-component closure. A chain of three such anchors is rejected:
    it would contradict the assumed separation of distinct static symbols.
    Conversion-frontier ownership must subsequently suppress the appropriate
    incoming/outgoing description, so this function alone is not a decoder.
    """
    by_kind = {'static': {}, 'moving': {}}
    for hit in hits:
        if hit.kind in by_kind:
            by_kind[hit.kind].setdefault(hit.anchor, []).append(hit)
    output = []
    conflicts = []
    for kind, by_anchor in by_kind.items():
        for anchor in sorted(by_anchor):
            descriptions = by_anchor[anchor]
            symbols = {h.symbol for h in descriptions}
            if len(symbols) != 1:
                conflicts.append(f'conflicting_{kind}_labels')
                continue
            if kind == 'static':
                previous = by_anchor.get(anchor-7, ())
                following = by_anchor.get(anchor+7, ())
                if previous and following:
                    conflicts.append('nonisolated_static_aliases')
                if previous:
                    if any(h.symbol not in symbols for h in previous):
                        conflicts.append('conflicting_static_aliases')
                    continue
                if following:
                    if any(h.symbol not in symbols for h in following):
                        conflicts.append('conflicting_static_aliases')
                        continue
                    descriptions = descriptions+following
            output.append(_combine(descriptions, anchor))
    return tuple(output), tuple(sorted(set(conflicts)))


class CanonicalSymbolRecognizer:
    """Diagnostic wrapper around exactly the finite words used by the machine.

    ``find`` returns all designated sites and explicit label conflicts. Its
    coordinate lists are for inspection; the 2DFT uses the primitive IDs and
    bounded relative positions directly.
    """

    def __init__(self):
        self.patterns = canonical_primitives()
        self.matcher = LiteralMatcher(self.patterns, reverse=True)
        self.width = self.matcher.width

    def find(self, bits):
        tail = warm = 0
        hits = []
        for end, bit in enumerate(bits, 1):
            tail, warm, indices = self.matcher.advance(tail, warm, int(bit))
            for index in indices:
                p = self.patterns[index]
                start = end-len(p.bits)
                hits.append(CanonicalHit(p.kind, p.symbol, start, end,
                    start+p.offset, start+p.offset+p.cells,
                    start+p.anchor_offset))
        return canonicalize_symbols(hits)
