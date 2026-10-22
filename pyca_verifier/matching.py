"""Exact bounded-word searches in packed binary rows, using only stdlib.

Search the shared suffix once in each of the eight byte alignments, verify
partial-byte boundaries, and check the short distinguishing prefixes locally.
The packed representation changes neither the words nor their occurrences.
All positions and duplicate signature entries are retained without debounce.
"""
import re


_NONZERO_BYTES = re.compile(rb'[^\x00]')
_BYTE_POSITIONS = tuple(tuple(i for i in range(8) if value & (1 << i))
                        for value in range(256))


class _PackedWord:
    """Compile all byte alignments of a left-to-right binary word."""

    def __init__(self, bits):
        self.bits = bits
        self.size = len(bits)
        value = int(bits[::-1], 2)
        compiled = []
        for offset in range(8):
            length = offset + self.size
            data = (value << offset).to_bytes((length+7)//8, "little")
            first = int(offset != 0)
            end = length//8
            leading_mask = (255 ^ ((1 << offset)-1)) if offset else 0
            trailing_mask = (1 << (length % 8))-1
            compiled.append((offset, data[first:end], first, end,
                             leading_mask, data[0] & leading_mask,
                             trailing_mask, data[-1] & trailing_mask))
        self.compiled = tuple(compiled)

    def starts(self, data, width):
        if width < self.size:
            return
        if self.size < 16:
            # Very short generic patterns can lack an interior full byte in
            # some alignments. Ready signatures are longer than this cutoff.
            text = format(int.from_bytes(data, "little"),
                          f"0{len(data)*8}b")[::-1][:width]
            start = text.find(self.bits)
            while start >= 0:
                yield start
                start = text.find(self.bits, start+1)
            return

        for (offset, piece, first, end, leading_mask, leading,
             trailing_mask, trailing) in self.compiled:
            found = data.find(piece)
            while found >= 0:
                base = found-first
                start = base*8+offset
                if (0 <= start and start+self.size <= width
                        and (not leading_mask
                             or data[base] & leading_mask == leading)
                        and (not trailing_mask
                             or data[base+end] & trailing_mask == trailing)):
                    yield start
                # Byte matches can overlap. Different bit alignments cover
                # each bit start once, including starts inside the last byte.
                found = data.find(piece, found+1)


class ReadyMatcher:
    """Return exact ``(signature_index, start_bit)`` occurrences.

    ``signatures`` may contain binary strings or objects with a ``bits``
    property. No import of the ready detector is required. Starts are relative
    to bit zero of ``value``, whose least significant bit is its leftmost cell.
    """

    def __init__(self, signatures):
        if isinstance(signatures, str):
            raise TypeError("signatures must be an iterable of signatures")
        self.patterns = tuple(getattr(signature, "bits", signature)
                              for signature in signatures)
        if not self.patterns:
            raise ValueError("At least one signature is required")
        for bits in self.patterns:
            if not isinstance(bits, str):
                raise TypeError("Each signature must be a binary string")
            if not bits or any(bit not in "01" for bit in bits):
                raise ValueError("Each signature must contain binary digits")

        common = self.patterns[0]
        for bits in self.patterns[1:]:
            limit = min(len(common), len(bits))
            count = 0
            while count < limit and common[-count-1] == bits[-count-1]:
                count += 1
            common = common[-count:] if count else ""
        if len(common) >= 16:
            prefixes = []
            for index, bits in enumerate(self.patterns):
                prefix = bits[:-len(common)]
                size = len(prefix)
                prefixes.append((index, size,
                                 int(prefix[::-1], 2) if prefix else 0,
                                 (1 << size)-1))
            self.groups = ((_PackedWord(common), tuple(prefixes)),)
        else:
            # Custom signature families need not share a useful suffix.
            self.groups = tuple((_PackedWord(bits), ((index, 0, 0, 0),))
                                for index, bits in enumerate(self.patterns))

    def find(self, value, width):
        """Find all occurrences, retaining overlapping and duplicate entries."""
        if type(value) is not int or type(width) is not int:
            raise TypeError("value and width must be integers")
        if width < 0 or value < 0 or value.bit_length() > width:
            raise ValueError("value must fit within a nonnegative width")
        data = value.to_bytes((width+7)//8, "little")
        result = []
        for suffix, prefixes in self.groups:
            for head in suffix.starts(data, width):
                for index, size, wanted, mask in prefixes:
                    start = head-size
                    if start < 0:
                        continue
                    if size:
                        base, offset = divmod(start, 8)
                        actual = int.from_bytes(
                            data[base:base+(offset+size+7)//8], "little") >> offset
                        if actual & mask != wanted:
                            continue
                    result.append((index, start))
        return tuple(sorted(result))


def match_starts(value, width, bits):
    """Return all exact literal starts as a bitset, retaining overlaps."""
    count = width - len(bits) + 1
    if count <= 0:
        return 0
    matches = (1 << count) - 1
    for offset, symbol in enumerate(bits):
        matches &= (value >> offset) if symbol == '1' else ~(value >> offset)
        if not matches:
            break
    return matches


def positions(bits):
    """Yield the indices of set bits in increasing spatial order."""
    if bits.bit_length() >= 65536 and bits.bit_count() >= 16:
        # Repeated extraction of a low bit copies a large integer for every
        # occurrence. Scan its packed nonzero bytes once when there are enough
        # occurrences to amortize that scan. Small and very sparse masks keep
        # the inexpensive integer path below.
        data = bits.to_bytes((bits.bit_length()+7)//8, 'little')
        for match in _NONZERO_BYTES.finditer(data):
            base = match.start()
            for offset in _BYTE_POSITIONS[data[base]]:
                yield base*8 + offset
        return
    while bits:
        first = bits & -bits
        yield first.bit_length() - 1
        bits ^= first
