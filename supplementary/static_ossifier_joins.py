"""Audit this release's static/ossifier joins in Cook's native distance units.

No runtime files are modified; no ready-word or decoder recognizer is used.
Run with any Python >=3.10 from any directory. The paired report distinguishes
finite binary measurements from conditional collision-network arithmetic.
"""
from pathlib import Path
from hashlib import sha256
from itertools import product
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from pyca_verifier.automaton import BitRow, step
from pyca_verifier.encoder import Encoder, Initialization, _base_ossifier_gap
from pyca_verifier.patterns import ETHER, TABLES, word
from pyca_verifier.spacing_geometry import (calibration,
    compact_initial_gap_certificate, compact_long_gap_certificate)
if __package__:
    from .distance_conventions import derive_normalizations, enabled_checks, checked
else:
    from distance_conventions import derive_normalizations, enabled_checks, checked

COR = derive_normalizations(include_controls=True)
PERIOD = {'C2': 7, 'A4': 3, 'E': 30, 'acceptor': 3, 'rejector': 3}
COEFFICIENT = {'C2': (1, 0), 'A4': (3, -2), 'E': (15, 4),
               'acceptor': (3, -2), 'rejector': (3, -2)}


def hits(row, family):
    result = []
    text = row.word()
    for p in range(PERIOD[family]):
        pattern = ETHER + word(family, p) + ETHER
        pos = text.find(pattern)
        while pos >= 0:
            x = row.origin + pos + 14
            a, b = COEFFICIENT[family]
            result.append({'x': x, 'phase': p,
                'anchor': a*x + b*row.time + COR[family][str(p)]})
            pos = text.find(pattern, pos+1)
    return sorted(result, key=lambda h: h['x'])


def over(delta):
    assert (delta-9) % 2 == 0
    return (delta-9)//2


def up(delta):
    assert (delta-30) % 14 == 0
    return (delta-30)//14


def padded(bits, tiles=100):
    return BitRow.from_word(ETHER*tiles + bits + ETHER*tiles, origin=-14*tiles)


def free_orbits():
    records = []
    for family in ('C2', 'A4', 'E'):
        period = PERIOD[family]
        for p in range(period):
            row = padded(word(family, p))
            initial = hits(row, family)
            assert len(initial) == 1
            anchor = initial[0]['anchor']
            for t in range(1, period+1):
                row = step(row)
                current = hits(row, family)
                assert len(current) == 1 and current[0]['anchor'] == anchor
                assert current[0]['phase'] == (p+t) % period
            records.append({'family': family, 'starting_phase': p,
                'ticks': period, 'constant_normalized_anchor': anchor,
                'return_displacement': current[0]['x']-initial[0]['x']})
    return records


def static_joins():
    internal, joins = [], []
    for symbol in 'YN':
        expected = [18, 18 if symbol == 'Y' else 10, 14]
        for phase in range(7):
            row = padded(word(symbol, phase))
            anchors = [h['anchor'] for h in hits(row, 'C2')]
            assert len(anchors) == 4
            assert anchors == calibration()['static_cores'][symbol][str(phase)]
            distances = [over(b-a) for a, b in zip(anchors, anchors[1:])]
            assert distances == expected
            internal.append({'symbol': symbol, 'phase': phase,
                'anchors': anchors, 'cook_over': distances})
    # These are the two initial cuts actually chosen by the encoder. Evolving
    # each pair traverses all seven common temporal phases without changing
    # its 684-cell spatial pitch.
    for phase in (0, 4):
        for left, right in product('YN', repeat=2):
            gap = 14*(1 + (6 if left == 'Y' else 7) + 32)
            row = padded(word(left, phase) + ETHER*(gap//14) + word(right, phase))
            assert len(word(left, phase))+gap == 684
            first_anchors = None
            for t in range(7):
                particles = hits(row, 'C2')
                anchors = [h['anchor'] for h in particles]
                assert len(anchors) == 8
                if first_anchors is None:
                    first_anchors = anchors
                assert anchors == first_anchors
                delta = anchors[4]-anchors[3]
                assert delta == (557 if left == 'Y' else 573)
                distance = over(delta)
                assert distance >= 6 and distance % 4 == 2
                joins.append({'left': left, 'right': right,
                    'encoder_phase': phase, 'tick': t,
                    'particle_phases': [h['phase'] for h in particles],
                    'boundary_anchor_gap': delta, 'cook_over': distance})
                row = step(row)
    return internal, joins


def ossifier_joins():
    internal, joins = [], []
    for p in range(3):
        row = padded(word('O', p))
        anchors = [h['anchor'] for h in hits(row, 'A4')]
        assert len(anchors) == 4
        assert anchors == calibration()['ossifier_cores'][str(p)]
        distances = [up(b-a) for a, b in zip(anchors, anchors[1:])]
        assert distances == [83, 113, 77]
        internal.append({'phase': p, 'anchors': anchors, 'cook_up': distances})
    # All parity/residue classes plus the actual minimum recurring short gap.
    for gap in list(range(1, 29, 2)) + [179]:
        for right_phase, (left_phase, correction) in Encoder.OSS.items():
            text = word('O', left_phase) + ETHER*(gap+correction) + word('O', right_phase)
            row = padded(text)
            first_anchors = None
            for t in range(3):
                anchors = [h['anchor'] for h in hits(row, 'A4')]
                assert len(anchors) == 8
                if first_anchors is None:
                    first_anchors = anchors
                assert anchors == first_anchors
                delta = anchors[4]-anchors[3]
                assert delta == 42*gap+58
                distance = up(delta)
                assert distance == 3*gap+2 and distance % 6 == 5
                joins.append({'raw_gap_tiles': gap, 'left_phase': left_phase,
                    'right_phase': right_phase, 'tick': t,
                    'phase_correction_tiles': correction,
                    'boundary_anchor_difference': delta, 'cook_up': distance})
                row = step(row)
    return internal, joins


def initial_heads():
    records = []
    for symbol, phase in [('Y', 0), ('N', 4)]:
        row = padded(word(symbol, phase) + ETHER*2 + word('L', 2), tiles=150)
        c = hits(row, 'C2')[-1]['anchor']
        head = hits(row, 'E')[0]
        k = head['anchor'] + 4*head['phase']
        assert k-15*c == 825 and (k-15*c) % 120 == 105
        # A local consumption witness supplies the first invisible. Its full
        # E phase is essential: the scalar trajectory intercept is not enough.
        for _ in range(1200):
            row = step(row)
        outgoing = hits(row, 'E')
        assert len(outgoing) == 2
        control = 'acceptor' if symbol == 'Y' else 'rejector'
        control_hits = hits(row, control)
        assert len(control_hits) == 1 and control_hits[0]['x'] > outgoing[-1]['x']
        assert explained(row, ('E', control))
        first = outgoing[0]
        tau = (first['phase']-row.time) % 30
        assert (first['anchor']+14*tau) % 5 == 0
        u = (first['anchor']+14*tau)//5
        assert u == (448 if symbol == 'Y' else 406)
        first_k = first['anchor']+4*tau
        first_static_crossing = []
        for preceding in 'YN':
            preceding_c = -684+calibration()['static_cores'][preceding][str(phase)][-1]
            residue = (first_k-15*preceding_c) % 120
            assert residue == 45
            first_static_crossing.append({'preceding_symbol': preceding,
                'K_minus_15c_mod120': residue, 'cook_over': 3})
        shift = 20 if symbol == 'Y' else 23
        bootstrap = []
        for n in range(1, 13):
            for guard in range(1, 21, 2):
                # Head core is at 56+684(n−1) relative to the start of tape().
                # First invisible crosses 4(n−1) prior C2s: U changes by +33
                # per intended crossing, using the native scattering contract.
                u_at_a4 = u + 3*(56+684*(n-1)) + 33*4*(n-1)
                a = -3*len(word('O', 2)) + 42*shift + calibration()['ossifier_cores']['2'][-1] - 42*guard
                assert (u_at_a4-a) % 84 == 44
                bootstrap.append({'n': n, 'odd_guard': guard,
                    'first_invisible_U_minus_a_mod84': (u_at_a4-a) % 84})
        records.append({'head': symbol, 'encoder_symbol_phase': phase,
            'leading_E_phase': head['phase'], 'leading_E_K_minus_15c': k-15*c,
            'leading_E_K_minus_15c_mod120': (k-15*c) % 120,
            'consumption_witness_ticks': 1200,
            'outgoing_control': control, 'outgoing_control_particle': control_hits[0],
            'all_nonether_cells_explained': True,
            'first_invisible': first, 'first_invisible_tau': tau,
            'first_invisible_U_relative_to_static_core': u,
            'first_invisible_crosses_previous_static': first_static_crossing,
            'conditional_bootstrap_cases': bootstrap})
    return records


def explained(row, families):
    """Require every non-ether 14-window to lie in a complete outgoing word."""
    rotations = {ETHER[k:]+ETHER[:k] for k in range(14)}
    spans = [(h['x']-row.origin-14,
              h['x']-row.origin+len(word(family, h['phase']))+14)
             for family in families for h in hits(row, family)]
    text = row.word()
    return all(text[i:i+14] in rotations or any(a <= i and i+14 <= b for a, b in spans)
               for i in range(len(text)-13))


def native_ossifications():
    """Both data values, all O/data phases in the elementary conversion class.

    These are the four-E moving words used by the native frontier catalogue.
    This check establishes the actual O packet's deposition geometry; linking
    every emitted packet to these words is a separate source grammar check.
    """
    moving = {}
    for symbol in 'YN':
        phases, gaps = ((0, 7, 14, 21), (7, 10, 6)) if symbol == 'Y' else ((0, 7, 20, 27), (7, 12, 7))
        core = word('E', phases[0])+''.join(ETHER*g+word('E', p) for g, p in zip(gaps, phases[1:]))
        row = padded(core)
        for tick in range(30):
            es = hits(row, 'E')
            assert len(es) == 4
            start = es[0]['x']-row.origin
            end = es[-1]['x']-row.origin+len(word('E', es[-1]['phase']))
            moving[symbol, es[0]['phase']] = row.word()[start:end]
            row = step(row)
    records = []
    for symbol, op, mp, gap in product('YN', range(3), range(30), (4, 5)):
        if (mp-op) % 3 != 2:
            continue
        row = padded(word('O', op)+ETHER*gap+moving[symbol, mp], tiles=200)
        aa = [h['anchor'] for h in hits(row, 'A4')][::-1]
        es = hits(row, 'E')
        ee = [h['anchor'] for h in es]
        assert len(aa) == len(ee) == 4
        first_u = (ee[0]+14*es[0]['phase'])//5
        phase_residue = (first_u-aa[0]) % 84
        assert phase_residue in (30, 72)
        for _ in range(2300):
            row = step(row)
        cc = [h['anchor'] for h in hits(row, 'C2')][::-1]
        assert len(cc) == 4 and explained(row, ('C2',))
        distances = [over(a-b) for a, b in zip(cc, cc[1:])][::-1]
        assert distances == [18, 18 if symbol == 'Y' else 10, 14]
        kappas = [21*(c-7*(3-i))-2*a-(e-171*i) for i, (c, a, e) in enumerate(zip(cc, aa, ee))]
        assert kappas == [-24 if phase_residue == 30 else 60]*4
        records.append({'symbol': symbol, 'O_phase': op, 'moving_phase': mp,
            'gap_tiles': gap, 'first_U_minus_a_mod84': phase_residue,
            'ticks': 2300, 'outgoing_cook_over': distances,
            'per_conversion_kappa': kappas, 'all_nonether_cells_explained': True})
    return records


def atomic_crossings():
    """Full native phase classes and their exact scattering maps."""
    records = []
    for family, gaps in [('A4', (4, 5)), ('C2', range(1, 5))]:
        for lp, ep, gap in product(range(PERIOD[family]), range(30), gaps):
            row = padded(word(family, lp)+ETHER*gap+word('E', ep), tiles=160)
            left = hits(row, family)[0]
            incoming = hits(row, 'E')[0]
            tau = incoming['phase']
            if family == 'A4':
                u = (incoming['anchor']+14*tau)//5
                residue = (u-left['anchor']) % 84
                expected = {2: 'other', 16: 'other', 30: 'proper_ossification',
                            44: 'invisible_crossing', 58: 'alternative_ossification',
                            72: 'alternative_ossification'}[residue]
                cook_distance = ((residue-44)//14) % 6
            else:
                k = incoming['anchor']+4*tau
                residue = (k-15*left['anchor']) % 120
                expected = 'C2_crossing' if residue == 45 else 'other'
                cook_distance = ((residue+45)//30) % 4
            for _ in range(1000):
                row = step(row)
            output = {f: hits(row, f) for f in ('A4', 'E', 'C2')}
            facts = {}
            if expected in ('C2_crossing', 'invisible_crossing'):
                other = 'C2' if family == 'A4' else 'A4'
                assert len(output['E']) == len(output[family]) == 1 and not output[other]
                assert output['E'][0]['x'] < output[family][0]['x']
                assert explained(row, ('E', family))
                delta_e = output['E'][0]['anchor']-incoming['anchor']
                delta_left = output[family][0]['anchor']-left['anchor']
                out_tau = (output['E'][0]['phase']-row.time) % 30
                phase_change = (out_tau-tau) % 30
                if family == 'A4':
                    assert (delta_e, delta_left, phase_change) == (-94, -175, 1)
                    out_u = (output['E'][0]['anchor']+14*out_tau)//5
                    assert (out_u-u) % 84 == 68  # −16 modulo 84
                else:
                    assert (delta_e, delta_left, phase_change) == (-171, 7, 24)
                    in_u = (incoming['anchor']+14*tau)//5
                    out_u = (output['E'][0]['anchor']+14*out_tau)//5
                    assert (out_u-in_u) % 84 == 33
                facts = {'delta_e': delta_e, 'delta_other_anchor': delta_left,
                         'E_phase_change': phase_change, 'all_nonether_cells_explained': True}
            elif 'ossification' in expected:
                assert len(output['C2']) == 1 and not output['E'] and not output['A4']
                assert explained(row, ('C2',))
                kappa = 21*output['C2'][0]['anchor']-2*left['anchor']-incoming['anchor']
                assert kappa == {30: -24, 58: -10, 72: 60}[residue]
                facts = {'kappa': kappa, 'all_nonether_cells_explained': True}
            else:
                # Other phases are controls; don't give their residue-selected
                # names the status of a certified semantic endpoint.
                facts = {'semantic_endpoint_certified': False,
                         'intact_output_particle_counts': {f: len(h) for f, h in output.items()}}
            records.append({'left_family': family, 'left_phase': lp,
                'E_phase': ep, 'gap_tiles': gap, 'full_phase_residue': residue,
                'cook_up' if family == 'A4' else 'cook_over': cook_distance,
                'expected_reaction': expected, **facts})
    return records


def geometry_arithmetic():
    programs = [
        ('YYYYYY',), ('NNNNNN',), ('YNNNNY',),
        ('YYYYYY', '', ''), ('YNYYNY', '', 'YNNNNY', ''),
        ('YNNNNYYNNNNY',)*3, ('NNNNNN', '', '', '', 'YYYYYY'*2),
        ('YNYNYN', 'Y'*18, '', 'N'*12, ''),
    ]
    records = []
    for program in programs:
        init = Initialization('Y', program)
        cert = compact_long_gap_certificate(init)
        enc = Encoder(init)
        assert cert.maximum_unproductive_steps == 2*len(program)-2
        assert enc.short_distance % 2 == enc.long_distance % 2 == 1
        assert enc.long_distance >= cert.minimum_gap_tiles
        short_margin = 84*enc.short_distance - cert.short_source_score + 350
        long_margin = 84*enc.long_distance - cert.long_source_score + 350
        assert min(short_margin, long_margin) >= 21*573
        initial_checks = 0
        guards = []
        for n in range(1, 8):
            for symbols in product('YN', repeat=n):
                tape = ''.join(symbols)
                candidate = compact_initial_gap_certificate(Initialization(tape, program))
                if candidate is None:
                    continue
                assert candidate.selected_guard_tiles % 2 == 1
                assert candidate.gap_lower_bound_numerator >= 21*573
                assert candidate.ready_guard_tiles >= 4
                initial_checks += 1
                if tape in ('Y', 'YY', 'YYY', 'NY', 'NYY', 'NNY', 'NNNNNNY'):
                    guards.append({'tape': tape, **candidate.as_dict()})
        records.append({'appendants': program, 'long_gap_certificate': cert.as_dict(),
            'inherited_raw_gap_tiles': _base_ossifier_gap(init),
            'selected_short_tiles': enc.short_distance,
            'selected_long_tiles': enc.long_distance,
            'cook_short_up': 3*enc.short_distance+2,
            'cook_long_up': 3*enc.long_distance+2,
            'lower_bound_numerators': {'short': short_margin, 'long': long_margin},
            'initial_guards_checked': initial_checks, 'sample_initial_guards': guards})
    return records


def productive_bootstrap():
    """Proper conversion phase for arbitrary initial lengths, conditional on
    source grammar U_i^0=U_0+34(r_i−1)+35j and the intended FIFO crossings.
    """
    pc_phase, pc_gap = TABLES['yn']['20']['0']
    ap, gap = calibration()['components']['PC'][str(pc_phase)]['witnesses'][0]
    component_x = len(word('acceptor', ap))+14*gap
    row = padded(word('acceptor', ap)+ETHER*gap+word('PC', pc_phase), tiles=160)
    for _ in range(1200):
        row = step(row)
    es, aa = hits(row, 'E'), hits(row, 'acceptor')
    assert len(es) == 2 and len(aa) == 1 and explained(row, ('E', 'acceptor'))
    e_relative = es[0]['anchor']-15*component_x
    tau = (es[0]['phase']-row.time) % 30
    pc_x_from_L = len(word('L', 2))+14*pc_gap
    U_from_L = 3*pc_x_from_L+(e_relative+14*tau)//5
    K_from_L = 15*pc_x_from_L+e_relative+4*tau
    assert (U_from_L, K_from_L) == (1434, 7140)
    cases = []
    for symbol, phase, shift in [('Y', 0, 20), ('N', 4, 23)]:
        for n, guard in product(range(1, 13), range(1, 21, 2)):
            tape_width = 56+684*(n-1)+len(word(symbol, phase))
            U0 = 3*(tape_width+28)+U_from_L
            K0 = 15*(tape_width+28)+K_from_L
            a0 = -58-42*guard+42*shift
            c_right = 56+684*(n-1)+calibration()['static_cores'][symbol][str(phase)][-1]
            up_residue = (U0-a0+48*n-34) % 84
            over_residue = (K0-30-15*c_right) % 120
            assert up_residue == 30 and over_residue == 45
            cases.append({'head': symbol, 'n': n, 'odd_guard': guard,
                'productive_U_minus_a_mod84': up_residue,
                'data_crossing_initial_C2_K_minus_15c_mod120': over_residue})
    return {'native_first_PC_phase': pc_phase, 'PC_x_relative_to_L': pc_x_from_L,
        'native_first_E_relative_e': e_relative, 'native_first_E_tau': tau,
        'first_source_U_relative_to_L': U_from_L,
        'first_source_K_relative_to_L': K_from_L,
        'conditional_cases': cases,
        'assumptions': ['Source grammar U_i^0=U_0+34(r_i-1)+35j modulo84',
            'Accepted appendants have 24k constituent E-bars: i-j divisible by24',
            'C_i=4n+i-4r_i ordinary C2 crossings and 2r_i invisible/A4 crossings',
            'Each preceding native crossing occurs with its certified phase and isolation'],
        'all_input_reduction': 'U_i-a_i=U_0-a_0+48n-34+252r_i+49(i-j) modulo84',
        'selected_Cook_up': 5, 'selected_kappa': -24}


def run(output_dir=None):
    enabled_checks()
    static, static_pairs = checked('STATIC_JOIN', static_joins)
    ossifiers, ossifier_pairs = checked('OSSIFIER_JOIN', ossifier_joins)
    result = {'passed': True,
        'scope': 'Release finite native join identities and conditional affine gap arithmetic; not all-time encounter ordering',
        'ready_or_decoder_checks_performed': False,
        'audit_script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'independently_derived_normalizations': COR,
        'source_hashes': {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest()
            for p in [HERE/'distance_conventions.py', ROOT/'pyca_verifier/encoder.py', ROOT/'pyca_verifier/spacing_geometry.py',
                      ROOT/'pyca_verifier/automaton.py', ROOT/'pyca_verifier/patterns.py',
                      ROOT/'pyca_verifier/data/gliders.json', ROOT/'pyca_verifier/data/encoder_geometry.json',
                      *(ROOT/'pyca_verifier/data'/f'dict_{name}.json' for name in TABLES)]},
        'free_particle_orbits': checked('FREE_PARTICLE_ORBIT', free_orbits),
        'internal_static': static, 'static_pairs': static_pairs,
        'internal_ossifier': ossifiers, 'ossifier_pairs': ossifier_pairs,
        'initial_head_and_invisible': checked('INITIAL_HEAD_AND_INVISIBLE', initial_heads),
        'native_whole_ossifications': checked('WHOLE_OSSIFICATION', native_ossifications),
        'native_atomic_crossings': checked('ATOMIC_CROSSING', atomic_crossings),
        'proper_productive_branch_bootstrap': checked('PRODUCTIVE_BOOTSTRAP', productive_bootstrap),
        'program_dependent_geometric_bounds': checked('GEOMETRIC_GAP_BOUND', geometry_arithmetic)}
    output = Path(output_dir) if output_dir is not None else HERE / 'results'
    output.mkdir(parents=True, exist_ok=True)
    (output/'static-ossifier-joins.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    result = run()
    print(json.dumps({'passed': True, 'free_phase_orbits': len(result['free_particle_orbits']),
        'internal_static_phases': len(result['internal_static']), 'static_pair_rows': len(result['static_pairs']),
        'internal_ossifier_phases': len(result['internal_ossifier']), 'ossifier_pair_rows': len(result['ossifier_pairs']),
        'head_cases': len(result['initial_head_and_invisible']),
        'native_whole_ossifications': len(result['native_whole_ossifications']),
        'native_atomic_crossings': len(result['native_atomic_crossings']),
        'initial_guard_cases': sum(r['initial_guards_checked'] for r in result['program_dependent_geometric_bounds'])}, indent=2))


if __name__ == '__main__':
    main()
