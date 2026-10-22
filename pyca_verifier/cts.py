"""Independent cyclic-tag reference, used only after decoding for comparison."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CTSState:
    tape: str
    appendant_index: int = 0

    def advance(self, appendants):
        if not self.tape:
            return self
        index = self.appendant_index
        return CTSState(self.tape[1:]+(appendants[index] if self.tape[0] == 'Y' else ''),
                        (index+1) % len(appendants))

    def as_dict(self):
        return {'tape': self.tape, 'appendant_index': self.appendant_index}
