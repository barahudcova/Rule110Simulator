#!/usr/bin/env python3
"""Structured end-to-end tests of the shipped Rule 110 decoder.

Run from any directory: python supplementary/decoder_cts.py [--record].
Every observed ready row is saved, including successes, for direct replay.
The independent reference below is deliberately not pyca_verifier.cts.
It supplies no data to the decoder, ready matcher, or CA transition.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, asdict
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pyca_verifier.encoder import Initialization
from pyca_verifier.runner import run_multisteps


@dataclass(frozen=True)
class Case:
    name: str
    tape: str
    appendants: tuple[str, ...]
    multisteps: int
    purpose: str


CASES = (
    Case('two-empty', 'YYY', ('YYYYYY', '', ''), 36,
         'Historical unknown-window case; two consecutive empty appendants.'),
    Case('three-empty', 'YYYY', ('YYYYYY', '', '', ''), 28,
         'Primary short leader followed by two secondary short leaders.'),
    Case('five-empty', 'YYYYYYYY', ('YYYYYY', '', '', '', '', ''), 30,
         'Long run of secondary short leaders and repeated cycle markers.'),
    Case('repeated-twelve-historical', 'YNNNNYYNNNNYYNNNNY',
         ('YNNNNYYNNNNY',) * 3, 40,
         'Historical twelve-letter regression, beyond both earlier failures.'),
    Case('identical-two', 'YY', ('YYYYYY',) * 2, 24,
         'Equal appendants require an absolute pointer from the marker.'),
    Case('identical-three', 'YYY', ('YYYYYY',) * 3, 24,
         'Three indistinguishable program words with distinct pointers.'),
    Case('one-appendant-growth', 'YY', ('YYYYYY',), 24,
         'Every read productive; rapid growth and densely emitted Y packets.'),
    Case('long-horizon-empty', 'Y' * 64, ('YYYYYY',) + ('',) * 7, 64,
         'Eight appendants and sixty-four transitions; low production rate.'),
    Case('long-horizon-mixed', 'Y' * 72,
         ('YNNNNY', '', '', '', '', ''), 60,
         'Long prefix with low Y density and repeated short-leader transitions.'),
    Case('unequal-6-12-18', 'Y' * 18,
         ('YNYYNY', 'YNNNNYYNNNNY', 'YNYNNY' * 3), 24,
         'Unequal six/twelve/eighteen-letter packet trains.'),
    Case('unequal-6-24-empty', 'Y' * 16,
         ('YNNNNY', '', 'YNNNNY' * 4, ''), 12,
         'Long twenty-four-letter train bracketed by empty appendants.'),
    Case('unequal-24-6', 'Y' * 24,
         ('YNNNNY' * 4, 'YNYYNY'), 12,
         'Long first train followed by a much shorter train.'),
    Case('n-head-immediate-next', 'N' + 'Y' * 20,
         ('YYYYYY', 'YNNNNY', ''), 24,
         'N-headed initialization and a productive second read.'),
    Case('n-head-late-productive', 'NNNNNY' + 'Y' * 24,
         ('YNYYNY', '', 'YYYYYY', '', 'YNNNNY', 'YNYNYN'), 24,
         'Five leading N symbols; first productivity only at read five.'),
    Case('n-head-seven-late', 'N' * 7 + 'Y' * 32,
         ('YYYYYY',) + ('',) * 6 + ('YNNNNY',), 24,
         'First productivity at the last appendant of an eight-appendant cycle.'),
    Case('all-n-payload', 'Y' * 40,
         ('NNNNNN', 'NNNNNN' * 2, ''), 24,
         'All appended symbols N; productivity is established only for the prefix.'),
    Case('all-n-and-y', 'Y' * 28,
         ('NNNNNN', 'YYYYYY', '', 'YNNNNY'), 24,
         'N-only trains interleaved with Y-only trains and an empty appendant.'),
    Case('alternating-payload', 'Y' * 20,
         ('YNYNYN', 'NYNYNY', '', ''), 28,
         'Alternating packet values, both leader variants and pointer wraparound.'),
    Case('all-y-long-empty', 'Y' * 16,
         ('YYYYYY' * 3, '', '', 'YYYYYY', ''), 12,
         'High growth followed by consecutive empty appendants.'),
    Case('tail-y-packets', 'Y' * 24,
         ('NNNNNY', 'NNNNNY' * 2, ''), 24,
         'Y at the end of each six-letter block; frontier and packet boundaries.'),
    Case('head-y-packets', 'Y' * 24,
         ('YNNNNN', '', 'YNNNNN' * 2), 24,
         'Y at the start of each six-letter block.'),
    Case('alternating-initial', 'YN' * 18,
         ('YYYYYY', 'NNNNNN', 'YNNNNY', ''), 24,
         'Alternating initial stationary data with mixed appendant values.'),
    Case('six-letter-historical-extended', 'NYY' + 'Y' * 24,
         ('YNYYNY', '', 'YNNNNY', ''), 24,
         'Original visualization program with extra initial Y for a productive prefix.'),
    Case('empty-across-cycle-boundary', 'Y' * 20,
         ('YYYYYY', '', '', 'YNNNNY', '', '', ''), 28,
         'Long final empty run followed by the next cycle-marker raw leader.'),
)


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def runtime_hashes():
    files = sorted((ROOT / 'pyca_verifier').rglob('*.py'))
    files += sorted((ROOT / 'pyca_verifier' / 'data').glob('*.json'))
    return {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in files}


def reference_prefix(case):
    """Literal queue algorithm, independent of the runtime CTSState class.

    A productive read removes Y and appends a nonempty appendant. The
    admissibility check is on aligned complete z-step rotations, not every
    sliding z-step interval. The last incomplete rotation is reported too.
    """
    queue, index = list(case.tape), 0
    states, productive, halted = [], [], None
    for step in range(case.multisteps + 1):
        states.append({'tape': ''.join(queue), 'appendant_index': index})
        if step == case.multisteps:
            break
        if not queue:
            halted = step
            break
        symbol = queue.pop(0)
        produced = list(case.appendants[index]) if symbol == 'Y' else []
        productive.append(bool(produced))
        queue.extend(produced)
        index = (index + 1) % len(case.appendants)
    z = len(case.appendants)
    complete = [productive[start:start + z]
                for start in range(0, len(productive) - z + 1, z)]
    tail = productive[len(complete) * z:]
    all_y_forever = (set(case.tape) == {'Y'}
        and all(set(a) <= {'Y'} for a in case.appendants)
        and len(case.tape) >= z and sum(map(len, case.appendants)) >= z)
    return states, {
        'alphabet_and_length_constraints': all(len(a) % 6 == 0 for a in case.appendants),
        'nonempty_at_every_requested_ready_state': len(states) == case.multisteps + 1
            and all(s['tape'] for s in states),
        'productive_complete_aligned_rotations': sum(any(r) for r in complete),
        'complete_aligned_rotations': len(complete),
        'unproductive_complete_aligned_rotations': [i for i, r in enumerate(complete) if not any(r)],
        'incomplete_final_rotation_reads': len(tail),
        'incomplete_final_rotation_productive': any(tail),
        'first_productive_step': next((i for i, p in enumerate(productive) if p), None),
        'productive_reads': sum(productive),
        'halted_before_requested_step': halted,
        'global_admissibility_proved_for_all_y_family': all_y_forever,
        'global_family_argument': ('All symbols remain Y; every rotation produces data and '
            'its net length change is nonnegative, so no halt or unproductive rotation occurs.'
            if all_y_forever else None),
        'scope': 'Exact requested prefix only; no whole-trajectory admissibility claim.'}


def run_case(case, output, hashes, *, resume):
    destination = output / case.name
    destination.mkdir(parents=True, exist_ok=True)
    receipt = destination / 'result.json'
    specification = asdict(case)
    specification['appendants'] = list(case.appendants)
    old = json.loads(receipt.read_text()) if receipt.exists() else None
    driver = sha256(Path(__file__).read_bytes()).hexdigest()
    if (resume and old and old.get('case') == specification
            and old.get('runtime_sha256') == hashes and old.get('driver_sha256') == driver):
        print(f"{case.name}: reused {old['status']}, {old['checked_multisteps']} transitions", flush=True)
        return old
    expected, admissibility = reference_prefix(case)
    if (admissibility['unproductive_complete_aligned_rotations']
            or not admissibility['nonempty_at_every_requested_ready_state']):
        raise ValueError(f'{case.name}: requested prefix is outside the campaign productivity condition')
    records, problems = [], []
    started = perf_counter()
    print(f'{case.name}: starting {case.multisteps} transitions', flush=True)
    with gzip.open(destination / 'ready-rows.jsonl.gz', 'wt') as archive:
        archive.write(json.dumps({'record_type': 'metadata', 'case': specification,
            'runtime_sha256': hashes, 'format_version': 1}) + '\n')

        def on_ready(row, event):
            ordinal = len(records)
            wanted = expected[ordinal] if ordinal < len(expected) else None
            supported = event['status'] == 'decoded'
            tape_ok = supported and wanted is not None and event['tape'] == wanted['tape']
            pointer_ok = supported and wanted is not None and event['appendant_index'] == wanted['appendant_index']
            runner_reference_ok = wanted is not None and event['reference'] == wanted
            observation = {'ready_index': ordinal, 'tick': row.time,
                'status': event['status'], 'reason': event['reason'],
                'tape': event['tape'], 'appendant_index': event['appendant_index'],
                'expected': wanted, 'tape_matches_independent_reference': tape_ok,
                'pointer_matches_independent_reference': pointer_ok,
                'runner_reference_matches_independent_reference': runner_reference_ok,
                'row_sha256': sha256(row.word().encode('ascii')).hexdigest(),
                'width': row.width, 'origin': row.origin}
            records.append(observation)
            record = {'record_type': 'ready_row', **observation, 'bits': row.word(),
                      'initial_tape': case.tape, 'appendants': list(case.appendants),
                      'case_name': case.name, 'independent_expected': wanted,
                      'event': event}
            archive.write(json.dumps(record, separators=(',', ':')) + '\n')
            archive.flush()
            if not (tape_ok and pointer_ok and runner_reference_ok):
                problems.append(observation)
                dump(destination / f'failure-{row.time}.json', observation)
                print('FAILURE ' + json.dumps({'case': case.name, **observation}), flush=True)

        try:
            report = run_multisteps(Initialization(case.tape, case.appendants),
                                   multisteps=case.multisteps, on_ready=on_ready)
            snapshot = report.pop('failure_snapshot', None)
            if snapshot is not None:
                with gzip.open(destination / f"failure-{snapshot['time']}.json.gz", 'wt') as f:
                    json.dump(snapshot, f, separators=(',', ':'))
                report['failure_snapshot'] = {k: snapshot[k] for k in ('origin', 'time', 'width')}
            dump(destination / 'report.json', report)
            goal = report['verification_goal']
            status = goal['status'] if not problems else 'failed'
            result = {'case': specification, 'status': status,
                'reason': goal['reason'], 'checked_multisteps': goal['checked_multisteps'],
                'ready_rows': len(records), 'native_ticks': report['evolution']['native_ticks'],
                'initial_seed_is_ready': report['initial_seed_is_ready'],
                'independent_mismatches': len(problems),
                'unsupported_ready_rows': report['decoder']['unsupported_events'],
                'runtime_mismatch_ticks': report['decoder']['mismatch_ticks'],
                'multiple_match_ticks': len(report['readiness']['ambiguous_ticks']),
                'consecutive_ready_ticks': len(report['readiness']['consecutive_ready_ticks']),
                'ready_phase_counts': {str(p): sum(e['c2_phase'] == p for e in report['readiness']['events'])
                                       for p in (1, 2, 5, 6)},
                'maximum_row_width': max((r['width'] for r in records), default=0),
                'problems': problems, 'prefix_admissibility': admissibility,
                'runtime_sha256': hashes, 'driver_sha256': driver,
                'elapsed_seconds': perf_counter() - started,
                'replay_file': 'ready-rows.jsonl.gz'}
        except Exception as exc:
            result = {'case': specification, 'status': 'exception',
                'reason': f'{type(exc).__name__}: {exc}', 'checked_multisteps': 0,
                'ready_rows': len(records), 'problems': problems,
                'prefix_admissibility': admissibility, 'runtime_sha256': hashes,
                'driver_sha256': driver, 'elapsed_seconds': perf_counter() - started}
            print(f"EXCEPTION {case.name}: {result['reason']}", flush=True)
    with (destination / 'decoded.csv').open('w', newline='') as f:
        fields = ('ready_index', 'tick', 'status', 'reason', 'tape', 'appendant_index',
                  'tape_matches_independent_reference', 'pointer_matches_independent_reference',
                  'runner_reference_matches_independent_reference', 'row_sha256')
        writer = csv.DictWriter(f, fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)
    dump(receipt, result)
    print(f"{case.name}: {result['status']}, {result['checked_multisteps']}/{case.multisteps} transitions, "
          f"{result.get('native_ticks', 0):,} ticks, {result['elapsed_seconds']:.1f}s", flush=True)
    return result


def replay(path):
    from pyca_verifier.automaton import BitRow
    from pyca_verifier.canonical_decoder import Decoder
    checked, failures = 0, []
    with gzip.open(path, 'rt') as f:
        meta = json.loads(next(f))
        decoder = Decoder(tuple(meta['case']['appendants']))
        for line in f:
            item = json.loads(line)
            row = BitRow(int(item['bits'][::-1], 2), item['width'], item['origin'], item['tick'])
            result = decoder.decode(row)
            wanted = item['expected']
            if not (result.status == 'decoded' and result.tape == wanted['tape']
                    and result.appendant_index == wanted['appendant_index']):
                failures.append({'ready_index': item['ready_index'], 'tick': item['tick'],
                                 'actual': result.as_dict(), 'expected': wanted})
            checked += 1
    summary = {'rows': checked, 'failures': failures}
    print(json.dumps(summary, indent=2))
    return bool(failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', nargs='+', choices=[c.name for c in CASES],
                        help='Omit to run all structured cases.')
    parser.add_argument('--output', type=Path, default=ROOT / 'supplementary/results/decoder-cts')
    parser.add_argument('--record', action='store_true', help='Update the versioned compact summary.')
    parser.add_argument('--no-resume', action='store_true', help='Recompute even unchanged completed cases.')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--replay', type=Path, help='Decode every complete row in one ready-rows.jsonl.gz.')
    args = parser.parse_args()
    if args.replay:
        return replay(args.replay)
    if args.list:
        print(json.dumps([asdict(c) for c in CASES], indent=2))
        return 0
    cases = [c for c in CASES if args.cases is None or c.name in args.cases]
    hashes, results = runtime_hashes(), []
    for case in cases:
        result = run_case(case, args.output, hashes, resume=not args.no_resume)
        results.append(result)
        # Persist completed results after every case, including any failure.
        dump(args.output / 'progress.json', {'completed_cases': results})
    unchanged = runtime_hashes() == hashes
    phases = {str(p): sum(r.get('ready_phase_counts', {}).get(str(p), 0) for r in results)
              for p in (1, 2, 5, 6)}
    summary = {'format_version': 1, 'campaign': 'Structured CTS decoder campaign',
        'cases': len(results), 'requested_multisteps': sum(c.multisteps for c in cases),
        'checked_multisteps': sum(r['checked_multisteps'] for r in results),
        'ready_rows': sum(r['ready_rows'] for r in results),
        'native_ticks': sum(r.get('native_ticks', 0) for r in results),
        'case_status_counts': {s: sum(r['status'] == s for r in results)
                               for s in ('passed', 'failed', 'inconclusive', 'exception')},
        'independent_mismatches': sum(r.get('independent_mismatches', 0) for r in results),
        'unsupported_ready_rows': sum(r.get('unsupported_ready_rows', 0) for r in results),
        'multiple_match_ticks': sum(r.get('multiple_match_ticks', 0) for r in results),
        'consecutive_ready_ticks': sum(r.get('consecutive_ready_ticks', 0) for r in results),
        'ready_phase_counts': phases, 'runtime_unchanged_during_run': unchanged,
        'runtime_sha256': hashes, 'driver_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'results': [{k: v for k, v in r.items() if k not in ('runtime_sha256', 'driver_sha256')}
                    for r in results],
        'scope': 'Finite trials on the exact requested prefixes; no proof of decoder completeness.'}
    dump(args.output / 'summary.json', summary)
    if args.record:
        dump(ROOT / 'supplementary/decoder-cts-summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('runtime_sha256', 'results')}, indent=2))
    return int(not unchanged or any(r['status'] != 'passed' for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
