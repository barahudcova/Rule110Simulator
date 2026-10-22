"""Bounded exact recognition of compiler-provided binary words."""

class LiteralMatcher:
    """Fixed-width shift-register recognizer, without a huge trie.

    Buckets are compiler constants. The register has a fixed bit width, and
    every tested suffix length is a compiler constant. A prefix lookup keeps
    ordinary ether from triggering thousands of large-integer comparisons.
    """
    def __init__(self, literals, *, reverse=False):
        self.literals = tuple(literals)
        self.width = max(map(lambda p: len(p.bits), literals))
        self.mask = (1 << self.width)-1
        self.tables = {}
        self.prefixes = {}
        for i, p in enumerate(literals):
            oriented = p.bits if reverse else p.bits[::-1]
            width = len(oriented)
            value = int(oriented, 2)
            k = min(64, width)
            prefix = value & ((1 << k)-1)
            self.prefixes.setdefault(k, {}).setdefault(prefix, set()).add(width)
            self.tables.setdefault(width, {}).setdefault(value, []).append(i)
        self.prefixes = {k: {prefix: tuple(sorted(widths)) for prefix, widths in bucket.items()}
                         for k, bucket in self.prefixes.items()}
        self.masks = {width: (1 << width)-1 for width in self.tables}

    def advance(self, tail, warm, digit):
        tail = ((tail << 1) | digit) & self.mask
        warm = min(self.width, warm+1)
        hits = []
        for k, bucket in self.prefixes.items():
            if warm < k:
                continue
            for width in bucket.get(tail & ((1 << k)-1), ()):
                if warm >= width:
                    hits.extend(self.tables[width].get(tail & self.masks[width], ()))
        return tail, warm, tuple(hits)


