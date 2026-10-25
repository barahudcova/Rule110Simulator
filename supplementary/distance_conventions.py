"""Measure Cook's ether references on this release's native particle orbits.

No component joins, expected computation, ready words, or decoder are used.
Run with Python 3.10+; only the standard library and this release are used.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT))
from pyca_verifier.automaton import BitRow, step
from pyca_verifier.patterns import ETHER, word

PERIOD = {'C2': 7, 'A4': 3, 'E': 30}
SLOPE = {'C2': (1, 0), 'A4': (3, -2), 'E': (15, 4)}


def enabled_checks():
    if not __debug__:
        raise RuntimeError('CHECKS_DISABLED: run without python -O; assertions are verification checks')


def checked(code, procedure, *args):
    """Keep the failing stage in the exception even for bare inner asserts."""
    try:
        return procedure(*args)
    except AssertionError as error:
        raise AssertionError(f'{code}: a required native identity failed; {error}') from error


def native_rows(family, phase, ticks, padding=40):
    row = BitRow.from_word(ETHER * padding + word(family, phase) + ETHER * padding)
    rows = []
    for _ in range(ticks):
        rows.append((row.origin, row.word()))
        row = step(row)
    return rows


def derive_normalizations(*, include_controls=False):
    """Follow each free particle from phase zero; no calibration eta is used.

    The control particles are needed only by the companion conversion audit.
    Coordinates have scale/time coefficient (1,0) for C2, (3,-2) for A4
    and both controls, and (15,4) for E-bar.
    """
    enabled_checks()
    result = {}
    periods = dict(PERIOD)
    slopes = dict(SLOPE)
    if include_controls:
        periods.update(acceptor=3, rejector=3)
        slopes.update(acceptor=(3, -2), rejector=(3, -2))
    for family, period in periods.items():
        corrections = {}
        for tick, (origin, bits) in enumerate(native_rows(family, 0, period)):
            hits = []
            for phase in range(period):
                pattern = ETHER + word(family, phase) + ETHER
                at = bits.find(pattern)
                while at >= 0:
                    hits.append((origin + at + 14, phase))
                    at = bits.find(pattern, at + 1)
            assert len(hits) == 1, (family, tick, hits)
            x, phase = hits[0]
            assert phase == tick
            scale, time_coefficient = slopes[family]
            corrections[str(phase)] = scale * (560 - x) - time_coefficient * tick
        result[family] = corrections
    return result


def triangles(rows, times, xs):
    """Full size-three ether triangles, not suffixes of larger white holes."""
    def bit(t, x):
        origin, bits = rows[t]
        assert 0 <= x - origin < len(bits)
        return bits[x - origin]

    return {(t, x) for t in times for x in xs
            if bit(t - 1, x) == '1' and bit(t, x - 1) == '1'
            and all(bit(t + j, x + k) == ('0' if k < 3 - j else '1')
                    for j in range(3) for k in range(4 - j))}


def static_and_rightmoving_refs(norm):
    results = []
    for family in ('C2', 'A4'):
        for phase in range(PERIOD[family]):
            rows = native_rows(family, phase, 20, padding=20)
            points = triangles(rows, range(1, 16), range(250, 330))
            scale, tc = SLOPE[family]
            anchor = scale * 280 + norm[family][str(phase)]
            offsets = sorted({scale * x + tc * t - anchor for t, x in points})
            if family == 'C2':
                left = max(v for v in offsets if v < 0)
                right = min(v for v in offsets if v > 0)
                assert (left, right) == (-2, 7)
                assert all(v % 2 == 0 for v in offsets if v < 0)
                assert all(v % 2 == 1 for v in offsets if v > 0)
                pitch = 2
            else:
                left = max(v for v in offsets if v <= 0)
                right = min(v for v in offsets if v > 0)
                assert (left, right) == (0, 30)
                assert all(v % 14 == 0 for v in offsets if v <= 0)
                assert all((v - 30) % 14 == 0 for v in offsets if v > 0)
                pitch = 14
            results.append(dict(family=family, phase=phase, anchor=anchor,
                                left_reference_offset=left, right_reference_offset=right,
                                reference_pitch=pitch, observed_offsets=offsets))
    return results


def leftmoving_refs(norm):
    results = []
    for phase in range(30):
        numerator = norm['E'][str(phase)] + 4 * phase
        assert numerator % 15 == 0
        offset = -numerator // 15
        rows = native_rows('E', phase, 218)
        actual = triangles(rows, range(1, 214), range(440, 610))
        # Coordinates relative to the free phase-zero orbit of this particle.
        points = {(t + phase, x - 560 + offset) for t, x in actual}

        def q(vertex):
            t, x = vertex
            return 15 * x + 4 * t

        def flood(seeds, shift):
            found = set(seeds)
            todo = list(found)
            while todo:
                t, x = todo.pop()
                target = (t + shift[0], x + shift[1])
                if target in points and target not in found:
                    found.add(target)
                    todo.append(target)
            return found

        # Follow adjacent triangles inward from unquestionably exterior ether.
        # No predicted near-particle reference offsets enter these searches.
        left = flood((p for p in points if q(p) < -500), (3, 2))
        right = flood((p for p in points if q(p) > 500), (-3, -2))
        assert not left.intersection(right)
        left_up = max(map(q, left))
        right_up = min(map(q, right))
        left_columns = {p for p in left if (p[0] - 7, p[1]) in left}
        right_columns = {p for p in right if (p[0] + 7, p[1]) in right}
        left_over = max(map(q, left_columns))
        right_over = min(map(q, right_columns))
        witnesses = {
            'left_up': sorted(p for p in left if q(p) == left_up),
            'right_up': sorted(p for p in right if q(p) == right_up),
            'left_over': sorted(p for p in left_columns if q(p) == left_over),
            'right_over': sorted(p for p in right_columns if q(p) == right_over),
        }
        residues = {
            key: sorted({(3 * x - 2 * t) % 84 if key.endswith('up') else x % 8
                         for t, x in vertices})
            for key, vertices in witnesses.items()
        }
        assert residues == {'left_up': [70], 'right_up': [49],
                            'left_over': [2], 'right_over': [3]}, (phase, residues)
        results.append(dict(phase=phase, phase_zero_offset=offset,
                            exterior_connected_triangle_counts=[len(left), len(right)],
                            extremes_in_Q=[left_up, right_up, left_over, right_over],
                            reference_residues=residues, reference_vertices=witnesses))
    return results


def run(output_dir=None):
    enabled_checks()
    norm = checked('NATIVE_NORMALIZATION', derive_normalizations)
    sources = [Path(__file__).resolve(),
               PROJECT / 'pyca_verifier/patterns.py',
               PROJECT / 'pyca_verifier/automaton.py',
               PROJECT / 'pyca_verifier/data/gliders.json',
               PROJECT / 'pyca_verifier/data/encoder_geometry.json']
    result = dict(
        passed=True,
        scope='Geometric units and side references of isolated native particles; no encoder, ready, or decoder correctness claim',
        sources={str(p.relative_to(PROJECT)): sha256(p.read_bytes()).hexdigest()
                 for p in sources},
        primary_references=['Cook 2004 pp15-17, Figs7-8', 'Cook 2009 pp40-41, Figs5-11'],
        source_urls={
            'Cook 2004': 'https://content.wolfram.com/sites/13/2023/02/15-1-1.pdf',
            'Cook 2009': 'https://arxiv.org/pdf/0906.3248',
        },
        derived_normalizations=norm,
        C2_and_A4=checked('C2_A4_ETHER_REFERENCE', static_and_rightmoving_refs, norm),
        E=checked('E_ETHER_REFERENCE', leftmoving_refs, norm),
        formulas=dict(C2_C2_over='(cR-cL-9)/2', A4_A4_up='(aR-aL-30)/14',
                      E_E_over='(XR-XL-1)/2 mod4', E_E_up='(UR-UL-63)/14 mod6',
                      C2_E_over='(XR-cL+3)/2 mod4', A4_E_up='(UR-aL-44)/14 mod6'),
    )
    output = Path(output_dir) if output_dir is not None else HERE / 'results'
    output.mkdir(parents=True, exist_ok=True)
    output = output / 'distance-conventions.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    run()
    print('Passed all 7 C2, 3 A4, and 30 E-bar phases, with independently derived normalizations.')
    print(HERE / 'results/distance-conventions.json')


if __name__ == '__main__':
    main()
