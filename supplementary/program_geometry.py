"""Independently evolved free-packet geometry for the program audit.

All binary words and lookup tables come from this release's runtime. Canonical
cuts are located in exact isolated Rule 110 orbits; no drawing or external
catalogue is used. A join is checked cell for cell against independent CA
updates, including both phase-aware canonical cuts and intervening ether.

These helpers verify free initial joins only. The reaction and finite-grammar
checks are in program_joins.py. All imports use the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import json
import sys

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from pyca_verifier.automaton import BitRow, step
from pyca_verifier.patterns import ETHER, TABLES, word


@dataclass(frozen=True, slots=True)
class CellRow:
    """One horizontal row; coordinates increase from left to right."""

    left: int
    bits: str

    @property
    def right(self) -> int:
        return self.left + len(self.bits)


PROGRAM_FAMILIES = ("PC", "SC", "RL", "SL", "L")


def _height(height):
    if type(height) is not int or height < 1:
        raise ValueError("height must be a positive integer")


@lru_cache(maxsize=None)
def _cycle_offsets(family):
    """Locate every canonical phase in a fully known isolated CA orbit."""
    if family not in PROGRAM_FAMILIES:
        raise ValueError(f"unknown program family: {family}")
    padding = len(ETHER) * 8
    state = BitRow.from_word(ETHER * 8 + word(family, 0) + ETHER * 8,
                             origin=-padding)
    offsets = []
    for time in range(31):
        literal = word(family, time % 30)
        cells = state.word()
        index = cells.find(literal)
        if index < 0 or cells.find(literal, index + 1) >= 0:
            raise AssertionError(("canonical word is absent or ambiguous",
                                  family, time))
        # Both exterior tiles are actual, fully known ether, not invented
        # boundary values or a replacement for cropped particle pixels.
        if cells[index-14:index] != ETHER:
            raise AssertionError(("left ether guard changed", family, time))
        end = index + len(literal)
        if cells[end:end+14] != ETHER:
            raise AssertionError(("right ether guard changed", family, time))
        offsets.append(state.origin + index)
        if time < 30:
            state = step(state)
    if offsets[0] != 0 or offsets[30] != -8:
        raise AssertionError(("expected thirty-tick displacement", family,
                              offsets[0], offsets[30]))
    return tuple(offsets[:30])


@lru_cache(maxsize=None)
def program_rows(family, phase, height=100):
    """Return exact canonical cuts, with the literal JSON word at row zero.

    A packet advances by -8 cells every thirty ticks.  The phase's cut offset
    is measured from an actual Rule 110 orbit in :func:`_cycle_offsets`.
    """
    _height(height)
    if type(phase) is not int or not 0 <= phase < 30:
        raise ValueError("program phase must be an integer from 0 through 29")
    offsets = _cycle_offsets(family)
    result = []
    for time in range(height):
        cycles, current = divmod(phase + time, 30)
        left = offsets[current] - offsets[phase] - 8 * cycles
        result.append(CellRow(left, word(family, current)))
    if result[0] != CellRow(0, word(family, phase)):
        raise AssertionError("literal top cut changed")
    return tuple(result)


def padding_rows(left_piece, right_piece, top_gap_tiles):
    """The exact ether gap between two phase-specific canonical pieces.

    Both input pieces have their own top origin zero.  The right piece is
    translated by ``len(left_top) + 14*top_gap_tiles``.  The result uses the
    left piece's coordinates; row widths can be zero or change by fourteen.
    A negative width means these two cuts cannot be joined in that spacing.
    """
    if not left_piece or len(left_piece) != len(right_piece):
        raise ValueError("pieces must have the same positive height")
    if type(top_gap_tiles) is not int or top_gap_tiles < 0:
        raise ValueError("top_gap_tiles must be a nonnegative integer")
    if left_piece[0].left != 0 or right_piece[0].left != 0:
        raise ValueError("input top origins must be zero")
    origin = left_piece[0].right
    translation = origin + 14*top_gap_tiles
    result = []
    for time, (left, right) in enumerate(zip(left_piece, right_piece)):
        start, end = left.right, translation + right.left
        if end < start:
            raise ValueError(f"canonical cuts overlap at tick {time}")
        bits = "".join(ETHER[(x-origin+4*time) % 14]
                       for x in range(start, end))
        if len(bits) % 14 or bits != ETHER * (len(bits)//14):
            raise AssertionError("join cuts do not align to ether tile phases")
        result.append(CellRow(start, bits))
    return tuple(result)


def joined_program_rows(left_family, left_phase, right_family, right_phase,
                        top_gap_tiles, height=100):
    """Compose exact bits for two word pieces and their actual ether gap."""
    left = program_rows(left_family, left_phase, height)
    right = program_rows(right_family, right_phase, height)
    gap = padding_rows(left, right, top_gap_tiles)
    return tuple(CellRow(a.left, a.bits + g.bits + b.bits)
                 for a, g, b in zip(left, gap, right))


def encoder_program_joins(include_markers=True):
    """All finite phase-table join types actually used by Encoder.program."""
    cases = []
    for phase in range(30):
        for key, left, right, extra in (
                ("sl_sl", "SL", "SL", 0),
                ("sl_rl", "SL", "RL", 0),
                ("rl", "SC", "RL", 8),
                ("sc_sl", "SC", "SL", 8)):
            target, tiles = TABLES[key][str(phase)]
            cases.append((key, left, phase, right, target, tiles+extra))
            if include_markers and key in ("rl", "sl_rl"):
                cases.append((key+"_marker4", left, phase, right,
                              target, tiles+extra+4))
        for symbol in ("0", "Y", "N"):
            target, tiles = TABLES["yn"][str(phase)][symbol]
            cases.append(("SC_"+symbol, "SC", phase, "SC", target, tiles))
        for symbol in ("Y", "N"):
            target, tiles = TABLES["yn"][str((phase+14) % 30)][symbol]
            cases.append(("PC_"+symbol, "PC", phase, "SC", target, tiles))
        target, tiles = TABLES["yn"][str((phase+22) % 30)]["0"]
        cases.append(("RL_PC", "RL", phase, "PC", target, tiles))
    target, tiles = TABLES["yn"]["20"]["0"]
    cases.append(("L2_PC", "L", 2, "PC", target, tiles))
    return tuple(cases)


def validate_program_joins(height=100, include_markers=True):
    """Check assembled puzzle rows against direct CA evolution of each join.

    This covers all 300 phase-table joins, their sixty four-tile-marker
    variants, and the initial L[2] to first principal-component join.
    """
    _height(height)
    padding_tiles = (height+13)//14 + 8
    padding = padding_tiles*14
    failures = []
    cells_checked = 0
    variable_gaps = 0
    zero_gap_cases = 0
    cases = encoder_program_joins(include_markers)
    for name, left, phase, right, target, tiles in cases:
        rows = joined_program_rows(left, phase, right, target, tiles, height)
        top = word(left, phase) + ETHER*tiles + word(right, target)
        state = BitRow.from_word(ETHER*padding_tiles+top+ETHER*padding_tiles,
                                 origin=-padding)
        gaps = padding_rows(program_rows(left, phase, height),
                            program_rows(right, target, height), tiles)
        variable_gaps += len({len(g.bits) for g in gaps}) > 1
        zero_gap_cases += tiles == 0
        for time, row in enumerate(rows):
            start = row.left-state.origin
            actual = state.word()[start:start+len(row.bits)]
            cells_checked += len(row.bits)
            if actual != row.bits:
                failures.append({"join": name, "left": [left, phase],
                                 "right": [right, target], "tiles": tiles,
                                 "tick": time})
                break
            if time+1 < height:
                state = step(state)
    return {"height": height, "join_cases": len(cases),
            "top_zero_gap_cases": zero_gap_cases,
            "cases_with_variable_padding_width": variable_gaps,
            "compared_cells": cells_checked, "failures": failures}

