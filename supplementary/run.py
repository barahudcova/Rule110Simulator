"""Run all release-local encoder checks using only Python's standard library."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(HERE), str(ROOT)]


def source_hashes():
    files = list(HERE.glob('*.py'))
    files += [ROOT/'pyca_verifier'/name for name in (
        'automaton.py', 'encoder.py', 'patterns.py', 'spacing_geometry.py', 'gui/simulation.py')]
    files += [ROOT/'pyca_verifier/data'/name for name in ('gliders.json', 'encoder_geometry.json')]
    files += list((ROOT/'pyca_verifier/data').glob('dict_*.json'))
    return {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def summarize(distance, program, static, chunks):
    assert distance['passed'] and static['passed'] and chunks['passed']
    assert program['component_calibration_matches_runtime']
    assert not program['measured_boundary_failures']
    assert not program['native_free_join_check']['failures']
    assert all(v['passed'] for v in program['full_phase_source_closure'].values())
    leaders = program['native_leader_joins']
    for name, failures in leaders.items():
        if name.endswith('_failures'):
            assert not failures, (name, failures)
    assert static['proper_productive_branch_bootstrap']['selected_Cook_up'] == 5
    return dict(
        particle_reference_phases=len(distance['C2_and_A4'])+len(distance['E']),
        direct_Cook_program_boundaries=program['measured_boundary_cases'],
        native_free_program_joins=program['native_free_join_check']['join_cases'],
        native_free_join_cells=program['native_free_join_check']['compared_cells'],
        grammar_states=program['grammar_state_count'], grammar_edges=len(program['grammar_edges']),
        grammar_closing_transitions=program['grammar_closing_count'],
        source_calibration_trials=program['native_component_source_trials'],
        exact_moving_packet_sources=program['absolute_moving_packets']['cases'],
        leader_preparations=leaders['preparation_cases'],
        short_consumption_seams=leaders['short_consumption_cases'],
        short_successor_frontiers=leaders['short_successor_cases'],
        component_to_short_frontiers=leaders['component_short_frontier_cases'],
        static_pair_temporal_rows=len(static['static_pairs']),
        ossifier_pair_temporal_rows=len(static['ossifier_pairs']),
        native_whole_ossifications=len(static['native_whole_ossifications']),
        native_atomic_contexts=len(static['native_atomic_crossings']),
        initial_guard_arithmetic_cases=sum(r['initial_guards_checked'] for r in static['program_dependent_geometric_bounds']),
        program_chunk_checks=chunks['program_chunk_cases'],
        ossifier_chunk_checks=chunks['ossifier_chunk_cases'],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'results', help='Destination for generated JSON reports')
    parser.add_argument('--record', action='store_true', help='Also update the compact, versioned verified-summary.json after a passing run')
    args = parser.parse_args()
    if not __debug__:
        parser.error('Run without Python -O; these checks require assertions.')
    if sys.version_info < (3, 10):
        parser.error('Python 3.10 or later is required.')
    args.output.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    started = perf_counter()
    summary = dict(status='running', scope='Finite local encoder alignment and native collision contracts',
                   source_sha256=before, checks=[], ready_or_decoder_checks_performed=False)
    try:
        import distance_conventions
        import program_joins
        import static_ossifier_joins
        import chunk_generation
        import pyca_verifier.encoder
        assert Path(pyca_verifier.encoder.__file__).resolve() == ROOT/'pyca_verifier/encoder.py'
        results = []
        for name, module in (('distance conventions', distance_conventions),
                             ('program joins and finite grammar', program_joins),
                             ('static symbols and ossifiers', static_ossifier_joins),
                             ('source continuation', chunk_generation)):
            print(f'Checking {name}...', flush=True)
            tick = perf_counter()
            entry = dict(name=name, passed=False)
            summary['checks'].append(entry)
            result = module.run(output_dir=args.output)
            assert result.get('passed') is not False, (name, result.get('failures'))
            results.append(result)
            entry.update(passed=True, seconds=round(perf_counter()-tick, 3))
        summary['counts'] = summarize(*results)
        assert source_hashes() == before, 'Audited source files changed during the run'
        summary['status'] = 'passed'
        summary['source_files_unchanged'] = True
        summary['assumptions_and_limits'] = [
            'Cook collision order and isolation, and continuing productive rotations, are hypotheses of the spacing argument.',
            'Raw-leader through-E^n numerical distances are replaced by complete native preparation and successor checks.',
            'Source concatenation and insertion phases are checked; arbitrary live-splice causal equivalence is not proved.',
            'Ready-word uniqueness and decoder completeness are outside this encoder audit.',
        ]
    except Exception as exc:
        summary['status'] = 'failed'
        summary['error'] = f'{type(exc).__name__}: {exc}'
        print(summary['error'], file=sys.stderr)
    summary['elapsed_seconds'] = round(perf_counter()-started, 3)
    summary['result_sha256'] = {p.name: sha256(p.read_bytes()).hexdigest()
                                for p in sorted(args.output.glob('*.json')) if p.name != 'summary.json'}
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    if summary['status'] != 'passed':
        return 1
    if args.record:
        # Keep only the small overview in the repository; detailed outputs stay ignored.
        (HERE/'verified-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(f"Passed all encoder checks in {summary['elapsed_seconds']:.1f}s. Reports: {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
