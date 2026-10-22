"""Exact affine spacing bounds for the compact encoder.

The calibration comes from native Rule 110 collisions, not from a CTS oracle.
Encoding performs integer arithmetic, without CA evolution. These certificates
prove geometric inequalities in the intended FIFO elementary collision network.
Embedding that network in every complete CA trajectory is a separate invariant.
"""
from dataclasses import asdict, dataclass
from functools import lru_cache
from hashlib import sha256
import json
from .encoder import (GEOMETRY, PROGRAM_CYCLE_MARKER_TILES, Initialization,
                      _base_ossifier_gap)
from .patterns import DATA, TABLES, word


def _ceil_div(n, d):
    return -(-n // d)


def _round_up(n, residue, period):
    return n + (residue-n) % period


@lru_cache(maxsize=1)
def calibration():
    data = json.loads((DATA/'encoder_geometry.json').read_text())
    if data['format_version'] != 1:
        raise ValueError('Unsupported encoder geometry calibration')
    if sha256((DATA/'gliders.json').read_bytes()).hexdigest() != data['gliders_sha256']:
        raise ValueError('Encoder geometry calibration uses a different glider catalogue')
    return data


@lru_cache(maxsize=4096)
def _appendant_geometry(symbols, phase, moving_extra_tiles):
    """Width, terminal phase, and source E intercepts of each accepted bit.

    e=15*x+4*t+eta_E(phase). Measured component output offsets are relative
    to the input component core at t=0. No acceptance decision is made here.
    """
    beta = calibration()['components']
    x, packets = 0, []
    for index, symbol in enumerate(symbols):
        if index:
            x += 14*moving_extra_tiles
        p, gap = TABLES['yn'][str(phase)]['0']
        family = 'PC' if index == 0 else 'SC'
        x += 14*gap
        pair = [15*x+b for b in beta[family][str(p)]['offsets']]
        x += len(word(family, p))
        if index == 0:
            p = (p+14) % 30
        phase, gap = TABLES['yn'][str(p)][symbol]
        x += 14*gap
        pair.extend(15*x+b for b in beta['SC'][str(phase)]['offsets'])
        x += len(word('SC', phase))
        packets.append(tuple(pair))
    return x, phase, tuple(packets)


def _program_geometry(appendants, moving_extra_tiles, marker, first_phase,
                      count, *, prepared=False):
    """Measure actual phase-table transitions, retaining empty appendants."""
    x, phase, entries = 0, first_phase, []
    size = len(appendants)
    for index in range(count):
        current = appendants[index % size]
        if index == 0:
            x += len(word('L', 2)) if prepared else len(word('RL', phase))
            phase = 20 if prepared else (phase+22) % 30
        else:
            previous = appendants[(index-1) % size]
            table = (('sl_sl' if not previous else 'sc_sl') if not current else
                     ('sl_rl' if not previous else 'rl'))
            p, gap = TABLES[table][str(phase)]
            x += 14*(gap + (marker if index % size == 0 else 0))
            x += len(word('RL' if current else 'SL', p))
            phase = (p+22) % 30 if current else p
        width, phase, packets = _appendant_geometry(current, phase, moving_extra_tiles)
        entries.append(tuple(tuple(15*x+e for e in packet) for packet in packets))
        x += width + (112 if current else 0)
    return tuple(entries)


@dataclass(frozen=True, slots=True)
class CompactLongGapCertificate:
    appendant_count: int
    cycle_marker_tiles: int
    moving_symbol_extra_tiles: int
    maximum_unproductive_steps: int
    static_pitch_cells: int
    adjacent_c2_clearance_cells: int
    short_source_score: int
    long_source_score: int
    short_phase_witness: tuple
    long_phase_witness: tuple
    minimum_short_gap_tiles: int
    unrounded_gap_tiles: int
    phase_residue_tiles: int
    minimum_gap_tiles: int
    extra_clearance_cells: int

    def as_dict(self):
        result = asdict(self)
        result['short_phase_witness'] = list(self.short_phase_witness)
        result['long_phase_witness'] = list(self.long_phase_witness)
        result.update({
            'certificate_scope': 'exact affine spacing invariant of the intended elementary collision network',
            'productivity_assumption': 'each aligned appendant rotation has a productive step',
            'global_CA_embedding_proved': False,
            'gap_formula': 'C2_gap >= (84*L - delta_e_source + 350 + 310*d)/21',
            'source_score': 'maximum(delta_e_source - 310*d)',
            'phase_enumeration': 'all30 raw phases; actual transitions; all productive endpoint indices',
            'scattering_allowance_status': 'none: cumulative displacements are counted exactly',
            'kappa_range': [-24, 60],
            'packet_boundary_a_offset': 58,
        })
        return result


@lru_cache(maxsize=256)
def compact_long_gap_certificate(initialization=Initialization()):
    """Use exact scattering counts rather than an engineering allowance.

    For consecutive data E's separated by d CTS reads:
      difference in C2 crossing counts = 1-4*d;
      difference in invisible/A4 crossing counts = 2*d.
    Combining e->e-171, c->c+7, a->a-175 and 21*c=2*a+e+kappa:
      21*C2_gap = 84*L-delta_e_source+434+310*d+kappa_old-kappa_new.
    Productive ossification has kappa in {-24,60}. Thus 350 is a rigorous
    lower constant in this particle network. Further crossings of the old C2
    increase its separation from the next deposit. Common histories cancel.
    """
    spacing = GEOMETRY
    cycle_marker_tiles = PROGRAM_CYCLE_MARKER_TILES
    extra_clearance_cells = 0
    appendants = initialization.appendants
    if any(len(a) % 6 for a in appendants):
        raise ValueError('The compact spacing bound requires appendant lengths divisible by six')
    size = len(appendants)
    short_score = long_score = None
    short_witness = long_witness = ()
    for phase in range(30):
        entries = _program_geometry(appendants, spacing.moving_symbol_extra_tiles,
                                    cycle_marker_tiles, phase, 3*size)
        for i in range(size):
            packets = entries[i]
            for k in range(len(packets)-1):
                delta = packets[k+1][0]-packets[k][-1]
                if short_score is None or delta > short_score:
                    short_score, short_witness = delta, (phase, i, k, 0, delta)
            if not packets:
                continue
            for d in range(1, 2*size):
                if not entries[i+d]:
                    continue
                delta = entries[i+d][0][0]-packets[-1][-1]
                score = delta-310*d
                if long_score is None or score > long_score:
                    long_score, long_witness = score, (phase, i, len(packets)-1, d, delta)
    assert short_score is not None and long_score is not None
    if short_score > long_score:
        long_score, long_witness = short_score, short_witness
    pitch = 236+14*spacing.initial_symbol_extra_tiles
    # Normalized C2 spans: N=111 and Y=127 cells.
    clearance = pitch-111+extra_clearance_cells
    short_raw = max(0, _ceil_div(21*clearance+short_score-350, 84))
    nominal_short = 67+spacing.ossifier_group_extra_tiles
    short_gap = _round_up(max(short_raw, nominal_short), nominal_short, 14)
    long_raw = max(0, _ceil_div(21*clearance+long_score-350, 84))
    residue = _base_ossifier_gap(initialization) % 14
    long_gap = _round_up(long_raw, residue, 14)
    return CompactLongGapCertificate(size, cycle_marker_tiles,
        spacing.moving_symbol_extra_tiles, 2*size-2, pitch, clearance,
        short_score, long_score, short_witness, long_witness, short_gap,
        long_raw, residue, long_gap, extra_clearance_cells)


@dataclass(frozen=True, slots=True)
class InitialGapCertificate:
    first_productive_step: int
    initial_symbols: int
    first_source_e_intercept: int
    c2_clearance_cells: int
    minimum_guard_tiles: int
    selected_guard_tiles: int
    ready_guard_tiles: int
    phase_residue_tiles: int
    gap_lower_bound_numerator: int

    def as_dict(self):
        result = asdict(self)
        result.update({
            'gap_lower_bound_denominator': 21,
            'certificate_scope': 'initial affine spacing invariant, conditional on intended collisions',
            'global_CA_embedding_proved': False,
        })
        return result


def compact_initial_gap_certificate(initialization):
    """Locate the first productive read using only the initial word.

    No future CTS trajectory is evaluated. None means no initial productive
    read exists: the tape exhausts without production, so the productive-run
    hypothesis is inapplicable. The guard precedes ready initialization.
    """
    spacing = GEOMETRY
    cycle_marker_tiles = PROGRAM_CYCLE_MARKER_TILES
    tape, appendants = initialization.tape, initialization.appendants
    r = next((i for i, s in enumerate(tape)
              if s == 'Y' and appendants[i % len(appendants)]), None)
    if r is None:
        return None
    n = len(tape)
    phase, shift = (4, 23) if tape[0] == 'N' else (0, 20)
    physical = tape[::-1]
    tape_width = 42 + sum(14+len(word(s, phase)) for s in physical)
    tape_width += sum(14*((6 if s == 'Y' else 7)+spacing.initial_symbol_extra_tiles)
                      for s in physical[:-1])
    packets = _program_geometry(appendants, spacing.moving_symbol_extra_tiles,
                                cycle_marker_tiles, 2, r+1, prepared=True)
    source_e = 15*(tape_width+28) + packets[r][0][0]
    data = calibration()
    c0 = 56 + data['static_cores'][tape[-1]][str(phase)][0]
    a_at_zero_guard = -3*len(word('O', 2)) + 42*shift + data['ossifier_cores']['2'][-1]
    constant = (21*c0-2*a_at_zero_guard-source_e+684*n+310*(r+1)+147-60)
    clearance = 236+14*spacing.initial_symbol_extra_tiles-111
    minimum = max(shift+4, _ceil_div(21*clearance-constant, 84))
    original = n*28 + max(map(len, appendants))*150*r + 139
    minimum = _round_up(minimum, original, 10)
    selected = minimum+spacing.first_ossifier_extra_tiles_per_symbol*n
    return InitialGapCertificate(r, n, source_e, clearance, minimum, selected,
        selected-shift, original % 10, constant+84*selected)
