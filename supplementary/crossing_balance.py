"""Finite C2/E-bar reaction bounds and an exact crossing-ledger check.

This is a conditional scattering-network audit, not a global CA invariant.
No decoder, CTS reference, or readiness predicate is used.
"""
from __future__ import annotations

from hashlib import sha256
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from pyca_verifier.automaton import step
from pyca_verifier.patterns import ETHER, word
from static_ossifier_joins import COR, explained, hits, padded


def reaction_bounds():
    """All 7 x 30 incoming phase pairs in the passing residue class.

    The active interval starts when the two input particles cease to be
    independently recognizable with 14-cell ether guards. It ends at the
    start of 210 consecutive rows where the two output particles are
    guarded and separated. The last row must explain every non-ether
    window. The full joint phase period avoids mistaking an intermittent
    guarded output match for the end of all boundary effects.
    """
    ether_words = {ETHER[i:] + ETHER[:i] for i in range(14)}
    records = []
    for cp, ep in product(range(7), range(30)):
        allowed = []
        for gap in range(1, 5):
            c = COR['C2'][str(cp)]
            e = 15 * (len(word('C2', cp)) + 14*gap) + COR['E'][str(ep)]
            if (e + 4*ep - 15*c) % 120 == 45:
                allowed.append((gap, c, e))
        assert len(allowed) == 1
        gap, c, e = allowed[0]
        row = padded(word('C2', cp) + ETHER*gap + word('E', ep), tiles=100)
        start = None
        bounds = []
        outgoing_run = 0
        for tick in range(1001):
            cs, es = hits(row, 'C2'), hits(row, 'E')
            incoming = (len(cs) == len(es) == 1 and
                        cs[0]['anchor'] == c and es[0]['anchor'] == e)
            outgoing = (len(cs) == len(es) == 1 and
                        cs[0]['anchor'] == c+7 and es[0]['anchor'] == e-171 and
                        es[0]['x'] < cs[0]['x'])
            if start is None and not incoming:
                start = tick
            outgoing_run = outgoing_run+1 if outgoing else 0
            if start is not None and outgoing_run == 210:
                assert explained(row, ('C2', 'E'))
                assert (es[0]['phase']-tick-ep) % 30 == 24
                end = tick-209
                active_bounds = [b for t, b in bounds if start <= t < end]
                assert active_bounds
                records.append(dict(C2_phase=cp, E_phase=ep, gap_tiles=gap,
                    active_start=start, active_end_exclusive=end,
                    active_ticks=end-start,
                    defect_support_relative_to_incoming_C2=[
                        min(b[0] for b in active_bounds), max(b[1] for b in active_bounds)],
                    C2_displacement=7, E_intercept_displacement=-171,
                    E_phase_displacement=24))
                break
            if start is not None:
                bits = row.word()
                defects = [i for i in range(len(bits)-13)
                           if bits[i:i+14] not in ether_words]
                assert defects
                lo, hi = row.origin + defects[0] - c, row.origin + defects[-1] + 14 - c
                bounds.append((tick, (lo, hi)))
            row = step(row)
        else:
            raise AssertionError(('reaction_did_not_finish', cp, ep, gap))
    assert len(records) == 210
    return records


def ledger_check():
    """States 0,1,2 mean neither/right-only/both boundaries crossed.

    Every pair of birth/current states with nondecreasing per-particle state
    is checked. This includes particles between the endpoints at birth.
    The equality itself follows independently for each particle.
    """
    count = 0
    choices = [(birth, now) for birth in range(3) for now in range(birth, 3)]
    for n in range(7):
        for case in product(choices, repeat=n):
            crossed_right = sum((now >= 1) - (birth >= 1) for birth, now in case)
            crossed_left = sum((now >= 2) - (birth >= 2) for birth, now in case)
            birth_pending = sum(birth == 1 for birth, now in case)
            now_pending = sum(now == 1 for birth, now in case)
            displacement = 7*(crossed_right-crossed_left)
            assert displacement == 7*(now_pending-birth_pending)
            assert displacement <= 7*now_pending
            count += 1
    return dict(checked_state_pairs=count, maximum_particles=6,
                all_time_proof='Per-particle indicator identity; see CROSSING_BALANCE.md',
                gap_identity='g(t)-g(birth)=7*(B(t)-B(birth))',
                ledger_roles='E-bar identities survive both endpoint crossings; boundaries survive')


def boundary_allowance(records):
    """Check the numerical constants in the conditional packing lemma.

    Read and hash-check the independently produced density and emission
    receipts. The scattering-network embedding remains an explicit premise.
    """
    lo = min(r['defect_support_relative_to_incoming_C2'][0] for r in records)-7
    hi = max(r['defect_support_relative_to_incoming_C2'][1] for r in records)
    widths = [len(word('E', p)) for p in range(30)]
    corrections = [Fraction(COR['E'][str(p)], 15) for p in range(30)]
    ether_words = {ETHER[i:] + ETHER[:i] for i in range(14)}
    for p in range(30):
        bits = ETHER + word('E', p) + ETHER
        # Each free E has at least one distinguishing window meeting its
        # core. A 14-window meeting [x,x+w) starts in [x-13,x+w-1].
        assert any(bits[j:j+14] not in ether_words and
                   j < 14+len(word('E', p)) and j+14 > 14
                   for j in range(len(bits)-13))
    lower = lo-max(widths)+1+min(corrections)
    upper = hi-1+max(corrections)
    collar = 100
    assert -collar <= lower <= upper <= collar
    assumed_minimum_free_spacing = 14
    ideal_offsets = []
    for record in records:
        cp, ep, gap = record['C2_phase'], record['E_phase'], record['gap_tiles']
        c = COR['C2'][str(cp)]
        e = 15*(len(word('C2', cp))+14*gap)+COR['E'][str(ep)]
        ideal_time = Fraction(e-15*c, 4)
        ideal_offsets.append((record['active_start']-ideal_time,
                              record['active_end_exclusive']-ideal_time))
    first_offset = min(a for a, b in ideal_offsets)
    last_offset = max(b for a, b in ideal_offsets)
    assert (first_offset, last_offset) == (Fraction(-421, 4), Fraction(263, 4))
    density_path = HERE/'passing-particle-spacing.json'
    emission_path = HERE/'passing-source-seams.json'
    density = json.loads(density_path.read_text())
    emission = json.loads(emission_path.read_text())
    assert density['finite_checks_passed'] and emission['passed']
    for receipt in (density, emission):
        hashes = receipt.get('source_sha256', receipt.get('sources'))
        assert hashes
        for name, expected in hashes.items():
            assert sha256((ROOT/name).read_bytes()).hexdigest() == expected, name
    free_min_e = density['free_pair_spacing']['minimum_delta_e']
    source_min_e = emission['minimum_source_e_difference']
    assert free_min_e >= 15*14
    # Before a fixed surviving C2, successive reads only remove upstream
    # C2s. A read separation d adds 684*d to this source difference.
    assert source_min_e >= 1325
    minimum_ideal_time_gap = Fraction(source_min_e-15*7, 4)
    active_per_endpoint = int((last_offset-first_offset)//minimum_ideal_time_gap)+1
    assert minimum_ideal_time_gap >= 305 and active_per_endpoint == 1
    arrival_constant = Fraction(2*collar, 14)+1+2*active_per_endpoint
    assert arrival_constant <= 20
    return dict(
        scope='Uniform boundary count in the intended FIFO scattering network, using independently checked emission and free-particle bounds',
        global_CA_embedding_proved=False,
        companion_receipts={p.name:sha256(p.read_bytes()).hexdigest()
                            for p in (density_path, emission_path)},
        current_anchor_defect_collar=[lo, hi],
        maximum_E_core_width=max(widths),
        E_normalized_position_minus_core_start=[str(min(corrections)), str(max(corrections))],
        derived_free_position_collar=[str(lower), str(upper)],
        chosen_symmetric_collar=collar,
        assumed_minimum_free_spacing=assumed_minimum_free_spacing,
        conditional_arrival_argument=dict(
            ideal_time='(e-15*c)/4',
            active_window_offsets=[str(first_offset), str(last_offset)],
            minimum_source_e_difference=source_min_e,
            minimum_incoming_e_difference=source_min_e,
            incoming_formula='delta_e_incoming=delta_e_source+684*d, d>=0',
            incoming_bound_verified_in_intended_network=True,
            minimum_ideal_time_gap=str(minimum_ideal_time_gap),
            active_per_endpoint=active_per_endpoint,
            additive_count_bound=str(arrival_constant),
            conditional_result='B(t) <= g(t)/14 + 20'),
        assumptions=['Surviving facing C2 endpoints, with no other C2 in their gap',
                     'FIFO E-bar passing and no interior reaction or disappearance',
                     'Finite atomic windows compose in the ordered incoming stream',
                     'Free E-bar normalized anchors at least fourteen cells apart'])


def run():
    if not __debug__:
        raise RuntimeError('Run without -O; assertions perform the verification')
    records = reaction_bounds()
    lower = min(r['defect_support_relative_to_incoming_C2'][0] for r in records)
    upper = max(r['defect_support_relative_to_incoming_C2'][1] for r in records)
    sources = [Path(__file__), HERE/'static_ossifier_joins.py', HERE/'distance_conventions.py',
               ROOT/'pyca_verifier/automaton.py', ROOT/'pyca_verifier/patterns.py',
               ROOT/'pyca_verifier/data/gliders.json']
    result = dict(passed=True,
        scope='Exact isolated reactions and conditional particle accounting; not a global embedding theorem',
        sources={str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in sources},
        reaction_count=len(records),
        maximum_active_ticks=max(r['active_ticks'] for r in records),
        union_active_defect_support=[lower, upper],
        uniform_simultaneous_boundary_count_in_intended_network=True,
        ledger=ledger_check(), boundary_allowance=boundary_allowance(records), reactions=records)
    output = HERE/'crossing-balance-summary.json'
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('sources', 'reactions')}, indent=2))
    return result


if __name__ == '__main__':
    run()
