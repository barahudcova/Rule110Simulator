"""The intact ossifier words delimiting the left side of decoded content."""
from dataclasses import dataclass
from functools import lru_cache
from .patterns import ETHER, GLIDERS, word


@dataclass(frozen=True, slots=True)
class AuxiliaryPattern:
    kind: str
    variant: str
    phase: int
    bits: str


@lru_cache(maxsize=1)
def auxiliary_patterns():
    return tuple(AuxiliaryPattern('ossifier','O',phase,ETHER+word('O',phase)+ETHER)
                 for phase in range(len(GLIDERS['O'])))
