"""Replay the physical A4/static-Y collision in the excluded NYYY pilot.

The default is a small isolated collision, independent of every decoder and
CTS reference. --archive additionally verifies its exact causal input patch
against the preserved native ready-row checkpoints (no new global CA run).
"""
from __future__ import annotations

import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from pyca_verifier.automaton import BitRow, step
from pyca_verifier.patterns import ETHER, word
from pyca_verifier.ready import C2_OFFSETS

PAIR_TICK, A4_X, Y_X = 209633, 224714, 225018
BAND, HORIZON = (224980, 225200), 500
FINAL_BAND = (224700, 225500)


def digest(text):
    return sha256(text.encode('ascii')).hexdigest()


def runtime_hashes():
    paths = sorted((ROOT/'pyca_verifier').rglob('*.py'))
    paths += sorted((ROOT/'pyca_verifier/data').glob('*.json'))
    return {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in paths}


def cut(row, left, right):
    if not row.origin <= left < right <= row.origin+row.width:
        raise AssertionError('Requested causal crop lies outside the known row')
    value = (row.value >> (left-row.origin)) & ((1 << (right-left))-1)
    return format(value, f'0{right-left}b')[::-1]


def particles(row, family, phases, band=BAND):
    text = cut(row, *band)
    found = []
    for phase in phases:
        needle = ETHER+word(family, phase)+ETHER
        at = text.find(needle)
        while at >= 0:
            x = band[0]+at+len(ETHER)
            hit = {'x': x, 'phase': phase}
            if family == 'C2':
                hit['anchor'] = x-C2_OFFSETS[phase]
            found.append(hit)
            at = text.find(needle, at+1)
    return sorted(found, key=lambda hit: (hit['x'], hit['phase']))


def isolated_seed():
    core = word('A4', 2)+ETHER*21+word('Y', 2)
    return BitRow.from_word(ETHER*150+core+ETHER*150, origin=A4_X-2100)


def isolated_test():
    row, first_loss, snapshots = isolated_seed(), None, []
    for dt in range(1501):
        if not particles(row, 'Y', range(7)) and first_loss is None:
            first_loss = dt
        if dt in (0, 420, 434, 500, 1500):
            snapshots.append({'relative_tick': dt, 'mapped_native_tick': PAIR_TICK+dt,
                'C2': particles(row, 'C2', range(7)),
                'intact_Y': particles(row, 'Y', range(7))})
        if dt < 1500:
            row = step(row)
    if first_loss != 428 or {h['anchor'] for h in snapshots[-1]['C2']} != {225114, 225151}:
        raise AssertionError('Isolated collision differs from the recorded physical diagnosis')
    return {'seed': 'A4[2] ETHER^21 Y[2], with150 ether tiles on each side',
        'A4_core_x': A4_X, 'Y_core_x': Y_X, 'ether_gap_tiles': 21,
        'pair_core_sha256': digest(word('A4', 2)+ETHER*21+word('Y', 2)),
        'simulated_ticks': 1500, 'observed_interval': list(BAND),
        'first_tick_without_intact_Y': first_loss,
        'mapped_first_native_tick_without_intact_Y': PAIR_TICK+first_loss,
        'snapshots': snapshots}


def checkpoint_test(archive):
    records = {}
    with gzip.open(archive, 'rt') as stream:
        for line in stream:
            record = json.loads(line)
            if record.get('ready_index') in (11, 12):
                records[record['ready_index']] = record
    old, new = records[11], records[12]
    if (old['tick'], new['tick']) != (207596, 225582):
        raise AssertionError('Unexpected checkpoints')
    for record in (old, new):
        expected = record.get('binary_sha256', record.get('row_sha256'))
        if len(record['bits']) != record['width'] or digest(record['bits']) != expected:
            raise AssertionError('Checkpoint width/hash mismatch')
    total = new['tick']-old['tick']
    left, right = FINAL_BAND[0]-total, FINAL_BAND[1]+total
    text = old['bits'][left-old['origin']:right-old['origin']]
    row = BitRow(int(text[::-1], 2), len(text), left, old['tick'])
    pair_check = None
    for dt in range(total+1):
        if row.time == PAIR_TICK:
            pair = isolated_seed()
            causal = (BAND[0]-HORIZON, BAND[1]+HORIZON)
            actual, expected = cut(row, *causal), cut(pair, *causal)
            exact_word = ETHER+word('A4', 2)+ETHER*21+word('Y', 2)+ETHER
            if actual != expected or cut(row, A4_X-14, Y_X+len(word('Y', 2))+14) != exact_word:
                raise AssertionError('Actual causal input is not the isolated A4/Y pair')
            pair_check = {'native_tick': PAIR_TICK, 'causal_input_interval': list(causal),
                'causal_input_sha256': digest(actual),
                'actual_equals_isolated_seed_on_complete_input_cone': True,
                'forced_output_interval': list(BAND), 'forced_output_horizon': HORIZON,
                'reason': 'Rule110 has radius one, so these input cells determine the stated output band.'}
        if dt < total:
            row = step(row)
    actual = cut(row, *FINAL_BAND)
    expected = new['bits'][FINAL_BAND[0]-new['origin']:FINAL_BAND[1]-new['origin']]
    if actual != expected or pair_check is None:
        raise AssertionError('Checkpoint replay does not match the saved final local row')
    return {'archive_sha256': sha256(archive.read_bytes()).hexdigest(),
        'source_rows': [{'ready_index': r['ready_index'], 'tick': r['tick'],
            'origin': r['origin'], 'width': r['width'], 'binary_sha256': digest(r['bits'])}
            for r in (old, new)],
        'checkpoint_replay_ticks': total, 'initial_known_interval': [left, right],
        'initial_crop_sha256': digest(text), 'final_verified_interval': list(FINAL_BAND),
        'final_crop_sha256': digest(actual), 'final_saved_row_exactly_matches': True,
        'isolated_pair_causal_witness': pair_check}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Preserved outside-domain pilot ready-rows.jsonl.gz.')
    parser.add_argument('--output', type=Path, default=HERE/'results/decoder-database/excluded-collision.json')
    parser.add_argument('--record', action='store_true', help='Update the compact versioned diagnostic receipt.')
    args = parser.parse_args()
    before = runtime_hashes()
    result = {'classification': 'Physical corruption of a staticY by an incoming A4; excluded input',
        'isolated_collision': isolated_test(),
        'checkpoint_confirmation': checkpoint_test(args.archive) if args.archive else None,
        'runtime_sha256': before, 'driver_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope': 'Proves this bounded unsafe A4/static encounter; does not prove which global scheduling '
                 'choice caused it, or decoder correctness outside its valid representation domain.'}
    result['runtime_unchanged'] = before == runtime_hashes()
    if not result['runtime_unchanged']:
        raise AssertionError('Runtime changed during diagnosis')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    if args.record:
        (HERE/'decoder-excluded-collision.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'runtime_sha256'}, indent=2))


if __name__ == '__main__':
    main()
