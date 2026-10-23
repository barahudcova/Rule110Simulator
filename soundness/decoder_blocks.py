"""Mixed Y/N tests with an elementary invariant proving global admissibility."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from decoder_cts import Case, dump, run_case, runtime_hashes


CASES = (
    (Case('block6-sparse', 'YNNNNY' * 3, ('YNNNNY', '', '', '', '', ''), 24,
          'Every six-letter tape block begins Y, so appendant zero is always productive.'), 0),
    (Case('block6-n-head', 'NNNNNY' * 3, ('NNNNNY', '', '', '', '', 'NNNNNY'), 24,
          'Every six-letter block ends Y; productivity occurs only at offset five.'), 5),
    (Case('block3-unequal', 'YNNYNY' * 3, ('YNNYNY', '', 'YYNYYY' * 2), 24,
          'Three-letter blocks begin Y; mixed six/twelve-letter appendants and an empty.'), 0),
)


def certificate(case, productive_offset):
    """Prove the fixed block invariant from finite input-word checks.

    At every aligned rotation the queue consists of complete z-letter blocks.
    Every block has Y at offset q; alpha_q is nonempty. Thus the qth read
    appends at least z letters, and every appended word preserves the block
    condition. Starting with at least one block prevents halting during the
    rotation; its final length is no smaller than its initial length.
    """
    z, q = len(case.appendants), productive_offset
    words = (case.tape,) + tuple(a for a in case.appendants if a)
    if not (0 <= q < z and case.appendants[q] and len(case.tape) >= z
            and len(case.appendants[q]) >= z
            and all(len(w) % z == 0 and all(w[i+q] == 'Y'
                for i in range(0, len(w), z)) for w in words)):
        raise AssertionError(f'Block-invariant hypotheses fail: {case.name}')
    return {'block_length': z, 'Y_offset': q,
        'productive_appendant_index': q,
        'minimum_letters_appended_per_rotation': len(case.appendants[q]),
        'minimum_net_length_change_per_rotation': len(case.appendants[q])-z,
        'global_nonhalting_and_productivity': True,
        'argument': 'Complete blocks persist at aligned rotation boundaries; '
                    'the designated Y read appends at least one complete block.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'results/decoder-blocks')
    parser.add_argument('--record', action='store_true')
    parser.add_argument('--no-resume', action='store_true')
    args = parser.parse_args()
    hashes = runtime_hashes()
    drivers = {p.name: sha256(p.read_bytes()).hexdigest()
               for p in (Path(__file__), HERE/'decoder_cts.py')}
    results = []
    for case, q in CASES:
        proof = certificate(case, q)
        result = run_case(case, args.output, hashes, resume=not args.no_resume)
        result['global_block_certificate'] = proof
        results.append(result)
    unchanged = runtime_hashes() == hashes and all(
        sha256((HERE/name).read_bytes()).hexdigest() == digest
        for name, digest in drivers.items())
    summary = {'campaign': 'Globally admissible mixed-block decoder tests',
        'cases': len(results), 'requested_multisteps': sum(c.multisteps for c, _ in CASES),
        'checked_multisteps': sum(r['checked_multisteps'] for r in results),
        'ready_rows': sum(r['ready_rows'] for r in results),
        'native_ticks': sum(r.get('native_ticks', 0) for r in results),
        'status': 'passed' if unchanged and all(r['status'] == 'passed' for r in results) else 'failed',
        'runtime_unchanged': unchanged, 'runtime_sha256': hashes,
        'driver_sha256': drivers,
        'results': [{k: v for k, v in r.items() if k not in ('runtime_sha256', 'driver_sha256')}
                    for r in results],
        'scope': 'Global admissibility of inputs is proved; decoding is tested for finite prefixes.'}
    dump(args.output/'summary.json', summary)
    if args.record:
        dump(HERE/'decoder-blocks-summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ('results', 'runtime_sha256')}, indent=2))
    return int(summary['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
