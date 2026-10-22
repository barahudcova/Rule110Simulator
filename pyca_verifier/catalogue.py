"""Integrity checks and ether geometry for the fixed runtime catalogues."""
from functools import lru_cache
from hashlib import sha256
import json
import re

from .patterns import DATA, ETHER

ROTATIONS = frozenset(ETHER[i:]+ETHER[:i] for i in range(len(ETHER)))


@lru_cache(maxsize=None)
def load_catalogue(name):
    """Read a required finite table, checking the released bytes first."""
    manifest = json.loads((DATA/'catalogue_manifest.json').read_text())
    expected = manifest['sha256'][name]
    raw = (DATA/name).read_bytes()
    if sha256(raw).hexdigest() != expected:
        raise ValueError(f'Runtime catalogue changed: {name}')
    return json.loads(raw)


@lru_cache(maxsize=28)
def _periodic_prefix(pattern):
    return re.compile('(?:'+re.escape(pattern)+')+')


def _prefix_length(text):
    if len(text) < 14 or text[:14] not in ROTATIONS:
        return 0
    initial = text[:14]
    matched = _periodic_prefix(initial).match(text).end()
    while matched < len(text) and text[matched] == initial[matched % 14]:
        matched += 1
    return matched


def defect_span(text):
    """First/last non-ether fourteen-cell windows in a bounded literal."""
    if len(text) < 14:
        return None
    prefix = _prefix_length(text)
    if prefix == len(text):
        return None
    first = max(0, prefix-13)
    while first+14 <= len(text) and text[first:first+14] in ROTATIONS:
        first += 1
    reverse = text[::-1]
    first_block = reverse[:14]
    reverse_rotations = {r[::-1] for r in ROTATIONS}
    if first_block in reverse_rotations:
        suffix = _periodic_prefix(first_block).match(reverse).end()
        while suffix < len(reverse) and reverse[suffix] == first_block[suffix % 14]:
            suffix += 1
    else:
        suffix = 0
    last = min(len(text)-14, len(text)-suffix)
    while last >= 0 and text[last:last+14] in ROTATIONS:
        last -= 1
    return (first, last+14) if first <= last else None
