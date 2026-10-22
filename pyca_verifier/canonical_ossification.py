"""Canonical identity for a symbol currently undergoing ossification.

The finite frontier vocabulary retains the nearest unused A4 as well as the
incoming/deposited data. That context is necessary: the two-C2/two-E data
fragment alone can be identical for Y and N. Each vocabulary word designates
the right endpoint of its nonether core as the conversion's unique anchor.

These helpers compare bounded relative positions supplied by the content
transducer. They do not evolve Rule 110, use an expected tape, or construct
unbounded overlap components. Recognition of a frontier assigns its single
logical symbol to the static sweep. Static/moving descriptions with anchors
inside that same conversion are consequently suppressed on both sweeps.

The frozen native parents test this rule in every catalogued temporal phase.
Completeness on arbitrary reachable contexts additionally requires that the
spacing invariant prevents an unrelated symbol's anchor from entering a
frontier's core; enumerating isolated parent words does not prove that fact.
"""
from .canonical_content_patterns import CanonicalHit


def canonicalize_frontiers(hits):
    """Merge frontier descriptions precisely when their designated cells agree.

    An anchor is the core's right endpoint, so matching longer ether guards
    cannot change the identity. Different anchors remain distinct; there is
    no transitive merging based on intersecting recognition windows.
    """
    by_anchor = {}
    conflicts = []
    for hit in hits:
        if hit.kind != 'frontier':
            continue
        if hit.hi != hit.anchor:
            raise ValueError('A conversion anchor must end its nonether core')
        old = by_anchor.get(hit.anchor)
        if old is None:
            by_anchor[hit.anchor] = hit
        elif old.symbol != hit.symbol:
            conflicts.append('Conversion descriptions at one anchor disagree')
        else:
            by_anchor[hit.anchor] = CanonicalHit('frontier', hit.symbol,
                min(old.left, hit.left), max(old.right, hit.right),
                min(old.lo, hit.lo), hit.anchor, hit.anchor)
    return tuple(by_anchor[a] for a in sorted(by_anchor)), tuple(conflicts)


def frontier_claims(frontier, symbol):
    """Test a designated position, rather than containment of a whole word.

    ``hi`` is included intentionally. In some moving phases the last literal
    cell, which is the moving anchor, is exactly the endpoint of the nonether
    core. No exterior-guard-dependent expansion or adjustable margin is used.
    """
    return (symbol.kind in ('static', 'moving')
            and frontier.lo <= symbol.anchor <= frontier.anchor)


def suppress_converting_symbols(frontiers, symbols):
    """Return independent symbol hits and disagreements about conversion.

    The caller emits the canonical frontiers once in its static sweep, plus
    the retained ordinary hits in their respective sweeps. A claimed child
    must agree on the value; conflicting evidence is never resolved by a
    preferred pattern. If distinct conversions claim the same anchor, the
    finite geometry is ambiguous and is reported explicitly.
    """
    retained = []
    conflicts = []
    for symbol in symbols:
        owners = tuple(frontier for frontier in frontiers
                       if frontier_claims(frontier, symbol))
        if not owners:
            retained.append(symbol)
        elif any(owner.symbol != symbol.symbol for owner in owners):
            conflicts.append('A conversion and its symbol description disagree')
        if len({owner.anchor for owner in owners}) > 1:
            conflicts.append('Distinct conversion anchors claim one symbol')
    return tuple(retained), tuple(conflicts)
