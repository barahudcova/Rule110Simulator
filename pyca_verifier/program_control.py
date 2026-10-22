"""Finite control for the ready boundary and appendant-pointer sweep.

This helper emits the program pointer and hands control to the sole tape
reader. It contains no tape-content decoder or alternative decoding path.
"""
from collections import deque
from dataclasses import dataclass, replace

from .patterns import word
from .program import compile_program
from .ready import ReadyDetector
from .transducer import LEFT_END, RIGHT_END, Transition


class BinaryRecognizer:
    """A fixed deterministic substring recognizer; labels are compiler data."""
    def __init__(self, entries, *, reverse=False):
        edges = [[-1, -1]]
        outputs = [[]]
        for bits, label in entries:
            node = 0
            for bit in (bits[::-1] if reverse else bits):
                digit = int(bit)
                target = edges[node][digit]
                if target < 0:
                    target = len(edges)
                    edges[node][digit] = target
                    edges.append([-1, -1])
                    outputs.append([])
                node = target
            if label not in outputs[node]:
                outputs[node].append(label)
        failures = [0]*len(edges)
        queue = deque()
        for digit in range(2):
            child = edges[0][digit]
            if child < 0:
                edges[0][digit] = 0
            else:
                queue.append(child)
        while queue:
            node = queue.popleft()
            for digit in range(2):
                child = edges[node][digit]
                if child < 0:
                    edges[node][digit] = edges[failures[node]][digit]
                else:
                    failures[child] = edges[failures[node]][digit]
                    outputs[child].extend(outputs[failures[child]])
                    queue.append(child)
        self.edges = tuple(tuple(edge) for edge in edges)
        self.outputs = tuple(tuple(output) for output in outputs)

    def advance(self, node, digit):
        node = self.edges[node][digit]
        return node, self.outputs[node]


@dataclass(frozen=True, slots=True)
class Control:
    mode: str
    node: int = 0
    remainder: int = 0
    remaining: int = 0
    owned: int = 0
    readiness: int = 0
    reason: str = ''


MODES = frozenset(('check-ready', 'find-ready', 'to-program', 'find-cycle',
    'to-anchor', 'count', 'to-static', 'static', 'moving', 'halt', 'fail'))
FAILURES = ('not_ready', 'ambiguous_program_anchor', 'no_intact_program_cycle',
    'lost_ready_boundary', 'no_intact_ossifier')


@dataclass(frozen=True, slots=True)
class DecodeResult:
    status: str
    tape: str | None
    appendant_index: int | None
    reason: str | None
    steps: int
    input_cells: int
    failure_offset: int | None = None
    trace: tuple = ()

    @property
    def supported(self):
        return self.status == 'decoded'

    def as_dict(self):
        return {name: getattr(self, name) for name in (
            'status', 'tape', 'appendant_index', 'reason', 'steps',
            'input_cells', 'failure_offset')}


class ProgramControl:
    """Compile only the bounded ready/program part of the binary transducer."""

    def __init__(self, appendants):
        self.appendants = tuple(appendants)
        self.program = compile_program(self.appendants)
        self.signatures = ReadyDetector().signatures
        ready = tuple((s.bits, i) for i, s in enumerate(self.signatures))
        self.ready_forward = BinaryRecognizer(ready)
        self.ready_reverse = BinaryRecognizer(ready, reverse=True)
        self.cycle_forward = BinaryRecognizer(
            (t.bits, len(t.bits)) for t in self.program.templates)
        count = [(s.bits, ('ready', i)) for i, s in enumerate(self.signatures)]
        count.extend((word(family, phase), ('leader', 0))
                     for family in ('RL', 'SL') for phase in range(30))
        self.count_reverse = BinaryRecognizer(count, reverse=True)
        self.window = max(s.leader_offset+1 for s in self.signatures)
        self.mask = (1 << self.window)-1
        self.walk_bound = max(*(len(t.bits) for t in self.program.templates),
                              *(len(s.bits) for s in self.signatures))
        self.mode_node_bounds = {'check-ready': len(self.ready_forward.edges),
            'find-ready': len(self.ready_reverse.edges),
            'find-cycle': len(self.cycle_forward.edges),
            'count': len(self.count_reverse.edges)}
        self.state_bound = (len(MODES)*max(self.mode_node_bounds.values())
            *len(self.appendants)*(self.walk_bound+1)*(1 << self.window)
            *3*(len(FAILURES)+1))

    def _valid_state(self, state):
        return (type(state) is Control and type(state.mode) is str
            and type(state.reason) is str and state.mode in MODES
            and all(type(v) is int for v in (state.node,state.remainder,
                state.remaining,state.owned,state.readiness))
            and 0 <= state.node < self.mode_node_bounds.get(state.mode,1)
            and 0 <= state.remainder < len(self.appendants)
            and 0 <= state.remaining <= self.walk_bound
            and 0 <= state.owned <= self.mask and 0 <= state.readiness <= 2
            and state.reason in ('',*FAILURES))

    @staticmethod
    def _fail(reason):
        return Transition(Control('fail', reason=reason), 'S')

    def _program_transition(self, state, symbol):
        mode = state.mode
        if mode in ('fail', 'halt'):
            return Transition(state, 'S')
        if mode == 'check-ready':
            if symbol == LEFT_END:
                if not self.program.has_unique_anchor:
                    return self._fail('ambiguous_program_anchor')
                return Transition(state, 'R')
            if symbol == RIGHT_END:
                if state.readiness != 1:
                    return self._fail('not_ready')
                return Transition(Control('find-ready'), 'L')
            node, hits = self.ready_forward.advance(state.node, int(symbol))
            return Transition(replace(state, node=node,
                readiness=min(2, state.readiness+len(hits))), 'R')
        if mode == 'find-ready':
            if symbol in (LEFT_END, RIGHT_END):
                return self._fail('lost_ready_boundary')
            node, hits = self.ready_reverse.advance(state.node, int(symbol))
            if hits:
                # The reverse match finishes at the left edge of the ready
                # word. Move to its right edge before looking for a full cycle.
                distance = len(self.signatures[hits[0]].bits)-1
                return Transition(Control('to-program', remaining=distance-1), 'R')
            return Transition(replace(state, node=node), 'L')
        if mode in ('to-program', 'to-anchor', 'to-static'):
            direction = 'L' if mode == 'to-anchor' else 'R'
            destination = {'to-program': 'find-cycle', 'to-anchor': 'count',
                           'to-static': 'static'}[mode]
            if symbol in (LEFT_END, RIGHT_END):
                return self._fail('lost_ready_boundary')
            if state.remaining:
                return Transition(replace(state, remaining=state.remaining-1), direction)
            if mode == 'to-anchor':
                # The alpha-zero raw leader at this position counts as one.
                return Transition(Control('count', remainder=1 % len(self.appendants)), 'L')
            return Transition(Control(destination, remainder=state.remainder), 'S')
        if mode == 'find-cycle':
            if symbol == RIGHT_END:
                return self._fail('no_intact_program_cycle')
            if symbol == LEFT_END:
                return self._fail('lost_ready_boundary')
            node, hits = self.cycle_forward.advance(state.node, int(symbol))
            if hits:
                if len(set(hits)) != 1:
                    return self._fail('ambiguous_program_anchor')
                return Transition(Control('to-anchor', remaining=hits[0]-2), 'L')
            return Transition(replace(state, node=node), 'R')
        if mode == 'count':
            if symbol in (LEFT_END, RIGHT_END):
                return self._fail('lost_ready_boundary')
            node, hits = self.count_reverse.advance(state.node, int(symbol))
            leaders = sum(role == 'leader' for role, _ in hits)
            recent = ((state.owned << 1) | bool(leaders)) & self.mask
            count = (state.remainder+leaders) % len(self.appendants)
            ready = tuple(index for role, index in hits if role == 'ready')
            if ready:
                signature = self.signatures[ready[0]]
                # An empty consuming head can still match its old SL core.
                # Count only leaders strictly to its right, using a bounded
                # recent-match mask, never an absolute coordinate.
                if recent & (1 << signature.leader_offset):
                    count = (count-1) % len(self.appendants)
                distance = signature.leader_offset-1
                return Transition(Control('to-static', remainder=count,
                    remaining=distance-1), 'R', (f'p{(-count) % len(self.appendants)}',))
            return Transition(replace(state, node=node, remainder=count, owned=recent), 'L')
        raise ValueError(f'Unexpected program-control mode {mode}')

    def as_dict(self):
        return {'ready_signature_count': len(self.signatures),
            'ready_signature_widths': sorted({len(s.bits) for s in self.signatures}),
            'program_templates': len(self.program.templates),
            'program_cycle_marker_tiles': self.program.cycle_marker_tiles,
            'program_marker_validation_phases': self.program.marker_validation_phases,
            'program_has_unique_anchor': self.program.has_unique_anchor,
            'uses_tick': False, 'uses_reference_cts': False,
            'uses_seed_cycle_count': False}
