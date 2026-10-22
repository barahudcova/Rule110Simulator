"""Exact Rule 110 evolution inside the known light cone of a finite row.

No boundary values are invented: each step discards one cell at either end.
The least significant bit is the leftmost cell, at coordinate ``origin``.
"""

from dataclasses import dataclass
from collections.abc import Iterator


@dataclass(frozen=True, slots=True)
class BitRow:
    value: int
    width: int
    origin: int = 0
    time: int = 0

    def __post_init__(self) -> None:
        for name in ("value", "width", "origin", "time"):
            if type(getattr(self, name)) is not int:
                raise TypeError(f"{name} must be an integer")
        if self.width < 1:
            raise ValueError("width must be positive")
        if self.value < 0 or self.value.bit_length() > self.width:
            raise ValueError("value must fit within width bits")
        if self.time < 0:
            raise ValueError("time must be nonnegative")

    @classmethod
    def from_word(cls, word: str, origin: int = 0) -> "BitRow":
        """Read a nonempty binary word from left to right."""
        if not isinstance(word, str):
            raise TypeError("word must be a string")
        if not word or any(cell not in "01" for cell in word):
            raise ValueError("word must contain one or more binary digits")
        return cls(int(word[::-1], 2), len(word), origin)

    def word(self) -> str:
        """Return cells in increasing spatial coordinate order."""
        return format(self.value, f"0{self.width}b")[::-1]


def step(row: BitRow) -> BitRow:
    """Advance Rule 110 once, preserving only cells with known neighbors."""
    if not isinstance(row, BitRow):
        raise TypeError("row must be a BitRow")
    if row.width < 3:
        raise ValueError("a Rule 110 step needs at least three known cells")
    left, center, right = row.value << 1, row.value, row.value >> 1
    next_value = (center | right) ^ (left & center & right)
    width = row.width - 2
    value = (next_value >> 1) & ((1 << width) - 1)
    return BitRow(value, width, row.origin + 1, row.time + 1)


def simulate(row: BitRow, steps: int) -> Iterator[BitRow]:
    """Yield the initial row and ``steps`` exact successive rows."""
    if not isinstance(row, BitRow):
        raise TypeError("row must be a BitRow")
    if type(steps) is not int:
        raise TypeError("steps must be an integer")
    if steps < 0:
        raise ValueError("steps must be nonnegative")
    if row.width < 2 * steps + 1:
        raise ValueError("initial row is too narrow for the requested light cone")
    yield row
    for _ in range(steps):
        row = step(row)
        yield row
