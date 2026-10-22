"""Display diagnostics for unsafe ossifier/stationary-tape encounters.

The A4/C2 detector observes an adjacent incoming pair, contact of their free
trajectories, and persistent core mismatch across a seven-tick window. Cook's
spatial and temporal F-production signatures are also monitored every CA tick.
These observations do not prove an input's infinite-time admissibility.
"""
from collections import deque
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from functools import lru_cache
from .patterns import ETHER, word
from .matching import match_starts, positions

SPATIAL = '01101001101000'
TEMPORAL = '110101010111111'
# Measured by evolving the original C2[0] through its seven phases.
C2_OFFSETS = (0,-4,6,2,-2,-6,-10)
A4_OFFSETS = (0,-4,6)


@lru_cache(maxsize=128)
def binary_pattern(bits):
    return int(bits[::-1],2),(1 << len(bits))-1


def spatial_starts(value, width):
    """Exact F-birth matches, sharing its repeated six-cell subword."""
    count = width-len(SPATIAL)+1
    if count <= 0:
        return 0
    # 011010 contains 01 at offsets zero and three. Form this shared
    # two-cell mask once, then check the two remaining cells. The final
    # fourteen-cell bound below excludes starts beyond the known row.
    pair = ~value & (value >> 1)
    repeated = pair & (pair >> 3) & (value >> 2) & ~(value >> 5)
    return (repeated & (repeated >> 6) & ~(value >> 12) & ~(value >> 13)
            & ((1 << count)-1))


def sequence_catalogue():
    pairs = []
    for a in range(3):
        for c in range(7):
            for tiles in (1,2,3):
                pairs.append({'a4_phase':a,'c2_phase':c,'ether_tiles':tiles,
                    'bits':ETHER+word('A4',a)+ETHER*tiles+word('C2',c)+ETHER})
    return {'sources':{'cook':'https://arxiv.org/pdf/0906.3248 (section 1; Figure 12(z))',
        'pairs':'Original PyCA A4/C2 catalogue; ether-separated approaching pairs'},
        'spatial_F_birth':SPATIAL,'temporal_F_birth':TEMPORAL,
        'temporal_order':'one fixed physical cell, oldest tick first; no display subsampling',
        'approaching_pairs':pairs,
        'interpretation':'A pair is a precursor. Overlapping A4/C2 cores departing their free '
            'trajectories, followed by persistent core loss, identifies a local encounter. '
            'F signatures are diagnostics; none alone proves non-admissibility or rules out intended halting.'}


@dataclass(frozen=True)
class CollisionEvent:
    kind: str
    tick: int
    x: int
    signature: str
    precursor_tick: int | None = None
    a4_phase: int | None = None
    c2_phase: int | None = None
    ether_tiles: int | None = None

    def as_dict(self):
        return asdict(self)


@dataclass
class Encounter:
    tick: int
    anchor: int
    a4_phase: int
    c2_phase: int
    tiles: int
    signature: str
    contact_seen: bool = False
    c2_losses: deque = field(default_factory=lambda: deque(maxlen=7))
    a4_losses: deque = field(default_factory=lambda: deque(maxlen=7))


class CollisionMonitor:
    def __init__(self):
        self.events = []
        self.pending = {}
        self.completed = set()
        self.recent = deque(maxlen=len(TEMPORAL))
        self.temporal_prefixes = [0]*len(TEMPORAL)
        self.previous_origin = None
        self.seen = set()
        self.a4 = [ETHER+word('A4',i)+ETHER for i in range(3)]
        self.c2 = [ETHER+word('C2',i)+ETHER for i in range(7)]
        self.a4_sizes = [len(word('A4',i)) for i in range(3)]
        self.a4_cores = [word('A4',i) for i in range(3)]
        self.c2_cores = [word('C2',i) for i in range(7)]
        self._a4_groups = self._phase_groups(self.a4_cores)
        self._c2_groups = self._phase_groups([core+ETHER for core in self.c2_cores])
        self._extra_gaps = {tiles: binary_pattern(ETHER*(tiles-1))
                            for tiles in (2,3)}

    @staticmethod
    def _phase_groups(patterns):
        """Group exact local words by size, retaining every phase index."""
        groups = {}
        for phase,bits in enumerate(patterns):
            value,mask = binary_pattern(bits)
            groups.setdefault(len(bits), {}).setdefault(value, []).append(phase)
        return tuple((size, (1 << size)-1, lookup) for size,lookup in groups.items())

    def contains(self, row, x, bits):
        offset = x-row.origin
        if offset < 0 or offset+len(bits) > row.width:
            return None
        value,mask = binary_pattern(bits)
        return ((row.value >> offset) & mask) == value

    def on_splice(self, before, after):
        """A reservoir edit is not a CA tick or a valid temporal observation.

        Retain a chronological prefix only if its remaining future light cone
        is unchanged. Matching the current cell alone can splice old ether
        history onto newly inserted program evolution when a neighbor changes.
        Newly supplied or affected cells must accumulate fresh native bits.
        """
        lo = max(before.origin,after.origin)
        hi = min(before.origin+before.width,after.origin+after.width)
        shift = after.origin-before.origin
        def align(value):
            return value >> shift if shift >= 0 else value << -shift
        valid = 0
        if hi > lo:
            overlap = ((1 << (hi-lo))-1) << (lo-after.origin)
            valid = overlap & ~(align(before.value)^after.value)
        # A prefix of i+1 bits needs len(TEMPORAL)-i-1 more native ticks.
        # Rule 110 has radius one, so erode the unchanged mask once for each
        # remaining tick. Changes outside the overlap count as unsafe too.
        # Long prefixes need a smaller cone than short prefixes; genuinely
        # unaffected histories remain available instead of resetting them all.
        prefixes = [0]*len(TEMPORAL)
        for i in range(len(TEMPORAL)-1, -1, -1):
            prefixes[i] = align(self.temporal_prefixes[i]) & valid
            valid &= (valid << 1) & (valid >> 1)
        self.temporal_prefixes = prefixes
        self.previous_origin = after.origin
        for anchor in list(self.pending):
            if not (lo+64 <= anchor < hi-64):
                del self.pending[anchor]

    def add(self, event):
        key = (event.kind,event.x)
        if key not in self.seen:
            self.seen.add(key)
            self.events.append(event)

    def sample_pairs(self, row):
        # Search all shared ether flanks, then check only bounded windows at
        # their candidates. A4 has two core lengths; the flanks exclude the
        # extensive untouched ether before any core or C2 phase is inspected.
        value, width = row.value, row.width
        ether_size = len(ETHER)
        ether = match_starts(value,width,ETHER)
        data = value.to_bytes((width+7)//8, 'little')

        def local_value(start, size, mask):
            if start < 0 or start+size > width:
                return None
            base,offset = divmod(start,8)
            return (int.from_bytes(data[base:base+(offset+size+7)//8], 'little')
                    >> offset) & mask

        a4_starts = [[] for _ in self.a4_cores]
        for size,mask,lookup in self._a4_groups:
            flanks = ether & (ether >> (ether_size+size))
            for start in positions(flanks):
                for a in lookup.get(local_value(start+ether_size,size,mask), ()):
                    a4_starts[a].append(start)
        # Preserve the original phase/start/gap/phase encounter ordering, even
        # if more than one complete word describes the same physical anchor.
        for a,starts in enumerate(a4_starts):
            for start in starts:
                end = start+ether_size+self.a4_sizes[a]
                for tiles in (1,2,3):
                    if tiles > 1:
                        # The first gap tile was checked as the A4 right flank.
                        wanted,mask = self._extra_gaps[tiles]
                        if local_value(end+ether_size,(tiles-1)*ether_size,mask) != wanted:
                            break  # A longer all-ether gap cannot match either.
                    x = end+tiles*ether_size
                    phases = []
                    for size,mask,lookup in self._c2_groups:
                        phases.extend(lookup.get(local_value(x,size,mask), ()))
                    for c in sorted(phases):
                        anchor = row.origin+x-C2_OFFSETS[c]
                        if anchor in self.pending or anchor in self.completed:
                            continue
                        signature = ETHER+self.a4_cores[a]+ETHER*tiles+self.c2_cores[c]+ETHER
                        self.pending[anchor] = Encounter(row.time,anchor,a,c,tiles,signature)

    def observe(self, row):
        """Observe a binary row; continuation splices must not be passed as ticks."""
        before = len(self.events)
        self.recent.append(row)
        for anchor,candidate in list(self.pending.items()):
            elapsed = row.time-candidate.tick
            phase = (candidate.c2_phase+elapsed)%7
            x = anchor+C2_OFFSETS[phase]
            a4_initial = (anchor+C2_OFFSETS[candidate.c2_phase]
                          -self.a4_sizes[candidate.a4_phase]-14*candidate.tiles)
            cycles,a4_phase = divmod(candidate.a4_phase+elapsed,3)
            a4_x = a4_initial-A4_OFFSETS[candidate.a4_phase]+2*cycles+A4_OFFSETS[a4_phase]
            # Use cores here: disappearance of an ether flank alone is not a collision.
            present = self.contains(row,x,self.c2_cores[phase])
            a4_present = self.contains(row,a4_x,self.a4_cores[a4_phase])
            if present is None or a4_present is None:
                # A discarded boundary is not evidence of a destroyed glider.
                del self.pending[anchor]
                continue
            gap = x-(a4_x+self.a4_sizes[a4_phase])
            if not present and not a4_present and -28 <= gap <= 4:
                candidate.contact_seen = True
            if not candidate.contact_seen and ((not present and gap > 4)
                                              or (not a4_present and gap > 14)):
                del self.pending[anchor]  # A different interaction consumed one first.
                continue
            candidate.c2_losses.append(not present)
            candidate.a4_losses.append(not a4_present)
            if (candidate.contact_seen and len(candidate.c2_losses) == 7
                    and sum(candidate.c2_losses) >= 5 and sum(candidate.a4_losses) >= 5):
                self.add(CollisionEvent('ossifier_static_tape',row.time,anchor,
                    candidate.signature,candidate.tick,candidate.a4_phase,
                    candidate.c2_phase,candidate.tiles))
                self.completed.add(anchor)
                del self.pending[anchor]
                continue
            if elapsed > 180:
                del self.pending[anchor]
        if row.time%4 == 0:
            self.sample_pairs(row)

        for start in positions(spatial_starts(row.value,row.width)):
            self.add(CollisionEvent('F_spatial_signature',row.time,row.origin+start,SPATIAL))

        # Shift-and matching of chronological bits at fixed physical coordinates.
        # It remains aligned when the binary simulator changes its finite origin.
        shift = 0 if self.previous_origin is None else row.origin-self.previous_origin
        mask = (1 << row.width)-1
        def align(value):
            return (value >> shift) if shift >= 0 else (value << -shift)&mask
        previous = self.temporal_prefixes
        zero_bits = mask^row.value
        self.temporal_prefixes = [((align(previous[i-1]) if i else mask) &
             (row.value if symbol == '1' else zero_bits))
             for i,symbol in enumerate(TEMPORAL)]
        for start in positions(self.temporal_prefixes[-1]):
            self.add(CollisionEvent('F_temporal_signature',row.time,row.origin+start,TEMPORAL))
        self.previous_origin = row.origin
        return self.events[before:]


def export_sequences(destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    catalogue = sequence_catalogue()
    destination.write_text(json.dumps(catalogue,indent=2)+'\n')
    lines = ['Cook spatial F-production signature: '+SPATIAL,
             'Cook temporal F-production signature: '+TEMPORAL,
             'Temporal bits are oldest first at one physical cell, every CA tick.',
             '', 'Approaching A4/C2 pairs (precursors, not standalone failure verdicts):']
    for pair in catalogue['approaching_pairs']:
        lines.append(f"A4[{pair['a4_phase']}], {pair['ether_tiles']} ether tile(s), "
                     f"C2[{pair['c2_phase']}]: {pair['bits']}")
    destination.with_suffix('.txt').write_text('\n'.join(lines)+'\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Export ossifier/static-tape diagnostic sequences')
    parser.add_argument('--output',type=Path,default=Path(
                        'artifacts/legacy-visualizer-diagnostics/ossifier-static-sequences.json'))
    args = parser.parse_args()
    export_sequences(args.output)
    print(f'Exported spatial/temporal signatures and 63 approaching pairs to {args.output}')
