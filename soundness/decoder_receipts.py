"""Check completed native-campaign archives, without rerunning the CA/decoder."""
from __future__ import annotations

import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CAMPAIGNS = (('decoder-cts', 24, 662), ('decoder-seeded', 32, 462),
             ('decoder-blocks', 3, 72))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_archive(path, case):
    """Validate bits, ordering, metadata, and a freshly computed literal queue."""
    tape, rules, goal = case['tape'], tuple(case['appendants']), case['multisteps']
    require(tape and set(tape) <= {'Y', 'N'}, 'Invalid initial tape')
    require(rules and rules[0] and all(len(a) % 6 == 0 and set(a) <= {'Y', 'N'}
                                     for a in rules), 'Invalid appendant syntax')
    index, previous_tick, count, productive = 0, -1, 0, []
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            if row.get('record_type') == 'metadata':
                meta = row['case']
                require(all(meta[k] == case[k] for k in ('tape', 'appendants', 'multisteps')),
                        'Archive header differs from the case descriptor')
                continue
            require(row['ready_index'] == count, 'Missing, duplicated or unordered ready index')
            tick = row['tick']
            require(tick == 0 if count == 0 else tick > previous_tick + 1,
                    'Wrong initial tick or nonseparated ready events')
            require(row['initial_tape'] == case['tape'] and tuple(row['appendants']) == rules,
                    'Ready row belongs to a different input')
            bits = row['bits']
            require(bits and len(bits) == row['width'] and not set(bits) - {'0', '1'},
                    'Invalid binary word or width')
            require(sha256(bits.encode('ascii')).hexdigest() == row.get(
                'binary_sha256', row.get('row_sha256')), 'Binary row hash mismatch')
            wanted = {'tape': tape, 'appendant_index': index}
            require(row['independent_expected'] == wanted, 'Saved expectation is incorrect')
            event = row['event']
            require(event['status'] == 'decoded' and all(event[k] == v for k, v in wanted.items()),
                    'Recorded decoder output differs from independent queue')
            require(event['reference'] == wanted, 'Runner reference differs from independent queue')
            require(event['tick'] == tick, 'Recorded event has the wrong tick')
            for key in ('status', 'tape', 'appendant_index'):
                require(key not in row or row[key] == event[key], 'Duplicate event fields disagree')
            count += 1
            previous_tick = tick
            if count <= goal:
                require(tape, 'Reference halts before the requested horizon')
                append = rules[index] if tape[0] == 'Y' else ''
                productive.append(bool(append))
                tape = tape[1:] + append
                index = (index + 1) % len(rules)
            require(tape, 'Empty reference state within the requested prefix')
    require(count == goal + 1, 'Archive does not contain exactly goal+1 ready rows')
    z = len(rules)
    require(all(any(productive[i:i+z]) for i in range(0, goal-z+1, z)),
            'Unproductive aligned rotation in the tested prefix')
    return {'ready_rows': count, 'transitions': goal, 'last_tick': previous_tick,
            'archive_sha256': sha256(path.read_bytes()).hexdigest()}


def audit(results):
    campaigns = []
    for name, expected_cases, expected_steps in CAMPAIGNS:
        summary_file = HERE / f'{name}-summary.json'
        summary = json.loads(summary_file.read_text())
        cases = summary['results']
        require(len(cases) == expected_cases, f'{name}: incomplete campaign')
        require(sum(r['case']['multisteps'] for r in cases) == expected_steps,
                f'{name}: unexpected goals')
        for relative, digest in summary['runtime_sha256'].items():
            require(sha256((ROOT/relative).read_bytes()).hexdigest() == digest,
                    f'Runtime changed: {relative}')
        checked, seen = [], set()
        for result in cases:
            case = result['case']
            label = case.get('id', case.get('name'))
            require(label and label not in seen, f'{name}: repeated case label')
            seen.add(label)
            require(result['status'] == 'passed', f'{label}: did not pass its goal')
            require(result['checked_multisteps'] == case['multisteps'], f'{label}: wrong goal count')
            record = check_archive(results/name/label/'ready-rows.jsonl.gz', case)
            require(record['last_tick'] == result['native_ticks'], f'{label}: wrong tick total')
            checked.append({'case': label, **record})
        rows = sum(r['ready_rows'] for r in checked)
        ticks = sum(r['last_tick'] for r in checked)
        require(summary['checked_multisteps'] == expected_steps and summary['native_ticks'] == ticks
                and summary.get('ready_rows', summary.get('ready_states')) == rows,
                f'{name}: aggregate counts disagree with archives')
        campaigns.append({'campaign': name, 'cases': len(checked), 'transitions': expected_steps,
            'ready_rows': rows, 'native_ticks': ticks, 'results': checked,
            'summary_sha256': sha256(summary_file.read_bytes()).hexdigest()})
    return {'status': 'passed', 'CA_or_decoder_reexecuted': False,
        'scope': 'Archive integrity and independent reference verification; not a second native run.',
        'cases': sum(c['cases'] for c in campaigns),
        'transitions': sum(c['transitions'] for c in campaigns),
        'ready_rows': sum(c['ready_rows'] for c in campaigns),
        'native_ticks': sum(c['native_ticks'] for c in campaigns), 'campaigns': campaigns,
        'driver_sha256': sha256(Path(__file__).read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=HERE/'results')
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    result = audit(args.results)
    destination = args.results/'decoder-archive-integrity.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2)+'\n')
    if args.record:
        (HERE/'decoder-archive-integrity.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'campaigns'}, indent=2))


if __name__ == '__main__':
    main()
