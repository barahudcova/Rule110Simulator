"""Complete binary 2DFT combining program position and canonical tape sites.

The original finite ready/program recognizers locate an intact program cycle
and count leaders modulo the fixed appendant list. Two subsequent sweeps emit
static then moving symbols using LocalContentTransducer's bounded classifier.
The content boundaries are recognized by finite words, never by coordinates.

On the rightward sweep a fixed FIFO delays semantic reading by the longest
ready-leader prefix. Recognizing the ready word then identifies exactly which
queued bits belong to its leader. Those bits are discarded; the content
classifier sees precisely the cells before the leader, including its final
static symbol. No CA evolution, reference CTS, clock or expected output enters
the transition function.
"""
from dataclasses import dataclass, replace

from .program_control import BinaryRecognizer, Control, DecodeResult, FAILURES, ProgramControl
from .local_content_transducer import ContentControl, LocalContentTransducer
from .tape_patterns import auxiliary_patterns
from .transducer import FixedControlSpec, LEFT_END, RIGHT_END, Transition, TwoWayTransducer


@dataclass(frozen=True, slots=True)
class CanonicalControl:
    base: Control
    phase: str = ''
    content: ContentControl = ContentControl('static')
    boundary_node: int = 0
    ready_node: int = 0
    queue: int = 0
    queued: int = 0
    remaining: int = 0
    reason: str = ''


class Decoder(ProgramControl):
    """One finite transducer for a fixed appendant list.

    The ready and program-marker recognizers locate the semantic tape region.
    Completeness on every reachable row remains a mathematical obligation;
    finite regression checks are evidence rather than a universal proof.
    """

    # Totalization on the whole ready language R: the halting domain K of
    # this fixed finite transducer is regular. A preliminary output-free DFA
    # can decide K, rewind, then either run this decoder or emit a fixed
    # configuration (p0, empty tape). The diagnostic API keeps rejections so
    # unsupported reachable configurations remain visible. Membership must be
    # decided before emitting output, since an emitted prefix cannot retract.
    def __init__(self, appendants):
        super().__init__(appendants)
        program_bound = self.state_bound
        self.content_machine = LocalContentTransducer()
        self.ossifier_reverse = BinaryRecognizer(
            ((p.bits, len(p.bits)) for p in auxiliary_patterns() if p.kind == 'ossifier'),
            reverse=True)
        self.leader_prefixes = tuple(len(s.bits)-s.leader_offset for s in self.signatures)
        self.queue_width = max(self.leader_prefixes)
        self.queue_mask = (1 << self.queue_width)-1
        self.remaining_bound = max(self.queue_width, self.content_machine.flush_bound)
        self.reasons = tuple(dict.fromkeys((*FAILURES, *self.content_machine.reasons)))
        self.initial = CanonicalControl(Control('check-ready'))
        self.halt = CanonicalControl(Control('halt'), phase='halt')
        self.loop_states = tuple(CanonicalControl(Control('fail'), phase='fail', reason=r)
                                 for r in self.reasons)
        bound = (program_bound*self.content_machine.machine.finite_state_bound
            *10*len(self.ossifier_reverse.edges)*len(self.ready_forward.edges)
            *(1 << self.queue_width)*(self.queue_width+1)*(self.remaining_bound+1)
            *(len(self.reasons)+1))
        self.machine = TwoWayTransducer(input_alphabet=('0', '1'),
            output_alphabet=('Y', 'N', *(f'p{i}' for i in range(len(self.appendants)))),
            initial_state=self.initial, halt_state=self.halt,
            control=FixedControlSpec(bound, self._valid_full,
                'Finite ready/program control, canonical content control, finite '
                'boundary DFAs, fixed leader-prefix FIFO and bounded flush counter'),
            transition=self._canonical_transition, max_output_per_transition=1)

    def _valid_full(self, state):
        if not (type(state) is CanonicalControl and super()._valid_state(state.base)
            and type(state.phase) is str and type(state.reason) is str
            and state.phase in ('', 'static', 'static-flush', 'moving',
                                'moving-drain', 'moving-flush', 'halt', 'fail')
            and self.content_machine._valid(state.content)
            and type(state.boundary_node) is int
            and 0 <= state.boundary_node < len(self.ossifier_reverse.edges)
            and type(state.ready_node) is int
            and 0 <= state.ready_node < len(self.ready_forward.edges)
            and type(state.queue) is int and 0 <= state.queue <= self.queue_mask
            and type(state.queued) is int and 0 <= state.queued <= self.queue_width
            and type(state.remaining) is int and 0 <= state.remaining <= self.remaining_bound
            and state.reason in ('', *self.reasons)):
            return False
        # The queued-bit count describes an actual bounded FIFO; draining
        # cannot read an empty queue or produce a nonbinary input symbol.
        if state.queue >= (1 << state.queued):
            return False
        if not state.phase:
            return state.base.mode in ('check-ready', 'find-ready', 'to-program',
                'find-cycle', 'to-anchor', 'count', 'to-static')
        if state.phase in ('fail', 'halt'):
            return state.base.mode == state.phase
        expected = 'static' if state.phase.startswith('static') else 'moving'
        if (state.base.mode != expected or state.content.mode != expected
                or state.content.flush != 0):
            return False
        if state.phase == 'moving-drain':
            return state.remaining <= state.queued
        if state.phase.endswith('-flush'):
            return state.remaining <= self.content_machine.flush_bound
        return state.remaining == 0

    def _canonical_fail(self, reason):
        return Transition(CanonicalControl(Control('fail'), phase='fail', reason=reason), 'S')

    def _advance_content(self, state, digit=None):
        following, output, error = self.content_machine._advance(state.content, digit)
        return replace(state, content=following), output, error

    def _canonical_transition(self, state, symbol):
        if state.phase in ('fail', 'halt'):
            return Transition(state, 'S')
        if not state.phase:
            instruction = super()._program_transition(state.base, symbol)
            if instruction.state.mode == 'fail':
                return self._canonical_fail(instruction.state.reason)
            following = CanonicalControl(instruction.state)
            if instruction.state.mode == 'static':
                following = replace(following, phase='static')
            return Transition(following, instruction.move, instruction.output)

        if state.phase in ('static-flush', 'moving-flush'):
            if state.remaining == self.content_machine.flush_bound:
                if state.phase == 'moving-flush':
                    return Transition(self.halt, 'S')
                # We are still physically on the first cell of the O word.
                # Re-read that cell exactly once in the rightward sweep.
                return Transition(CanonicalControl(Control('moving'), phase='moving',
                                  content=ContentControl('moving')), 'S')
            following, output, error = self._advance_content(state)
            if error:
                return self._canonical_fail(error)
            return Transition(replace(following, remaining=state.remaining+1), 'S', output)

        if state.phase == 'moving-drain':
            if not state.remaining:
                return Transition(replace(state, phase='moving-flush', queue=0, queued=0), 'S')
            digit = (state.queue >> (state.queued-1)) & 1
            following, output, error = self._advance_content(state, digit)
            if error:
                return self._canonical_fail(error)
            queued = state.queued-1
            return Transition(replace(following, queue=state.queue & ((1 << queued)-1),
                queued=queued, remaining=state.remaining-1), 'S', output)

        if symbol in (LEFT_END, RIGHT_END):
            reason = 'no_intact_ossifier' if state.phase == 'static' else 'lost_ready_boundary'
            return self._canonical_fail(reason)
        digit = int(symbol)
        if state.phase == 'static':
            following, output, error = self._advance_content(state, digit)
            if error:
                return self._canonical_fail(error)
            node, boundaries = self.ossifier_reverse.advance(state.boundary_node, digit)
            following = replace(following, boundary_node=node)
            if boundaries:
                return Transition(replace(following, phase='static-flush'), 'S', output)
            return Transition(following, 'L', output)

        # Physical rightward reading runs a fixed number of cells ahead of
        # semantic reading. At recognition, the leader is still in this FIFO.
        node, ready = self.ready_forward.advance(state.ready_node, digit)
        queue = (state.queue << 1) | digit
        following = replace(state, ready_node=node, queue=queue & self.queue_mask,
                            queued=min(self.queue_width, state.queued+1))
        output = ()
        if state.queued == self.queue_width:
            following, output, error = self._advance_content(following, queue >> self.queue_width)
            if error:
                return self._canonical_fail(error)
        if ready:
            prefixes = {self.leader_prefixes[i] for i in ready}
            if len(prefixes) != 1:
                return self._canonical_fail('lost_ready_boundary')
            remaining = following.queued-next(iter(prefixes))
            if remaining < 0:
                return self._canonical_fail('lost_ready_boundary')
            return Transition(replace(following, phase='moving-drain', remaining=remaining),
                              'S', output)
        return Transition(following, 'R', output)

    def decode(self, row_or_word, *, trace=False, memoize_transitions=True):
        text = row_or_word if isinstance(row_or_word, str) else row_or_word.word()
        result = self.machine.run(text, trace=trace, detect_loops=False,
            memoize_transitions=memoize_transitions, loop_states=self.loop_states,
            max_steps=14*(len(text)+self.walk_bound+self.content_machine.flush_bound+2))
        if not result.halted:
            return DecodeResult('unsupported', None, None,
                result.state.reason or result.status, result.steps, len(text),
                result.head-1, result.trace)
        return DecodeResult('decoded', ''.join(result.output[1:]),
            int(result.output[0][1:]), None, result.steps, len(text), trace=result.trace)

    def as_dict(self):
        return {**super().as_dict(), 'model': 'Complete canonical-position binary 2DFT',
            'full_decoder_is_2DFT': True,
            'content_transducer': self.content_machine.as_dict(),
            'right_boundary_fifo_cells': self.queue_width,
            'left_boundary': 'Rightmost intact O word before the consuming ready leader',
            'right_boundary': 'Cell immediately before the leader in the unique ready word',
            'finite_state_bound_log2_ceiling': self.machine.finite_state_bound.bit_length()}
