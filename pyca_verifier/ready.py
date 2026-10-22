"""A bounded, state-only readiness predicate; no clock or event debounce.

The rightmost stationary C2 component precedes the common head of a consuming
leader. The head is shared by ordinary and empty-appendant ready leaders; a
complete L template would exclude the latter. Pattern occurrence counts are
computed afresh from every binary row, including overlapping occurrences.
"""
from dataclasses import asdict, dataclass
from .automaton import BitRow
from .patterns import ETHER, word
from .optimized_ready_matching import PreparedHeadMatcher

C2_OFFSETS = (0, -4, 6, 2, -2, -6, -10)
READY_C2_PHASES = (1, 2, 5, 6)


@dataclass(frozen=True)
class ReadySignature:
    c2_phase: int = 1
    leader_prefix_cells = 99

    def __post_init__(self):
        if type(self.c2_phase) is not int or self.c2_phase not in READY_C2_PHASES:
            raise ValueError('c2_phase must be one of 1, 2, 5, or 6')

    @property
    def bits(self):
        return ETHER + word('C2', self.c2_phase) + ETHER*2 + word('L', 2)[:self.leader_prefix_cells]

    @property
    def c2_offset(self):
        return len(ETHER)

    @property
    def leader_offset(self):
        return len(ETHER) + len(word('C2', self.c2_phase)) + 2*len(ETHER)

    def as_dict(self):
        return {'bits': self.bits, 'cells': len(self.bits), 'c2_phase': self.c2_phase,
                'c2_cells': len(word('C2', self.c2_phase)), 'c2_offset': self.c2_offset,
                'ether_tiles': 2, 'gap_cells': 2*len(ETHER),
                'leader_phase': 2, 'leader_offset': self.leader_offset,
                'leader_prefix_cells': self.leader_prefix_cells,
                'distance_convention': 'C2 core right edge to ready-head left edge',
                'interpretation': 'Common ready head; not a complete ordinary L packet'}


@dataclass(frozen=True)
class ReadyMatch:
    tick: int
    start: int
    c2_x: int
    leader_x: int
    c2_phase: int
    c2_anchor: int

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ReadyObservation:
    tick: int
    matches: tuple[ReadyMatch, ...]

    @property
    def is_ready(self):
        """Exactly one occurrence; multiplicity is a diagnostic, not suppressed."""
        return len(self.matches) == 1


class ReadyDetector:
    def __init__(self):
        """Recognize the four fixed ready words, with no clock restriction."""
        self.signatures = tuple(ReadySignature(phase) for phase in READY_C2_PHASES)
        self.patterns = tuple((signature, signature.bits) for signature in self.signatures)
        self.matcher = PreparedHeadMatcher(self.signatures)

    def observe(self, row: BitRow) -> ReadyObservation:
        matches = []
        for index, offset in self.matcher.find(row.value, row.width):
            signature = self.signatures[index]
            start = row.origin + offset
            c2_x = start+signature.c2_offset
            matches.append(ReadyMatch(row.time, start, c2_x,
                start+signature.leader_offset, signature.c2_phase,
                c2_x-C2_OFFSETS[signature.c2_phase]))
        return ReadyObservation(row.time, tuple(sorted(matches, key=lambda match: (
            match.start, match.c2_phase))))


class ReadyTrace:
    """Record observations without changing their readiness classification."""
    def __init__(self):
        self.checked_ticks = 0
        self.last_tick = None
        self.events = []
        self.ambiguous = []
        self.consecutive_ready_ticks = []

    def observe(self, observation):
        tick = observation.tick
        if self.last_tick is not None and tick != self.last_tick+1:
            raise ValueError('Readiness must be checked at every consecutive CA tick')
        self.checked_ticks += 1
        self.last_tick = tick
        if len(observation.matches) > 1:
            self.ambiguous.append({'tick': tick,
                'matches': [match.as_dict() for match in observation.matches]})
        if observation.is_ready:
            previous = self.events[-1]['tick'] if self.events else None
            if previous is not None and tick == previous+1:
                self.consecutive_ready_ticks.append([previous, tick])
            event = observation.matches[0].as_dict()
            event.update(ready_index=len(self.events),
                         return_ticks=None if previous is None else tick-previous)
            self.events.append(event)

    def as_dict(self):
        return {'checked_ticks': self.checked_ticks, 'events': self.events,
                'ambiguous_ticks': self.ambiguous,
                'consecutive_ready_ticks': self.consecutive_ready_ticks}
