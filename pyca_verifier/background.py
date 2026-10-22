"""Exact Rule 110 continuation of a finite seed into declared ether exteriors.

The caller declares that the initial word is the entire finite non-background
part of an infinite configuration: everything outside it is periodic ether,
with phases anchored separately at its left and right edges. This declaration
cannot be inferred from matching ether at the edges of an arbitrary cropped
simulation. In particular, never construct this object from a crop whose
discarded cells might contain gliders or other disturbances.

Each step retains every deviation from both appropriate exterior phases. Only
verified ether prefixes and suffixes are removed; additional cells are taken
from the exact evolved periodic backgrounds. Growing padding therefore neither
replays the simulation nor changes the infinite initial configuration. This
provides an infinite *ether* continuation, not infinite program or ossifier
reservoirs. The existing shrinking ``automaton.step`` is left untouched.
"""

from functools import lru_cache

from .automaton import BitRow
from .patterns import ETHER


_PERIOD = len(ETHER)
_PERIOD_MASK = (1 << _PERIOD) - 1
_ETHER_VALUE = int(ETHER[::-1], 2)
_ETHER_ROTATIONS = frozenset(
    ((_ETHER_VALUE >> offset) | (_ETHER_VALUE << (_PERIOD-offset)))
    & _PERIOD_MASK for offset in range(_PERIOD))


def _periodic_step(value):
    """Apply the Rule 110 truth table to a cyclic fourteen-cell word."""
    left = ((value << 1) | (value >> (_PERIOD-1))) & _PERIOD_MASK
    right = (value >> 1) | ((value & 1) << (_PERIOD-1))
    return ((value | right) ^ (left & value & right)) & _PERIOD_MASK


@lru_cache(maxsize=_PERIOD)
def _orbit(value):
    result = [value]
    current = _periodic_step(value)
    while current != value:
        if current in result:
            raise ValueError('The declared boundary does not have a periodic ether orbit')
        result.append(current)
        current = _periodic_step(current)
    return tuple(result)


@lru_cache(maxsize=128)
def _repetition_mask(width):
    """One bit at the start of each fourteen-cell tile, including a short end."""
    tiles = (width + _PERIOD-1) // _PERIOD
    return ((1 << (tiles * _PERIOD)) - 1) // _PERIOD_MASK


def _periodic_value(orbit, anchor, origin, time_offset, width):
    phase = (origin-anchor) % _PERIOD
    period = orbit[time_offset % len(orbit)]
    period = ((period >> phase) | (period << (_PERIOD-phase))) & _PERIOD_MASK
    return (period * _repetition_mask(width)) & ((1 << width)-1)


class EtherBackground:
    """Evolve one declared finite seed without allocating a tick-sized pad.

    ``guard_cells`` is the minimum pure ether margin on each side. Twenty-eight
    cells suffice for the boundary algorithm; a decoder should request more
    than the longest guarded recognition literal (the verifier uses 2048).

    Read ``row`` to obtain the current complete finite observation. ``step()``
    advances exactly once and returns it. ``ensure_padding(n)`` increases its
    margin at its current time, without a Rule 110 step or restarting.

    Left and right ether need separate anchors: encoded gliders can change the
    spatial ether phase across the seed. A fixed seam is always retained, even
    if the entire observed word happens to match one of those phases.
    """

    def __init__(self, seed: BitRow, guard_cells: int = 2048):
        if not isinstance(seed, BitRow):
            raise TypeError('seed must be a BitRow')
        self._validate_guard(guard_cells)
        if seed.width < 2 * _PERIOD:
            raise ValueError('The declared seed needs two ether tiles at each boundary')
        left = seed.value & _PERIOD_MASK
        right = (seed.value >> (seed.width-_PERIOD)) & _PERIOD_MASK
        edge_mask = (1 << (2*_PERIOD)) - 1
        if (left not in _ETHER_ROTATIONS or right not in _ETHER_ROTATIONS
                or seed.value & edge_mask != left | (left << _PERIOD)
                or (seed.value >> (seed.width-2*_PERIOD)) & edge_mask
                != right | (right << _PERIOD)):
            raise ValueError('Both declared seed boundaries must contain two full ether tiles')

        self.row = seed
        self.guard_cells = guard_cells
        self.left_anchor = seed.origin
        self.right_anchor = seed.origin + seed.width-_PERIOD
        self.seam = seed.origin + seed.width//2
        self._seed_time = seed.time
        self._seed_origin = seed.origin
        self._seed_width = seed.width
        self._left_orbit = _orbit(left)
        self._right_orbit = _orbit(right)
        self.native_steps = 0
        self.padding_extensions = 0
        self.padding_cells_added = 0
        self.cropped_ether_cells = 0
        self._until_compaction = 0
        self.ensure_padding(guard_cells)

    @staticmethod
    def _validate_guard(guard_cells):
        if type(guard_cells) is not int:
            raise TypeError('guard_cells must be an integer')
        if guard_cells < 2 * _PERIOD:
            raise ValueError('guard_cells must be at least two ether tiles')

    def _background(self, row, origin, width, side):
        orbit, anchor = ((self._left_orbit, self.left_anchor) if side == 'left'
                         else (self._right_orbit, self.right_anchor))
        return _periodic_value(orbit, anchor, origin,
                               row.time-self._seed_time, width)

    def _support_bounds(self, row):
        """A complete disturbance interval, retaining the phase-change seam."""
        left_delta = row.value ^ self._background(row, row.origin, row.width, 'left')
        right_delta = row.value ^ self._background(row, row.origin, row.width, 'right')
        first = (row.origin + (left_delta & -left_delta).bit_length()-1
                 if left_delta else row.origin+row.width)
        end = row.origin + right_delta.bit_length()
        return min(first, self.seam), max(end, self.seam+1)

    def _resize(self, row, origin, end):
        """Copy known cells; fill only previously declared ether exteriors."""
        old_end = row.origin+row.width
        known_start, known_end = max(origin, row.origin), min(end, old_end)
        known_width = known_end-known_start
        if known_width <= 0:
            raise AssertionError('The retained seam must overlap the known row')
        value = ((row.value >> (known_start-row.origin))
                 & ((1 << known_width)-1)) << (known_start-origin)
        if origin < row.origin:
            value |= self._background(row, origin, row.origin-origin, 'left')
        if end > old_end:
            value |= self._background(row, old_end, end-old_end, 'right') << (old_end-origin)
        return BitRow(value, end-origin, origin, row.time)

    def _record_resize(self, old_row, row):
        added = max(0, old_row.origin-row.origin) + max(
            0, row.origin+row.width-old_row.origin-old_row.width)
        removed = max(0, row.origin-old_row.origin) + max(
            0, old_row.origin+old_row.width-row.origin-row.width)
        if added:
            self.padding_extensions += 1
            self.padding_cells_added += added
        self.cropped_ether_cells += removed

    def ensure_padding(self, guard_cells: int):
        """Increase pure ether margins at the current tick, preserving all cells."""
        self._validate_guard(guard_cells)
        self.guard_cells = max(self.guard_cells, guard_cells)
        # A disturbance can travel at most one cell per tick. Keeping this
        # additional buffer permits exact fixed-width evolution between
        # compactions without ever reducing the requested minimum margin.
        self._compaction_interval = min(128, max(1, self.guard_cells//2))
        margin = self.guard_cells+self._compaction_interval
        start, end = self._support_bounds(self.row)
        origin = min(self.row.origin, start-margin)
        end = max(self.row.origin+self.row.width, end+margin)
        old_row = self.row
        self.row = self._resize(old_row, origin, end)
        self._record_resize(old_row, self.row)
        self._until_compaction = 0
        return self.row

    def step(self):
        """Advance the declared infinite configuration by one native CA tick."""
        old_row = self.row
        # The verified ether margins protect this fixed extent between
        # compactions. Only the single missing neighbor on each side is needed.
        left = self._background(old_row, old_row.origin-1, 1, 'left')
        right = self._background(old_row, old_row.origin+old_row.width, 1, 'right')
        value, width = old_row.value, old_row.width
        left_cells = (value << 1) | left
        right_cells = (value >> 1) | (right << (width-1))
        # Apply Rule 110 to every retained cell using the two declared exterior
        # neighbors. Both centered and right arrays fit within width bits;
        # their union and the final XOR therefore need no additional mask.
        evolved = BitRow((value | right_cells) ^ (left_cells & value & right_cells),
                         width, old_row.origin, old_row.time+1)
        if self._until_compaction <= 0:
            start, end = self._support_bounds(evolved)
            margin = self.guard_cells+self._compaction_interval
            self.row = self._resize(evolved, start-margin, end+margin)
            self._until_compaction = self._compaction_interval-1
        else:
            self.row = evolved
            self._until_compaction -= 1
        self._record_resize(old_row, self.row)
        self.native_steps += 1
        return self.row

    def as_dict(self):
        """Describe the boundary declaration and accumulated evolution work."""
        return {
            'boundary': 'exact separately anchored periodic ether exteriors',
            'spatial_period': _PERIOD,
            'temporal_period': len(self._left_orbit),
            'seed_time': self._seed_time,
            'seed_origin': self._seed_origin,
            'seed_width': self._seed_width,
            'left_anchor': self.left_anchor,
            'right_anchor': self.right_anchor,
            'left_period_word': format(self._left_orbit[0], f'0{_PERIOD}b')[::-1],
            'right_period_word': format(self._right_orbit[0], f'0{_PERIOD}b')[::-1],
            'retained_seam': self.seam,
            'guard_cells': self.guard_cells,
            'compaction_interval': self._compaction_interval,
            'native_steps': self.native_steps,
            'padding_extensions': self.padding_extensions,
            'padding_cells_added': self.padding_cells_added,
            'cropped_ether_cells': self.cropped_ether_cells,
            'reservoir_replenishment': False,
        }
