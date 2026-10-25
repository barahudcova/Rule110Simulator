"""Replay saved complete decoder inputs without evolving the CA (stdlib only)."""
from __future__ import annotations

import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))

from pyca_verifier.canonical_decoder import Decoder


def replay(path, *, indices=None, memoize=True):
    """Accept either campaign's JSONL archive; never use its CA clock or origin."""
    decoders, results, seen = {}, [], set()
    requested_total = None
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            record = json.loads(line)
            if record.get('record_type') == 'metadata':
                requested_total = record['case'].get('multisteps')
                continue
            index = record['ready_index']
            if type(index) is not int or index < 0 or index in seen:
                raise ValueError(f'Invalid or duplicate ready index: {index}')
            seen.add(index)
            if indices is not None and index not in indices:
                continue
            bits = record['bits']
            if len(bits) != record['width'] or not bits or set(bits) - {'0', '1'}:
                raise ValueError(f'Invalid binary input at ready index {index}')
            digest = sha256(bits.encode('ascii')).hexdigest()
            expected_digest = record.get('row_sha256', record.get('binary_sha256'))
            if expected_digest is not None and expected_digest != digest:
                raise ValueError(f'Binary hash mismatch at ready index {index}')
            program = tuple(record['appendants'])
            if program not in decoders:
                decoders[program] = Decoder(program)
            actual = decoders[program].decode(bits, memoize_transitions=memoize)
            expected = record['independent_expected']
            matched = (actual.supported and expected is not None
                and actual.tape == expected['tape']
                and actual.appendant_index == expected['appendant_index'])
            results.append({'ready_index': index, 'tick': record['tick'],
                'binary_sha256': digest, 'matched': matched,
                'actual': actual.as_dict(), 'expected': expected})
            print(json.dumps(results[-1]), flush=True)
    found = {item['ready_index'] for item in results}
    missing = sorted(set(indices or ()) - found)
    gaps = sorted(set(range(max(seen) + 1)) - seen) if seen else []
    complete = requested_total is None or len(seen) == requested_total + 1
    summary = {'archive': str(path), 'checked_rows': len(results),
        'mismatches': sum(not item['matched'] for item in results),
        'missing_requested_indices': missing, 'memoize_transitions': memoize,
        'archive_index_gaps': gaps,
        'archive_matches_declared_goal': complete if requested_total is not None else None,
        'status': 'passed' if results and not missing and not gaps and complete and all(
            item['matched'] for item in results) else 'failed',
        'results': results}
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, help='A ready-rows.jsonl.gz from either campaign.')
    parser.add_argument('--ready-index', type=int, nargs='+',
                        help='Replay only these zero-based ready indices; omit for all.')
    parser.add_argument('--no-memoization', action='store_true',
                        help='Validate every interpreter transition without its per-run cache.')
    parser.add_argument('--output', type=Path, help='Also write a JSON receipt.')
    args = parser.parse_args()
    if args.ready_index and any(i < 0 for i in args.ready_index):
        parser.error('--ready-index must be nonnegative')
    result = replay(args.archive, indices=args.ready_index,
                    memoize=not args.no_memoization)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'results'}, indent=2))
    return int(result['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
