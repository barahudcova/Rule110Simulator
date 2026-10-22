"""Fixed finite program words and state-only appendant phase recognition.

An intact cycle starts at the ordinary raw leader for appendant zero and ends
after the next such leader.  The program is fixed when these words are compiled;
the input row, its clock, and its encoder trace never change the catalogue.

The encoder's generated tables fix the program joins. Complete cycle words
are evolved as one bounded Rule 110 window and cropped at their complete
exterior leaders, retaining every phase and the appendant-zero marker.
"""
from dataclasses import dataclass
from functools import lru_cache

from .automaton import BitRow, step
from .encoder import Initialization, PROGRAM_CYCLE_MARKER_TILES, make_encoder
from .matching import ReadyMatcher
from .patterns import ETHER, word


@dataclass(frozen=True, slots=True)
class LeaderPacket:
    start: int
    family: str
    phase: int
    cells: int

    @property
    def end(self):
        return self.start + self.cells


@dataclass(frozen=True, slots=True)
class CycleTemplate:
    bits: str
    first_leader_phase: int
    last_leader_offset: int
    last_leader_phase: int

    @property
    def cells(self):
        return len(self.bits)


@dataclass(frozen=True, slots=True)
class IntactCycle:
    start: int
    end: int
    template_index: int
    first_leader_phase: int


@dataclass(frozen=True, slots=True)
class ProgramCatalogue:
    appendants: tuple[str, ...]
    templates: tuple[CycleTemplate, ...]
    seed_variants: int
    rotational_symmetries: tuple[int, ...]
    cycle_marker_tiles: int = PROGRAM_CYCLE_MARKER_TILES
    marker_validation_phases: int = 210

    @property
    def has_unique_rotation(self):
        return not self.rotational_symmetries

    @property
    def has_unique_anchor(self):
        """The binary catalogue, rather than symbolic rotation, identifies zero."""
        return self.has_unique_rotation or (self.cycle_marker_tiles > 0
                                            and self.marker_validation_phases == 210)


_PACKET_LABELS = tuple((family, phase) for family in ("RL", "SL")
                       for phase in range(30))
_PACKET_MATCHER = ReadyMatcher(tuple(word(family, phase)
                                    for family, phase in _PACKET_LABELS))


def find_leaders(row: BitRow):
    """All complete raw RL/SL packets, without imposing an ether flank.

    Ether immediately adjacent to a packet changes alignment during evolution
    and between neighboring empty appendants.  Adding a fixed ether flank to
    these words incorrectly drops otherwise complete SL packets.
    """
    packets = []
    for index, offset in _PACKET_MATCHER.find(row.value, row.width):
        family, phase = _PACKET_LABELS[index]
        packets.append(LeaderPacket(row.origin + offset, family, phase,
                                    len(_PACKET_MATCHER.patterns[index])))
    return tuple(sorted(packets, key=lambda packet: packet.start))


@lru_cache(maxsize=None, typed=True)
def compile_program(appendants: tuple[str, ...]):
    """Compile bounded binary anchors for a fixed catalogue-based program.

    The encoder's boundary phase has thirty states.  Thirty-three full cycles
    expose its transient and every reachable cycle boundary, with a successor
    boundary available for each extracted block.  A 210-tick window covers the
    common temporal period of the thirty-phase packets and fourteen-cell ether.
    The padding is used only to generate exact bounded words; it is discarded.

    A repeated rotation of the symbolic list is reported explicitly. The fixed
    four-tile marker identifies appendant zero even for identical appendants.
    Each complete cycle word
    includes the marker before its terminal zero leader. The complete encoded
    reservoir is checked at all 210 joint temporal phases: only zero leaders
    may begin a matching cycle, and each must match exactly once.
    """
    if not isinstance(appendants, tuple):
        raise TypeError("appendants must be a tuple")
    initialization = Initialization("Y", appendants)
    size = len(appendants)
    cycle_marker_tiles = PROGRAM_CYCLE_MARKER_TILES
    encoder = make_encoder(initialization)
    encoded = BitRow.from_word(encoder.program(cycles=33))
    packets = find_leaders(encoded)
    if len(packets) != 33 * size:
        raise ValueError("Program packet boundaries are not uniquely recognizable")

    seeds = set()
    text = encoded.word()
    for index in range(size - 1, len(packets) - size, size):
        first, last = packets[index], packets[index + size]
        if first.family != "RL" or last.family != "RL":
            raise ValueError("The first appendant requires ordinary raw leaders")
        seeds.add(text[first.start:last.end])

    templates = {}
    for seed in sorted(seeds):
        row = BitRow.from_word(ETHER * 32 + seed + ETHER * 32)
        for _ in range(210):
            ordinary = tuple(packet for packet in find_leaders(row)
                             if packet.family == "RL")
            if len(ordinary) < 2:
                raise ValueError("An intact program cycle lost an exterior leader")
            first, last = ordinary[0], ordinary[-1]
            text = row.word()
            bits = text[first.start - row.origin:last.end - row.origin]
            templates[bits] = CycleTemplate(bits, first.phase,
                last.start - first.start, last.phase)
            row = step(row)

    symmetries = tuple(index for index in range(1, size)
                      if appendants[index:] + appendants[:index] == appendants)
    catalogue = ProgramCatalogue(appendants,
        tuple(templates[bits] for bits in sorted(templates)), len(seeds), symmetries,
        cycle_marker_tiles, 210)
    _validate_marked_anchors(encoded.word(), size, catalogue)
    return catalogue


def _validate_marked_anchors(program_word, size, catalogue):
    """Check bounded compiler-generated words, never inspect a decoder input.

    Padding contains every exterior leader's 210-tick backward light cone.
    Thirty-three cycles enumerate the encoder's boundary transient and its
    thirty possible phase states, with a successor for each extracted cycle.
    This exact check also rejects accidental matches of a shorter template
    inside a cycle or matches beginning at a nonzero raw leader.
    """
    row = BitRow.from_word(ETHER*32 + program_word + ETHER*32)
    for phase in range(210):
        packets = find_leaders(row)
        if len(packets) != 33*size:
            raise ValueError("A marked program lost a recognizable raw leader")
        expected = tuple(packets[index].start for index in
                         range(size-1, len(packets)-size, size))
        observed = tuple(match.start for match in find_intact_cycles(row, catalogue))
        if observed != expected:
            raise ValueError("The cycle marker does not uniquely identify appendant "
                             f"zero at native phase {phase}")
        row = step(row)


@lru_cache(maxsize=None)
def _cycle_matcher(catalogue):
    return ReadyMatcher(tuple(template.bits for template in catalogue.templates))


def find_intact_cycles(row: BitRow, catalogue: ProgramCatalogue):
    """Locate complete fixed catalogue words using only this binary row."""
    matches = []
    for index, offset in _cycle_matcher(catalogue).find(row.value, row.width):
        template = catalogue.templates[index]
        start = row.origin + offset
        matches.append(IntactCycle(start, start + template.cells, index,
                                    template.first_leader_phase))
    return tuple(sorted(matches, key=lambda match: match.start))


class ProgramPhaseError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProgramPhase:
    appendant_index: int
    anchor_x: int
    leaders_to_anchor: int
    template_index: int


def recognize_program_phase(row: BitRow, ready_leader_x: int,
                            catalogue: ProgramCatalogue):
    """Diagnostic realization of the finite-state leader-counting sweep.

    The first intact list to the right of the consuming head supplies its
    appendant-zero anchor. Count complete intervening leaders including that
    anchor, then negate the count modulo the fixed program size. A 2DFT only
    needs the remainder; the full count here is retained as test evidence.

    This helper does not establish the entire decoder or observation map.
    Missing intact cycles and indistinguishable rotations are rejected rather
    than replaced by a tick counter, seed-cycle count, or reference CTS state.
    """
    if not catalogue.has_unique_anchor:
        raise ProgramPhaseError("The appendant list has indistinguishable rotations; "
                                "a distinguishable phase marker is required")
    anchors = tuple(match for match in find_intact_cycles(row, catalogue)
                    if match.start > ready_leader_x)
    if not anchors:
        raise ProgramPhaseError("No complete intact appendant list remains to the right "
                                "of the ready leader")
    anchor = anchors[0]
    count = sum(ready_leader_x < packet.start <= anchor.start
                for packet in find_leaders(row))
    if not count:
        raise ProgramPhaseError("The intact-cycle anchor has no recognizable raw leader")
    return ProgramPhase((-count) % len(catalogue.appendants), anchor.start,
                        count, anchor.template_index)
