"""Canonical-position two-way finite decoder of a delimited content word.

Each sweep classifies one designated position at a time, after fixed lookahead.
Static words designate a C2 anchor; moving words designate their last cell;
converting words designate the end of their nonether core. A conversion emits
once in the static sweep and suppresses descriptions anchored inside it.

The rightward sweep also remembers the end of the last owned core: either an
emitted moving symbol or a conversion already emitted on the static sweep.
Uniformly spaced program components can produce a matching word across the
boundary between two moving symbols. Such a word shares a core with the
previously owned symbol and is skipped. Remembering ownership across input
positions, rather than reselecting it in each local window, preserves the
pairing through arbitrarily long trains. This rule requires that consecutive
real symbols have disjoint cores and that the first unclaimed match is real.

In particular, conversion recognition is required to establish that first
match. If a partial conversion is omitted from the catalogue, a word spanning
its remaining E gliders and the next symbol can start the wrong pairing.
Adding more overlap suppression cannot repair that missing semantic owner.
The V4 conversion extension is generated from independently completed local
O/garbage/data collisions; expected CTS tapes never label its words.

There are no larger collision-witness obligations or garbage coverage checks.
Non-emitting neighborhoods produce epsilon. Correctness requires the finite
local completeness/no-false-output checks on the intended representation
language. Other binary words can decode arbitrarily, including to empty.
Conflicting labels still reject. No Rule 110 evolution or CTS history is used.
"""
from dataclasses import dataclass, replace
from functools import lru_cache

from .canonical_content_patterns import (
    CanonicalHit, CanonicalPrimitive, canonical_primitives, canonicalize_symbols)
from .canonical_ossification import canonicalize_frontiers, suppress_converting_symbols
from .literal_matcher import LiteralMatcher
from .ossification_patterns import frontier_patterns
from .transducer import FixedControlSpec, LEFT_END, RIGHT_END, Transition, TwoWayTransducer


@dataclass(frozen=True, slots=True)
class ContentControl:
    mode: str
    tail: int = 0
    warm: int = 0
    pending: tuple = ()
    flush: int = 0
    reason: str = ''
    claimed_right: int | None = None


@dataclass(frozen=True, slots=True)
class ContentMachineResult:
    status: str
    static: tuple
    moving: tuple
    reason: str | None
    steps: int


@lru_cache(maxsize=1)
def content_primitives():
    """Fixed semantic words, without the old larger coverage witnesses."""
    return canonical_primitives()+tuple(CanonicalPrimitive(
        p.bits, 'frontier', p.symbol, p.core_offset, p.core_cells,
        p.anchor_offset) for p in frontier_patterns())


class LocalContentTransducer:
    """Classify one delayed position per cell; emit at most one symbol.

    Retained coordinates are relative to the head. Radius and retention are
    compiler constants, independent of tape length. Endmarker transitions
    drain the same bounded classifier without inserting fictional input bits.
    """
    reasons = ('conflicting_symbols', 'ambiguous_anchor', 'unexpected_endmarker')

    def __init__(self):
        self.primitives = content_primitives()
        self.forward_matcher = LiteralMatcher(self.primitives, reverse=True)
        self.reverse_matcher = LiteralMatcher(self.primitives)
        self.width = self.forward_matcher.width
        self.mask = (1 << self.width)-1
        # Two word widths include a symbol's aliases and any conversion that
        # claims them, together with each description's complete context.
        self.radius = 2*self.width+14
        self.retention = self.radius+2*self.width+32
        self.flush_bound = self.radius+14
        self.coordinate_bound = self.retention+2*self.width+32
        # Six kind/label choices at each bounded anchor; equal keys coalesce.
        # This is a derived cardinality, not an empirical unresolved-list cap.
        self.pending_bound = 6*(2*self.coordinate_bound+1)
        self.initial = ContentControl('seek')
        self.halt = ContentControl('halt')
        self.fail_states = tuple(ContentControl('fail', reason=r) for r in self.reasons)
        coordinate_values = 2*self.coordinate_bound+1
        slot_bits = (1+coordinate_values**4).bit_length()
        exponent = self.width+self.pending_bound*slot_bits
        bound = (8*(len(self.reasons)+1)*(self.width+1)*(self.flush_bound+1)) << exponent
        # None, or one endpoint in [-coordinate_bound, coordinate_bound].
        # It is relative to the reading head, not an unbounded tape position.
        bound *= 2*self.coordinate_bound+2
        self.machine = TwoWayTransducer(input_alphabet=('0', '1'),
            output_alphabet=('Y', 'N', '|'), initial_state=self.initial,
            halt_state=self.halt,
            control=FixedControlSpec(bound, self._valid,
                'Fixed binary register, bounded relative canonical detections, '
                'bounded moving-core ownership endpoint, fixed-radius delayed '
                'position and bounded endmarker drain'),
            transition=self.transition, max_output_per_transition=1)

    def _valid(self, state):
        if not (type(state) is ContentControl
                and type(state.mode) is str and type(state.reason) is str
                and state.mode in ('seek', 'static', 'moving', 'fail', 'halt')
                and state.reason in ('', *self.reasons)
                and type(state.tail) is int and 0 <= state.tail <= self.mask
                and type(state.warm) is int and 0 <= state.warm <= self.width
                and type(state.flush) is int and 0 <= state.flush <= self.flush_bound
                and type(state.pending) is tuple and len(state.pending) <= self.pending_bound):
            return False
        if state.mode not in ('static', 'moving') and state.pending:
            return False
        if state.claimed_right is not None and (
                state.mode != 'moving' or type(state.claimed_right) is not int
                or not -self.retention <= state.claimed_right <= self.coordinate_bound):
            return False
        previous_key=None
        for h in state.pending:
            if (type(h) is not CanonicalHit
                    or type(h.kind) is not str or type(h.symbol) is not str
                    or h.kind not in ('static','moving','frontier')
                    or h.symbol not in ('Y','N')
                    or any(type(v) is not int or abs(v)>self.coordinate_bound
                           for v in (h.left,h.right,h.lo,h.hi,h.anchor))):
                return False
            # These are invariants of literal matches and their same-anchor
            # unions. They make the declared control domain closed under a
            # coordinate shift, not merely finite along observed executions.
            if (not h.left <= h.lo < h.hi <= h.right
                    or any(abs(v-h.anchor) > self.width+14
                           for v in (h.left, h.right, h.lo, h.hi))
                    or (h.kind == 'frontier' and h.hi != h.anchor)
                    or (h.kind == 'moving' and h.anchor != h.right-1)):
                return False
            if state.mode == 'moving':
                if not -self.retention <= h.anchor <= 14:
                    return False
            elif not -14 <= h.anchor <= self.retention:
                return False
            key=h.kind,h.symbol,h.anchor
            if previous_key is not None and key<=previous_key:
                return False
            previous_key=key
        return True

    def _fail(self, reason):
        return Transition(ContentControl('fail', reason=reason), 'S')

    def _advance(self, state, digit=None):
        """Advance the bounded observation by one physical or virtual cell."""
        forward=state.mode=='moving'
        shift=-1 if forward else 1
        merged={}
        claimed_right=state.claimed_right
        if claimed_right is not None:
            claimed_right += shift
            if claimed_right < -self.retention:
                # An endpoint this far behind cannot overlap any candidate
                # at the delayed classification site, even with its longest
                # finite context. No global count or history is retained.
                claimed_right=None

        def add(hit):
            key=hit.kind,hit.symbol,hit.anchor
            previous=merged.get(key)
            if previous is None:
                merged[key]=hit
            else:
                merged[key]=CanonicalHit(hit.kind,hit.symbol,
                    min(previous.left,hit.left),max(previous.right,hit.right),
                    min(previous.lo,hit.lo),max(previous.hi,hit.hi),hit.anchor)

        for hit in state.pending:
            anchor=hit.anchor+shift
            if (anchor < -self.retention if forward else anchor > self.retention):
                continue
            add(CanonicalHit(hit.kind,hit.symbol,hit.left+shift,hit.right+shift,
                             hit.lo+shift,hit.hi+shift,anchor))
        tail,warm=state.tail,state.warm
        if digit is not None:
            matcher=self.forward_matcher if forward else self.reverse_matcher
            tail,warm,indices=matcher.advance(tail,warm,digit)
            for index in indices:
                p=self.primitives[index]
                left=1-len(p.bits) if forward else 0
                add(CanonicalHit(p.kind,p.symbol,left,left+len(p.bits),
                    left+p.offset,left+p.offset+p.cells,left+p.anchor_offset))
        pending=tuple(merged[key] for key in sorted(merged))
        center=-self.radius if forward else self.radius
        output=()
        if any(h.anchor==center for h in pending):
            symbols,errors=canonicalize_symbols(pending)
            frontiers,frontier_errors=canonicalize_frontiers(pending)
            symbols,ownership_errors=suppress_converting_symbols(frontiers,symbols)
            if errors or frontier_errors or ownership_errors:
                return state,(), 'conflicting_symbols'
            if forward:
                for frontier in frontiers:
                    if frontier.anchor == center:
                        # A conversion already emitted on the static sweep
                        # also owns its remaining moving gliders. A word
                        # crossing from those gliders into the next packet
                        # can end outside the frontier, escaping anchor-only
                        # suppression. Carry the frontier's endpoint forward
                        # so that such a word cannot start the wrong pairing.
                        claimed_right = (frontier.hi if claimed_right is None
                                         else max(claimed_right, frontier.hi))
            role='moving' if forward else 'static'
            at_center=[h for h in (*symbols,*frontiers) if h.anchor==center
                and ('static' if h.kind=='frontier' else h.kind)==role]
            if len(at_center)>1:
                return state,(), 'ambiguous_anchor'
            if at_center:
                hit=at_center[0]
                if not forward or claimed_right is None or hit.lo >= claimed_right:
                    output=(hit.symbol,)
                    if forward:
                        # Compare nonether cores: two independent literal
                        # words may overlap harmlessly in their ether guards.
                        claimed_right=hit.hi
        return replace(state,tail=tail,warm=warm,pending=pending,
                       claimed_right=claimed_right),output,None

    def transition(self,state,symbol):
        if state.mode in ('fail', 'halt'):
            return Transition(state,'S')
        if state.mode=='seek':
            if symbol==RIGHT_END:
                return Transition(ContentControl('static'),'L')
            return Transition(state,'R')
        if symbol in (LEFT_END,RIGHT_END):
            if ((state.mode == 'static' and symbol == RIGHT_END)
                    or (state.mode == 'moving' and symbol == LEFT_END)):
                return self._fail('unexpected_endmarker')
            if state.flush==self.flush_bound:
                if state.mode=='static':
                    return Transition(ContentControl('moving'),'R',('|',))
                return Transition(self.halt,'S')
            following,output,error=self._advance(state)
            if error:
                return self._fail(error)
            return Transition(replace(following,flush=state.flush+1),'S',output)
        following,output,error=self._advance(state,int(symbol))
        if error:
            return self._fail(error)
        return Transition(following,'R' if state.mode=='moving' else 'L',output)

    def decode(self,bits,*,trace=False):
        result=self.machine.run(bits,trace=trace,detect_loops=False,
            loop_states=self.fail_states,max_steps=3*len(bits)+2*self.flush_bound+12,
            memoize_transitions=True)
        if not result.halted:
            return ContentMachineResult('unrecognized',(),(),
                result.state.reason or result.status,result.steps)
        divider=result.output.index('|')
        return ContentMachineResult('decoded',result.output[:divider],
                                    result.output[divider+1:],None,result.steps)

    def as_dict(self):
        return {'model':'Canonical-position finite content 2DFT',
            'primitive_words':len(self.primitives),'maximum_width':self.width,
            'classification_radius':self.radius,'retained_anchor_distance':self.retention,
            'maximum_pending':self.pending_bound,'maximum_output_per_transition':1,
            'moving_ownership':'Conversions and emitted moving symbols claim their '
                'cores; skip later matches overlapping the last owned core; '
                'retain one bounded relative endpoint',
            'finite_state_bound_log2_ceiling':self.machine.finite_state_bound.bit_length(),
            'output_order':'static right-to-left, separator, moving left-to-right',
            'domain':'Semantic local classification; non-emitting contexts give epsilon; '
                'conflicting designated labels reject',
            'completeness':'Requires local vocabulary completeness, disjoint real moving '
                'cores, correct first-unclaimed pairing, and the conversion handoff '
                'invariant; finite regression tests do not establish all reachable rows'}
