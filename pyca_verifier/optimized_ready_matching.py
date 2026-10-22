"""Exact packed-byte candidate filtering for the prepared-leader ready words.

For every bit alignment, choose an interior byte of the complete common suffix
that never occurs in periodic ether. One byte-table pass finds all possible
candidate locations. Verify the whole interior word, both partial-byte edges,
and the complete distinguishing prefix at every candidate. Dense arbitrary
inputs use the generic exact matcher. No crop, clock condition, debounce, or
omitted native tick changes the recognized language.
"""
from .matching import ReadyMatcher
from .patterns import ETHER


_ETHER_BYTES = frozenset(int((ETHER*2)[phase:phase+8][::-1], 2)
                         for phase in range(len(ETHER)))


class PreparedHeadMatcher:
    """Same exact occurrence interface as ReadyMatcher, with a sparse gate."""

    candidate_limit = 1024

    def __init__(self, signatures):
        self.fallback = ReadyMatcher(signatures)
        self.patterns = self.fallback.patterns
        self.groups = self.fallback.groups
        self.gates = None
        if len(self.groups) != 1:
            return
        suffix, prefixes = self.groups[0]
        if suffix.size < 96:
            return
        # Ether absence selects a rare byte; correctness never assumes the
        # observed row is ether. Every complete suffix necessarily contains
        # its selected byte at the compiled alignment, in any binary row.
        gates = {}
        for alignment in suffix.compiled:
            _, piece, first, *_ = alignment
            options = [(index, byte) for index, byte in enumerate(piece)
                       if byte not in _ETHER_BYTES]
            if not options:
                return
            index, byte = min(options, key=lambda item:(item[1].bit_count(),item[1]))
            gates.setdefault(byte, []).append((first+index, alignment))
        self.gates = gates
        self.table = bytes(int(byte in gates) for byte in range(256))
        self.suffix_size = suffix.size
        self.prefixes = prefixes

    def find(self, value, width):
        if type(value) is not int or type(width) is not int:
            raise TypeError('value and width must be integers')
        if width < 0 or value < 0 or value.bit_length() > width:
            raise ValueError('value must fit within a nonnegative width')
        if self.gates is None or width < self.suffix_size:
            return self.fallback.find(value, width)
        data = value.to_bytes((width+7)//8, 'little')
        marked = data.translate(self.table)
        if marked.count(b'\1') > self.candidate_limit:
            return self.fallback.find(value, width)
        result = []
        found = marked.find(b'\1')
        while found >= 0:
            for position, alignment in self.gates[data[found]]:
                offset, piece, first, end, leading_mask, leading, trailing_mask, trailing = alignment
                base = found-position
                head = base*8+offset
                if not (0 <= head and head+self.suffix_size <= width
                        and data.startswith(piece, base+first)
                        and (not leading_mask or data[base] & leading_mask == leading)
                        and (not trailing_mask or data[base+end] & trailing_mask == trailing)):
                    continue
                for index, size, wanted, mask in self.prefixes:
                    start = head-size
                    if start < 0:
                        continue
                    if size:
                        byte, shift = divmod(start, 8)
                        actual = int.from_bytes(data[byte:byte+(shift+size+7)//8], 'little') >> shift
                        if actual & mask != wanted:
                            continue
                    result.append((index, start))
            found = marked.find(b'\1', found+1)
        return tuple(sorted(result))
