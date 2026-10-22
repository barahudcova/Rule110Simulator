"""The fixed catalogue-based Rule 110 encoder used by this verifier.

Coordinates increase left to right; the logical tape is reversed spatially
because its consuming leader approaches from the right. The single geometry
uses a 684-cell initial tape pitch, groups of six ossifier packets, and a
four-ether-tile marker before each future appendant-zero leader. Nonempty
tapes are composed directly at a ready configuration, without CA evolution.
"""
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json

from .automaton import BitRow
from .patterns import ETHER, TABLES, load, word


PROGRAM_CYCLE_MARKER_TILES = 4


@dataclass(frozen=True, slots=True)
class _Geometry:
    """Internal fixed dimensions; these are not encoder options."""

    initial_symbol_extra_tiles: int = field(default=32, init=False)
    moving_symbol_extra_tiles: int = field(default=0, init=False)
    ossifier_group_extra_tiles: int = field(default=112, init=False)
    first_ossifier_extra_tiles_per_symbol: int = field(default=0, init=False)
    minimum_long_ossifier_gap_tiles: int = field(default=0, init=False)
    ossifier_group_size: int = field(default=6, init=False)

    def as_dict(self):
        return asdict(self)


GEOMETRY = _Geometry()


@dataclass(frozen=True)
class Initialization:
    tape: str = "YYN"
    appendants: tuple[str, ...] = ("YNNYNN",)

    def __post_init__(self):
        object.__setattr__(self, "appendants", tuple(self.appendants))
        if any(c not in "YN" for c in self.tape):
            raise ValueError("Tape must contain only Y and N")
        if not self.appendants or not self.appendants[0]:
            raise ValueError("The encoder requires a nonempty first appendant")
        if any(c not in "YN" for a in self.appendants for c in a):
            raise ValueError("Appendants must contain only Y and N (or be empty)")
        if any(len(a) % 6 for a in self.appendants):
            raise ValueError("Appendant lengths must be multiples of six (empty is allowed)")


def _base_ossifier_gap(initialization):
    """The phase-table gap, before the fixed geometric lower bound."""
    text = "".join(initialization.appendants)
    nonempty = sum(bool(a) for a in initialization.appendants)
    empty = len(initialization.appendants) - nonempty
    return ((76*text.count("Y") + 80*text.count("N")
             + 60*nonempty + 43*empty)//4)*8 + 3


class Encoder:
    """Compose ready tape, program, and ossifier reservoirs in one geometry.

    ``program`` and ``ossifiers`` continue their phase state across calls, so
    a visualization can replenish its reservoirs with the same construction.
    The verifier instead chooses finite reservoir sizes in ``build_seed``.
    """

    OSS = {0: (1, 1), 1: (2, 0), 2: (0, 0)}

    def __init__(self, initialization=Initialization()):
        if not isinstance(initialization, Initialization):
            raise TypeError("initialization must be an Initialization")
        self.initialization = initialization
        self.phase = 20  # L[2] ends with ether phase (2 + 18) % 30.
        self.oss_phase = 2
        self.ossifier_count = 0
        self.trace = []
        self.cycle_marker_tiles = PROGRAM_CYCLE_MARKER_TILES
        self.inherited_long_distance = _base_ossifier_gap(initialization)
        self.initial_gap_certificate = None
        from .spacing_geometry import compact_long_gap_certificate
        self.long_gap_certificate = compact_long_gap_certificate(initialization)
        self.short_distance = self.long_gap_certificate.minimum_short_gap_tiles
        # Four program ether tiles add fourteen O-gap tiles, preserving the
        # phase-table residue. The certificate supplies the geometric bound.
        requested = max(self.long_gap_certificate.minimum_gap_tiles,
                        self.inherited_long_distance
                        + GEOMETRY.ossifier_group_extra_tiles + 14)
        self.long_distance = requested + (self.inherited_long_distance-requested) % 14
        head = initialization.tape[:1]
        self.initial_symbol_phase = 4 if head == 'N' else 0
        self.preparation_ticks = 480 if head == 'N' else (420 if head else 0)
        self.normalization_shift_cells = 2 if head == 'N' else 0
        self.ossifier_prefix_shift_tiles = 23 if head == 'N' else (20 if head else 0)

    def appendant(self, symbols, phase):
        """Encode one appendant using the fixed principal/standard tables."""
        result = []
        for index, symbol in enumerate(symbols):
            j, ethers = TABLES["yn"][str(phase)]["0"]
            result.append(ETHER*ethers + word("PC" if index == 0 else "SC", j))
            if index == 0:
                j = (j+14) % 30
            phase, ethers = TABLES["yn"][str(j)][symbol]
            result.append(ETHER*ethers + word("SC", phase))
        return "".join(result), phase

    def program(self, cycles=1):
        """Append whole program rotations, continuing the boundary phase.

        The ``sl_sl`` table supplies the repaired consecutive-empty transition.
        Every future raw leader for appendant zero has the fixed marker gap.
        """
        if cycles < 1:
            raise ValueError("cycles must be positive")
        appendants = self.initialization.appendants * cycles
        size = len(self.initialization.appendants)
        first, self.phase = self.appendant(appendants[0], self.phase)
        result = [first, ETHER*8]
        self.trace.append({'transition': 'first', 'appendant': appendants[0]})
        for index, (previous, current) in enumerate(zip(appendants, appendants[1:]), 1):
            if index % size == 0:
                result.append(ETHER*self.cycle_marker_tiles)
            table = ('sl_sl' if not previous else 'sc_sl') if not current else (
                'sl_rl' if not previous else 'rl')
            phase, ethers = TABLES[table][str(self.phase)]
            result.append(ETHER*ethers + word('SL' if not current else 'RL', phase))
            self.trace.append({'transition': table, 'appendant': current,
                               'input_phase': self.phase, 'phase': phase, 'ethers': ethers,
                               'cycle_marker_tiles': self.cycle_marker_tiles if index % size == 0 else 0})
            self.phase = phase
            if current:
                self.phase = (phase+22) % 30
                encoded, self.phase = self.appendant(current, self.phase)
                result.extend((encoded, ETHER*8))
        table = 'sl_rl' if not appendants[-1] else 'rl'
        phase, ethers = TABLES[table][str(self.phase)]
        result.append(ETHER*self.cycle_marker_tiles + ETHER*ethers + word('RL', phase))
        self.phase = (phase+22) % 30
        return ''.join(result)

    def tape(self):
        """Static symbols in the common phase selected by the first letter."""
        symbols = self.initialization.tape[::-1]
        result = [ETHER*3]
        for index, symbol in enumerate(symbols):
            result.append(ETHER + word(symbol, self.initial_symbol_phase))
            if index < len(symbols)-1:
                result.append(ETHER*((6 if symbol == 'Y' else 7)
                                    + GEOMETRY.initial_symbol_extra_tiles))
        return ''.join(result)

    def ossifiers(self, count):
        """Prepend packets in groups of six without restarting their phase."""
        result = ''
        for _ in range(count):
            self.ossifier_count += 1
            self.oss_phase, ethers = self.OSS[self.oss_phase]
            first_in_group = (self.ossifier_count-1) % 6 == 0
            distance = self.long_distance if first_in_group else self.short_distance
            result = word('O', self.oss_phase)+ETHER*(ethers+distance)+result
        return result

    def initial(self, width=4500, padding=840):
        """Build seven ossifier packets, a ready tape, and the program prefix.

        ``width`` determines only the number of complete program rotations;
        ``padding`` counts ether tiles at each exterior boundary. The prepared
        leader starts two ether tiles from the last C2 core for either Y or N.
        All ossifier packets are translated together to reach that ready cut.
        """
        tape = self.initialization.tape
        rules = self.initialization.appendants
        first = next((i for i, c in enumerate(tape)
                      if c == "Y" and rules[i % len(rules)]), len(tape))
        distance = len(tape)*28 + max(map(len, rules))*150*first + 139
        from .spacing_geometry import compact_initial_gap_certificate
        self.initial_gap_certificate = compact_initial_gap_certificate(self.initialization)
        if self.initial_gap_certificate is not None:
            distance = self.initial_gap_certificate.selected_guard_tiles
        self.oss_phase = 2
        self.ossifier_count = 6
        oss = word("O", 2) + ETHER*distance
        for _ in range(5):
            self.oss_phase, ethers = self.OSS[self.oss_phase]
            oss = word("O", self.oss_phase) + ETHER*(ethers+self.short_distance) + oss
        oss = ETHER*3 + self.ossifiers(1) + oss
        prefix = ETHER*(padding+3) + oss
        encoded_tape = self.tape()
        center = len(prefix) + len(encoded_tape)//2
        self.phase = 20
        self.trace.clear()
        cycles = width // (sum(map(len, rules))*600) + 1
        program = self.program(cycles)
        leader_gap = 2 if tape else 4
        if tape:
            advance = self.ossifier_prefix_shift_tiles*len(ETHER)
            if not prefix.endswith(ETHER*self.ossifier_prefix_shift_tiles):
                raise AssertionError('The initial ossifier guard is too short')
            prefix = ETHER*self.ossifier_prefix_shift_tiles + prefix[:-advance]
        return (prefix + encoded_tape + ETHER*leader_gap + word("L", 2)
                + program + ETHER*(padding+3)), center


def make_encoder(initialization=Initialization()):
    """Create the sole supported encoder, with fresh reservoir phase state."""
    return Encoder(initialization)


@dataclass(frozen=True, slots=True)
class EncodedSeed:
    """A fixed binary seed and reproducibility metadata, independent of a view."""

    row: BitRow
    center: int
    metadata: dict


def build_seed(initialization=Initialization(), program_cycles=8,
               extra_ossifiers=20, padding_cells=60000):
    """Encode a ready configuration with explicit finite reservoirs.

    ``program_cycles`` counts whole appendant rotations. Seven ossifier packets
    are present before adding ``extra_ossifiers``. Exterior padding rounds up
    to complete fourteen-cell ether tiles. All calls use the same geometry,
    cycle marker, phase tables, and readiness cut.
    """
    if not isinstance(initialization, Initialization):
        raise TypeError("initialization must be an Initialization")
    for name, value, minimum in (
            ("program_cycles", program_cycles, 1),
            ("extra_ossifiers", extra_ossifiers, 0),
            ("padding_cells", padding_cells, 0)):
        if type(value) is not int:
            raise TypeError(f"{name} must be an integer")
        if value < minimum:
            raise ValueError(f"{name} must be at least {minimum}")
    padding_tiles = (padding_cells + len(ETHER) - 1) // len(ETHER)
    encoder = make_encoder(initialization)
    program_scale = sum(map(len, initialization.appendants)) * 600
    text, center = encoder.initial(
        width=program_scale*(program_cycles-1), padding=padding_tiles)
    ossifier_start = len(ETHER)*(padding_tiles+6+encoder.ossifier_prefix_shift_tiles)
    original_oss_phase = encoder.oss_phase
    if not text.startswith(word("O", original_oss_phase), ossifier_start):
        raise AssertionError("The seed's leftmost ossifier layout changed")
    extra = encoder.ossifiers(extra_ossifiers)
    text = text[:ossifier_start] + extra + text[ossifier_start:]
    center += len(extra)
    row = BitRow.from_word(text)
    metadata = {
        "source_hash": load("source")["source_hash"],
        "source_hash_scope": "historical upstream snapshot; not this encoder release",
        "phase_tables_sha256": sha256(json.dumps(TABLES, sort_keys=True,
            separators=(",", ":")).encode("ascii")).hexdigest(),
        "encoding": "ready",
        "program_layout": "seamless-v1",
        "program_cycle_marker_tiles": PROGRAM_CYCLE_MARKER_TILES,
        "tape": initialization.tape,
        "appendants": list(initialization.appendants),
        "cycles": program_cycles,
        "extra_ossifiers": extra_ossifiers,
        "ossifier_packets": 7+extra_ossifiers,
        "padding_requested_cells": padding_cells,
        "padding_tiles": padding_tiles,
        "padding_cells": padding_tiles*len(ETHER),
        "phase": encoder.phase,
        "oss_phase": encoder.oss_phase,
        "original_oss_phase": original_oss_phase,
        "long_ossifier_distance_tiles": encoder.long_distance,
        "short_ossifier_distance_tiles": encoder.short_distance,
        "ossifier_group_size": GEOMETRY.ossifier_group_size,
        "spacing": GEOMETRY.as_dict(),
        "tape_center": center,
        "initial_width": row.width,
        "seed_sha256": sha256(text.encode("ascii")).hexdigest(),
        "ready_encoding": {
            'supported': bool(initialization.tape),
            'reason': None if initialization.tape else 'empty_tape_has_no_c2',
            'initial_symbol_phase': encoder.initial_symbol_phase,
            'gap_cells': 28 if initialization.tape else None,
            'anchor_distance_cells': 41 if initialization.tape else None,
            'local_leader_preparation_ticks': encoder.preparation_ticks,
            'normalization_shift_cells': encoder.normalization_shift_cells,
            'ossifier_shift_cells': encoder.ossifier_prefix_shift_tiles*len(ETHER),
            'construction': 'Direct catalogue composition; no Rule 110 warm-up',
        },
        "long_gap_geometry": encoder.long_gap_certificate.as_dict(),
        "initial_gap_geometry": (encoder.initial_gap_certificate.as_dict()
            if encoder.initial_gap_certificate is not None else {
                'productive_trajectory_hypothesis_applicable': False,
                'reason': 'no productive read exists in the initial tape',
                'global_CA_embedding_proved': False,
            }),
    }
    return EncodedSeed(row, center, metadata)
