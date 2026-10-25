"""Deterministic complementary end-to-end decoder campaign (standard library).

Every accepted case has an independently checked nonhalting/productive finite
CTS prefix. This is a test-prefix condition, not an assertion of productivity
for all future time. No reference data enter the encoder, CA, ready detector,
or decoder; the callback only records and compares their completed outputs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import random
import sys
from time import perf_counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LOADED_DRIVER_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))

from pyca_verifier.canonical_decoder import Decoder
from pyca_verifier.encoder import Initialization, build_seed
from pyca_verifier.ready import ReadyDetector
from pyca_verifier.runner import run_multisteps

SEED = 11020261023
TEST_REFINEMENT = {
    'case': 'seeded-z1-v3', 'original_multisteps': 24, 'final_multisteps': 6,
    'reason': 'The redundant 24-step/18-letter case allocated 432 produced-letter '
              'ossifiers and a 4,887,986-cell seed. A six-step probe preserves '
              '18-letter train coverage; other cases retain 24-step horizons.',
    'original_driver_sha256': '13e68c50ccfa392a04db296d980d6dca9c12a85093f335b63c87e9e47278f590',
    'original_run_status': 'interrupted; not counted as passed',
    'original_ready_rows_saved': 5, 'original_last_saved_tick': 167944,
    'original_partial_rows': 'results/decoder-seeded/interrupted-initial-goals/'
                             'seeded-z1-v3/ready-rows.recovered.jsonl.gz',
}


def digest_file(path):
    return sha256(path.read_bytes()).hexdigest()


def runtime_hashes():
    """Pin all shipped Python and JSON; unrelated output files are excluded."""
    paths = sorted(p for p in (ROOT / 'pyca_verifier').rglob('*')
                   if p.suffix in ('.py', '.json'))
    return {str(p.relative_to(ROOT)): digest_file(p) for p in paths}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def expected_prefix(tape, appendants, steps):
    """Small independent CTS implementation, with no runtime CTS imports."""
    states = []
    productive = []
    for pointer in range(steps + 1):
        states.append({'tape': tape, 'appendant_index': pointer % len(appendants)})
        if pointer == steps:
            break
        if not tape:
            return states, productive, 'halting_prefix'
        append = appendants[pointer % len(appendants)] if tape[0] == 'Y' else ''
        productive.append(bool(append))
        tape = tape[1:] + append
    if not states[-1]['tape']:
        return states, productive, 'halting_prefix'
    z = len(appendants)
    for offset in range(0, steps - z + 1, z):
        if not any(productive[offset:offset+z]):
            return states, productive, 'unproductive_aligned_rotation'
    return states, productive, None


def generate_cases():
    """32 reproducible cases, four distinct parameter families at each z."""
    rng = random.Random(SEED)
    cases = []
    rejected = Counter()
    for z in range(1, 9):
        for variant in range(4):
            r = (0, z-1, z//2, (z+1)//2)[variant] % z
            goal = (6 if z == 1 else 24) if variant == 3 else 12
            preflight_steps = ((goal + z - 1) // z) * z
            for attempt in range(1, 10001):
                def letters(length, density):
                    return ''.join('Y' if rng.random() < density else 'N'
                                   for _ in range(length))
                if variant == 0:
                    # Short arbitrary appendants, including a block of empties.
                    rules = [letters(6, .65) if rng.random() > .25 else ''
                             for _ in range(z)]
                elif variant == 1:
                    # Equal appendants deliberately defeat content-only pointers.
                    base = letters(6, .65)
                    rules = [base if i % 3 != 1 else '' for i in range(z)]
                elif variant == 2:
                    # One longer N-biased word, amid short words and empties.
                    rules = [letters(6, .6) if rng.random() > .2 else ''
                             for _ in range(z)]
                    rules[r] = letters(12, .4)
                else:
                    # Long Y-biased words with a long consecutive empty block.
                    rules = [letters(6, .8) for _ in range(z)]
                    if z >= 4:
                        for i in range(1, min(z-1, 4)):
                            rules[i] = ''
                    rules[r] = letters(18, .8)
                if not rules[0]:
                    rules[0] = letters(6, .7)
                if not rules[r]:
                    rules[r] = letters(6, .7)
                # Start with a prescribed first-productive offset; later bits
                # are independently sampled. z=1 necessarily needs every read
                # productive, so use an all-Y initial prefix of sufficient size.
                tail_length = rng.randrange(2, 9)
                tape = 'N'*r + 'Y' + letters(tail_length, .7)
                if z == 1:
                    tape = 'Y' * (preflight_steps + 1)
                states, productive, reason = expected_prefix(tape, rules, preflight_steps)
                if reason is not None:
                    rejected[reason] += 1
                    continue
                if next(i for i, value in enumerate(productive) if value) != r:
                    raise AssertionError('Incorrect constructed first-productive index')
                cases.append({'id': f'seeded-z{z}-v{variant}', 'tape': tape,
                    'appendants': rules, 'multisteps': goal,
                    'first_productive_offset': r, 'variant': variant,
                    'selection_attempts': attempt,
                    'preflight_steps': preflight_steps,
                    'productive_indices': [i for i, value in enumerate(productive) if value],
                    'preflight_status': 'nonhalting and productive in each aligned full rotation',
                    'expected': states[:goal+1]})
                break
            else:
                raise RuntimeError(f'Unable to sample z={z}, variant={variant}')
    return cases, dict(rejected)


def check_case(case, output, hashes, max_ticks):
    destination = Path(output) / case['id']
    destination.mkdir(parents=True, exist_ok=True)
    summary_path = destination / 'summary.json'
    if summary_path.exists():
        saved = json.loads(summary_path.read_text())
        if saved.get('runtime_sha256') == hashes and saved.get('case') == case:
            return saved
    discrepancies = []
    ready_count = 0
    with gzip.open(destination / 'ready-rows.jsonl.gz', 'wt', encoding='utf-8') as rows:
        def observe(row, event):
            nonlocal ready_count
            index = ready_count
            ready_count += 1
            expected = case['expected'][index] if index < len(case['expected']) else None
            row_text = row.word()
            record = {'case': case['id'], 'ready_index': index,
                      'initial_tape': case['tape'], 'appendants': case['appendants'],
                      'tick': row.time, 'origin': row.origin, 'width': row.width,
                      'bits': row_text, 'binary_sha256': sha256(row_text.encode()).hexdigest(),
                      'event': event, 'independent_expected': expected}
            rows.write(json.dumps(record, separators=(',', ':')) + '\n')
            rows.flush()
            if expected is None or event['status'] != 'decoded' or any(
                    event.get(key) != expected[key] for key in ('tape', 'appendant_index')):
                problem = {'ready_index': index, 'tick': row.time, 'expected': expected,
                           'observed': event, 'row_file': 'ready-rows.jsonl.gz'}
                discrepancies.append(problem)
                write_json(destination / 'independent-mismatches.json', discrepancies)
                print(json.dumps({'FAILURE': case['id'], **problem}), flush=True)
        started = perf_counter()
        try:
            report = run_multisteps(Initialization(case['tape'], tuple(case['appendants'])),
                                   multisteps=case['multisteps'], max_ticks=max_ticks,
                                   on_ready=observe)
        except Exception as exc:
            summary = {'case': case, 'status': 'error', 'error': repr(exc),
                       'runtime_sha256': hashes, 'ready_states_saved': ready_count,
                       'execution_driver_sha256': LOADED_DRIVER_SHA256,
                       'elapsed_seconds': perf_counter()-started}
            write_json(summary_path, summary)
            raise
    snapshot = report.pop('failure_snapshot', None)
    if snapshot is not None:
        with gzip.open(destination / 'failure-row.json.gz', 'wt', encoding='utf-8') as stream:
            json.dump(snapshot, stream, separators=(',', ':'))
        report['failure_snapshot'] = {'file': 'failure-row.json.gz', 'time': snapshot['time'],
                                      'origin': snapshot['origin'], 'width': snapshot['width']}
    write_json(destination / 'report.json', report)
    goal = report['verification_goal']
    summary = {'case': case, 'status': goal['status'] if not discrepancies else 'failed',
               'reason': goal['reason'], 'checked_multisteps': goal['checked_multisteps'],
               'native_ticks': report['evolution']['native_ticks'],
               'ready_states': len(report['decoder']['events']), 'ready_states_saved': ready_count,
               'unsupported_events': report['decoder']['unsupported_events'],
               'runtime_mismatch_ticks': report['decoder']['mismatch_ticks'],
               'independent_mismatches': discrepancies,
               'ready_c2_phase_counts': dict(Counter(str(e['c2_phase'])
                    for e in report['readiness']['events'])),
               'initial_seed_is_ready': report['initial_seed_is_ready'],
               'elapsed_seconds': report['evolution']['elapsed_seconds'],
               'resource_plan': goal['resource_plan'],
               'runtime_sha256': hashes,
               'execution_driver_sha256': LOADED_DRIVER_SHA256,
               'final_runtime_sha256_matches': runtime_hashes() == hashes,
               'rows': f"{case['id']}/ready-rows.jsonl.gz"}
    if ready_count != len(report['decoder']['events']):
        raise AssertionError('Saved ready-row count disagrees with run')
    if summary['status'] == 'passed' and ready_count != case['multisteps']+1:
        raise AssertionError('Incomplete case claimed passed')
    if not summary['final_runtime_sha256_matches']:
        raise AssertionError('Shipped runtime changed during case')
    write_json(summary_path, summary)
    return summary


def initialization_matrix(output, hashes):
    """All 64 six-letter appendants, both heads, direct full-2DFT checks."""
    destination = Path(output) / 'initialization-matrix.json'
    if destination.exists():
        value = json.loads(destination.read_text())
        if value.get('runtime_sha256') == hashes:
            return value
    count = 0
    failures = []
    started = perf_counter()
    detector = ReadyDetector()
    for letters in product('YN', repeat=6):
        word = ''.join(letters)
        decoder = Decoder((word,))
        for head in 'YN':
            tape = head + 'YNY'
            row = build_seed(Initialization(tape, (word,)), program_cycles=3,
                             extra_ossifiers=0, padding_cells=2048).row
            ready = detector.observe(row)
            result = decoder.decode(row)
            count += 1
            if not ready.is_ready or result.status != 'decoded' or result.tape != tape or result.appendant_index != 0:
                failures.append({'tape': tape, 'appendants': [word],
                    'ready': ready.is_ready, 'result': result.as_dict()})
                with gzip.open(Path(output)/f'initial-failure-{word}-{head}.json.gz', 'wt') as stream:
                    json.dump({'origin': row.origin, 'time': row.time, 'width': row.width,
                               'bits': row.word()}, stream)
    value = {'status': 'passed' if not failures else 'failed', 'cases': count,
             'distinct_six_letter_appendants': 64, 'initial_heads': ['Y', 'N'],
             'failures': failures, 'elapsed_seconds': perf_counter()-started,
             'runtime_sha256': hashes,
             'execution_driver_sha256': LOADED_DRIVER_SHA256,
             'scope': 'Direct initial-ready configuration decoding; no transition/admissibility claim'}
    write_json(destination, value)
    return value


def compact_result(result):
    """Keep complete bitrows/full events in ignored results, compact outcomes here."""
    keep = ('status', 'reason', 'checked_multisteps', 'native_ticks', 'ready_states',
            'unsupported_events', 'runtime_mismatch_ticks', 'independent_mismatches',
            'ready_c2_phase_counts', 'initial_seed_is_ready', 'elapsed_seconds', 'rows',
            'execution_driver_sha256')
    value = {k: result[k] for k in keep if k in result}
    case = result['case']
    value['case'] = {k: v for k, v in case.items() if k != 'expected'}
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'results/decoder-seeded')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--cases', nargs='*', help='Run selected IDs; omit for the complete campaign')
    parser.add_argument('--max-ticks', type=int, default=8000000)
    parser.add_argument('--skip-initialization-matrix', action='store_true')
    parser.add_argument('--record', action='store_true', help='Write compact versioned summary')
    args = parser.parse_args()
    if args.workers < 1 or args.max_ticks < 1:
        parser.error('--workers and --max-ticks must be positive')
    args.output.mkdir(parents=True, exist_ok=True)
    hashes = runtime_hashes()
    cases, rejected = generate_cases()
    if args.cases:
        selected = set(args.cases)
        unknown = selected - {c['id'] for c in cases}
        if unknown:
            parser.error(f'Unknown cases: {sorted(unknown)}')
        cases = [c for c in cases if c['id'] in selected]
    manifest = {'seed': SEED, 'cases': cases, 'rejected_preflight_candidates': rejected,
                'runtime_sha256': hashes, 'driver_sha256': LOADED_DRIVER_SHA256}
    write_json(args.output/'manifest.json', manifest)
    matrix = None
    if not args.skip_initialization_matrix:
        matrix = initialization_matrix(args.output, hashes)
        print(json.dumps({'initialization_matrix': matrix['status'], 'cases': matrix['cases']}), flush=True)
    outcomes = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(check_case, case, str(args.output), hashes, args.max_ticks): case
                   for case in cases}
        for future in as_completed(futures):
            result = future.result()
            outcomes.append(result)
            print(json.dumps({'case': result['case']['id'], 'status': result['status'],
                'transitions': result.get('checked_multisteps'),
                'ticks': result.get('native_ticks'), 'seconds': result['elapsed_seconds']}), flush=True)
            write_json(args.output/'progress.json', {'completed': len(outcomes), 'total': len(cases),
                'results': [compact_result(r) for r in sorted(outcomes, key=lambda r:r['case']['id'])]})
    outcomes.sort(key=lambda r: r['case']['id'])
    summary = {'campaign': 'Deterministic seeded/adversarial release full-decoder tests',
        'seed': SEED, 'case_count': len(outcomes), 'statuses': dict(Counter(r['status'] for r in outcomes)),
        'checked_multisteps': sum(r.get('checked_multisteps', 0) for r in outcomes),
        'native_ticks': sum(r.get('native_ticks', 0) for r in outcomes),
        'ready_states': sum(r.get('ready_states', 0) for r in outcomes),
        'unsupported_events': sum(r.get('unsupported_events', 0) for r in outcomes),
        'independent_mismatch_count': sum(len(r.get('independent_mismatches', [])) for r in outcomes),
        'rejected_preflight_candidates': rejected,
        'admissibility_scope': 'Independently verified productive, nonhalting finite prefixes only; '
                              'no theorem of admissibility for infinite runs',
        'initialization_matrix': None if matrix is None else {k:v for k,v in matrix.items() if k!='runtime_sha256'},
        'results': [compact_result(r) for r in outcomes],
        'runtime_sha256': hashes, 'driver_sha256': LOADED_DRIVER_SHA256,
        'case_execution_driver_sha256_counts': dict(Counter(
            r.get('execution_driver_sha256', 'not_recorded') for r in outcomes)),
        'initialization_matrix_execution_driver_sha256': (None if matrix is None
            else matrix.get('execution_driver_sha256')),
        'runtime_unchanged': runtime_hashes() == hashes,
        'test_design_refinement': TEST_REFINEMENT,
        'complete': (len(outcomes) == 32 and all(r['status'] == 'passed' for r in outcomes)
            and matrix is not None and matrix['cases'] == 128 and matrix['status'] == 'passed')}
    write_json(args.output/'summary.json', summary)
    if args.record:
        write_json(HERE/'decoder-seeded-summary.json', summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('results','runtime_sha256','initialization_matrix')}), flush=True)
    if any(r['status'] != 'passed' for r in outcomes) or (matrix and matrix['failures']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
