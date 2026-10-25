"""Audit the shipped content reader against an external native collision DB.

The exhaustive pass is a literal-vocabulary/ownership diagnostic, not execution
of the 2DFT on eight million frames. A separate deterministic selection runs the
actual unchanged LocalContentTransducer. Input labels come from source roles,
never from a CTS trajectory or the decoder's own output. Full decoder control
(ready language, pointer and finite-observation boundaries) is tested by the
cyclic-tag campaign, because isolated collision rows lack those structures.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys
from time import perf_counter
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from pyca_verifier.canonical_content_patterns import CanonicalHit, canonicalize_symbols
from pyca_verifier.canonical_ossification import canonicalize_frontiers, suppress_converting_symbols
from pyca_verifier.local_content_transducer import LocalContentTransducer
from pyca_verifier.patterns import ETHER, word


def file_hash(path):
    digest = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_hashes():
    names = ('local_content_transducer.py', 'canonical_content_patterns.py',
             'canonical_ossification.py', 'literal_matcher.py', 'transducer.py',
             'static_crossing_patterns.py', 'moving_crossing_patterns.py',
             'ossification_patterns.py', 'data/static_crossing_patterns.json',
             'data/moving_crossing_patterns.json', 'data/ossification_patterns.json')
    paths = [Path(__file__).resolve()] + [ROOT/'pyca_verifier'/n for n in names]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def unpack(blob, width):
    raw = zlib.decompress(blob)
    value = int.from_bytes(raw, 'little')
    if len(raw) != (width+7)//8 or value.bit_length() > width:
        raise AssertionError('Invalid packed row')
    return format(value, f'0{width}b')[::-1]


def contract(source):
    """An independent participant contract for a whole-content experiment."""
    f, p = source['family'], source['details'].get('parameters', {})
    if f.startswith('static-moving:'):
        return ('exact', p['static_symbol'], f[-1])
    if f.startswith('static-garbage:'):
        return ('exact', p['static_symbol'], '')
    if f == 'whole-static-E':
        return ('exact', p['symbol'], '')
    if f.startswith(('O-moving:', 'O-garbage-moving:')):
        return ('conversion', p.get('moving_symbol', p.get('symbol')), '')
    if f in ('v4-productive-garbage-prefixes', 'v4-short-train-conversion'):
        return ('conversion', p['symbol'], '')
    if f in ('free:Y', 'free:N'):
        return ('exact', f[-1], '')
    if f.startswith(('O-garbage:', 'A4-garbage:')) or f == 'O-two-garbage-pairs':
        return ('exact', '', '')
    # These are useful no-false-output controls. Their complete rows are not
    # necessarily in the content-word domain of a legal finite observation.
    # In particular a consuming leader's interior is not content to decode.
    if f.startswith(('ordinary-read-', 'short-read-')):
        return ('read_control', p['symbol'], '')
    return ('epsilon_control', '', '')


def errors_for(result, expected, *, tick=None, horizon=None):
    mode, symbol, moving = expected
    static, actual_moving = ''.join(result['static']), ''.join(result['moving'])
    if result['status'] != 'decoded':
        return [result.get('reason') or result['status']]
    if mode == 'exact':
        return [] if (static, actual_moving) == (symbol, moving) else ['wrong_semantic_output']
    if mode == 'conversion':
        return [] if static+actual_moving == symbol else ['conversion_not_exactly_once']
    if mode == 'read_control':
        if actual_moving or static not in ('', symbol):
            return ['unexpected_read_interior_output']
        if tick is not None and tick == 0 and static != symbol:
            return ['wrong_read_initial_output']
        if tick is not None and horizon is not None and tick == horizon and static:
            return ['wrong_read_final_output']
        return []
    return [] if not static and not actual_moving else ['noncontent_control_output']


def diagnostic(bits, machine):
    """Whole-row diagnostic using exactly the fixed runtime vocabulary.

    Unlike the production 2DFT, this diagnostic collects unbounded absolute
    coordinates. It independently sorts designated anchors and applies the
    same finite alias/conversion definitions and moving-core ownership rule.
    Agreement is tested on a separate selection; this pass alone is not a
    claim that every 2DFT transition has been executed.
    """
    tail = warm = 0
    hits = []
    matcher = machine.forward_matcher
    for end, digit in enumerate(bits, 1):
        tail, warm, indices = matcher.advance(tail, warm, int(digit))
        for i in indices:
            p = machine.primitives[i]
            start = end-len(p.bits)
            hits.append(CanonicalHit(p.kind, p.symbol, start, end,
                start+p.offset, start+p.offset+p.cells, start+p.anchor_offset))
    symbols, e1 = canonicalize_symbols(hits)
    frontiers, e2 = canonicalize_frontiers(hits)
    symbols, e3 = suppress_converting_symbols(frontiers, symbols)
    errors = tuple(e1)+tuple(e2)+tuple(e3)
    static = tuple(h.symbol for h in sorted(
        [h for h in symbols if h.kind == 'static']+list(frontiers),
        key=lambda h: h.anchor, reverse=True))
    moving, owned = [], None
    for hit in sorted([h for h in symbols if h.kind == 'moving']+list(frontiers),
                      key=lambda h: h.anchor):
        if hit.kind == 'frontier':
            owned = hit.hi if owned is None else max(owned, hit.hi)
        elif owned is None or hit.lo >= owned:
            moving.append(hit.symbol)
            owned = hit.hi
    return dict(status='unrecognized' if errors else 'decoded', static=static,
                moving=tuple(moving), reason='; '.join(errors) if errors else None)


def machine_result(machine, bits):
    r = machine.decode(bits)
    return dict(status=r.status, static=list(r.static), moving=list(r.moving), reason=r.reason)


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')


def scan(database, output, machine_phases=30):
    started = perf_counter()
    hashes = runtime_hashes()
    machine = LocalContentTransducer()
    db = sqlite3.connect(database.resolve().as_uri()+'?mode=ro', uri=True)
    db.execute('PRAGMA query_only=ON')
    metadata = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
    if metadata.get('schema') != 1 or not metadata.get('build_complete'):
        raise AssertionError('Unsupported or incomplete database')
    guard = metadata['frame_guard_cells']
    max_side_context = max(max(p.offset, len(p.bits)-p.offset-p.cells)
                           for p in machine.primitives)
    # A literal cannot span a cut placed in this much undisturbed ether;
    # pure ether has no semantic primitive (checked below). The diagnostic
    # may omit the outer 1900 ether cells. Actual machine runs use full rows.
    keep = max(148, max_side_context+14)
    trim = max(0, guard-keep)
    longest = max(len(p.bits) for p in machine.primitives)
    for rotation in range(14):
        tile = ETHER[rotation:]+ETHER[:rotation]
        ether = (tile*((longest+27)//14))[:longest+14]
        if any(p.bits in ether for p in machine.primitives):
            raise AssertionError('Semantic primitive appears in pure ether')
    sources = {}
    family_totals = defaultdict(Counter)
    contracts = defaultdict(dict)
    machine_cases = {}
    endpoint_checks, endpoint_failures = 0, []
    for sid, family, horizon, details in db.execute(
            'SELECT id,family,ticks,details_json FROM sources ORDER BY id'):
        source = dict(id=sid, family=family, ticks=horizon, details=json.loads(details))
        source['contract'] = contract(source)
        sources[sid] = source
        family_totals[family]['sources'] += 1
        rows = list(db.execute('SELECT pattern_id,min(tick),max(tick),count(*) FROM frames '
                              'WHERE source_id=? GROUP BY pattern_id', (sid,)))
        for pid, first, last, count in rows:
            key = source['contract']
            witness = dict(source_id=sid, family=family, tick=first,
                           last_tick=last, source_horizon=horizon)
            entry = contracts[pid].setdefault(key, dict(frames=0, witness=witness))
            entry['frames'] += count
            family_totals[family]['represented_frames'] += count
        # Every source has its endpoints tested by the diagnostic. Endpoint
        # literal identity is checked independently where a symbol survives.
        mode, symbol, _ = source['contract']
        if mode in ('exact', 'conversion') and symbol:
            for tick in (0, horizon):
                if mode == 'conversion' and tick == 0:
                    continue  # moving exact word is a separate vocabulary.
                row = db.execute('SELECT p.cells,p.packed_zlib FROM frames f '
                                 'JOIN patterns p ON p.id=f.pattern_id '
                                 'WHERE source_id=? AND tick=?', (sid, tick)).fetchone()
                text = unpack(row[1], row[0])
                n = sum(text.count(ETHER+word(symbol, p)+ETHER) for p in range(7))
                endpoint_checks += 1
                if n != 1:
                    endpoint_failures.append(dict(source_id=sid, tick=tick,
                                                  expected_symbol=symbol, literal_matches=n))
        # Select one actual source row per family and native tick residue,
        # including endpoints and intermediate phases spread across horizon.
        selected = {0, horizon, horizon//2}
        selected.update((horizon//2//machine_phases)*machine_phases+r
                        for r in range(machine_phases))
        for tick in sorted(t for t in selected if t <= horizon):
            pid = db.execute('SELECT pattern_id FROM frames WHERE source_id=? AND tick=?',
                             (sid, tick)).fetchone()[0]
            key = family, tick % machine_phases
            score = sha256((sid+':'+str(tick)).encode()).digest()
            if key not in machine_cases or score < machine_cases[key]['score']:
                machine_cases[key] = dict(source_id=sid, family=family, tick=tick,
                                          pattern_id=pid, score=score)
    output.mkdir(parents=True, exist_ok=True)
    diagnostic_failures, control_outputs, results = [], [], {}
    positive_controls = defaultdict(Counter)
    machine_witnesses = {case['pattern_id']: {k: v for k, v in case.items() if k != 'score'}
                         for case in machine_cases.values()}
    full_crop_checks = 0
    for index, (pid, width, digest, blob) in enumerate(db.execute(
            'SELECT id,cells,sha256,packed_zlib FROM patterns ORDER BY id'), 1):
        full = unpack(blob, width)
        text = full[trim:-trim] if trim else full
        result = diagnostic(text, machine)
        results[pid] = result
        if pid in machine_witnesses:
            # No locality assumption substitutes for this comparison.
            full_result = diagnostic(full, machine)
            if result != full_result:
                raise AssertionError(('Diagnostic ether crop changed result', pid))
            full_crop_checks += 1
        for expected, assignment in contracts[pid].items():
            witness = assignment['witness']
            if expected[0] in ('read_control', 'epsilon_control') and (result['static'] or result['moving']):
                positive_controls[expected[0]]['pattern_contract_pairs'] += 1
                positive_controls[expected[0]]['represented_frames'] += assignment['frames']
                positive_controls[expected[0]]['static_outputs'] += len(result['static'])
                positive_controls[expected[0]]['moving_outputs'] += len(result['moving'])
            errors = errors_for(result, expected)
            if not errors:
                continue
            record = dict(pattern_id=pid, pattern_sha256=digest, cells=width,
                contract=expected, result=result, errors=errors,
                represented_frames=assignment['frames'], **witness)
            if expected[0] in ('read_control', 'epsilon_control'):
                control_outputs.append(record)
            else:
                diagnostic_failures.append(record)
                machine_witnesses.setdefault(pid, witness | {'pattern_id': pid})
        if index % 5000 == 0:
            print(json.dumps(dict(stage='literal-vocabulary diagnostic',
                distinct_patterns=index, semantic_mismatches=len(diagnostic_failures),
                control_outputs=len(control_outputs),
                elapsed_seconds=round(perf_counter()-started, 1))), flush=True)
    write_json(output/'diagnostic-semantic-mismatches.json', diagnostic_failures)
    write_json(output/'diagnostic-noncontent-controls.json', control_outputs)
    # Full unchanged finite-state execution, including exact source replay on
    # every diagnostic semantic mismatch. Results are cached by pattern hash.
    cache_path = output/'machine-cache.json'
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    identity = sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    if cache.get('runtime_identity') != identity:
        cache = dict(runtime_identity=identity, results={})
    machine_disagreements, semantic_machine_failures, machine_control_outputs = [], [], []
    machine_family_counts = Counter()
    for index, (pid, witness) in enumerate(sorted(machine_witnesses.items()), 1):
        width, digest, blob = db.execute(
            'SELECT cells,sha256,packed_zlib FROM patterns WHERE id=?', (pid,)).fetchone()
        full = unpack(blob, width)
        key = digest
        if key not in cache['results']:
            cache['results'][key] = machine_result(machine, full)
        actual = cache['results'][key]
        expected_diag = json.loads(json.dumps(results[pid]))
        if actual != expected_diag:
            machine_disagreements.append(dict(pattern_id=pid, actual=actual,
                                              diagnostic=expected_diag, **witness))
        source = sources[witness['source_id']]
        errors = errors_for(actual, source['contract'], tick=witness['tick'], horizon=source['ticks'])
        if errors and source['contract'][0] not in ('read_control', 'epsilon_control'):
            failure = dict(pattern_id=pid, pattern_sha256=digest, actual=actual,
                contract=source['contract'], errors=errors, **witness)
            semantic_machine_failures.append(failure)
            write_json(output/f'mismatch-{pid}.json', dict(**failure, bits=full,
                source_details=source['details']))
            print(json.dumps(dict(stage='CONFIRMED SEMANTIC MISMATCH',
                                  pattern_id=pid, source_id=witness['source_id'],
                                  tick=witness['tick'], actual=actual,
                                  contract=source['contract'])), flush=True)
        elif errors:
            machine_control_outputs.append(dict(pattern_id=pid, actual=actual,
                contract=source['contract'], errors=errors, **witness))
        machine_family_counts[source['family']] += 1
        if index % 50 == 0:
            write_json(cache_path, cache)
            print(json.dumps(dict(stage='actual content 2DFT', unique_rows=index,
                selected_rows=len(machine_witnesses), disagreements=len(machine_disagreements),
                semantic_mismatches=len(semantic_machine_failures),
                elapsed_seconds=round(perf_counter()-started, 1))), flush=True)
    write_json(cache_path, cache)
    if runtime_hashes() != hashes:
        raise AssertionError('Runtime or driver changed during test')
    coverage = defaultdict(Counter)
    for source in sources.values():
        mode = source['contract'][0]
        coverage[mode]['sources'] += 1
        coverage[mode]['represented_frames'] += source['ticks']+1
    control_counts = Counter(r['family'] for r in control_outputs)
    summary = dict(database=dict(path=str(database.resolve()), bytes=database.stat().st_size,
        sha256=file_hash(database), sources=len(sources),
        represented_frames=sum(v['represented_frames'] for v in family_totals.values()),
        distinct_patterns=len(results)), runtime_sha256=hashes,
        diagnostic=dict(kind='global literal-hit/ownership diagnostic, not 2DFT execution',
            distinct_rows=len(results), literal_side_context_cells=max_side_context,
            retained_ether_guard_cells=keep, full_crop_agreement_rows=full_crop_checks,
            semantic_mismatches=len(diagnostic_failures),
            unexpected_noncontent_control_outputs=len(control_outputs),
            noncontent_control_output_families=dict(sorted(control_counts.items()))),
        positive_controls={k: dict(v) for k, v in sorted(positive_controls.items())},
        contract_coverage={k: dict(v) for k, v in sorted(coverage.items())},
        independent_static_endpoint_checks=endpoint_checks,
        independent_static_endpoint_failures=endpoint_failures,
        actual_2dft=dict(unique_full_guard_rows=len(machine_witnesses),
            selected_native_phases=machine_phases, family_rows=dict(sorted(machine_family_counts.items())),
            diagnostic_disagreements=machine_disagreements,
            semantic_mismatches=semantic_machine_failures,
            unexpected_noncontent_control_outputs=machine_control_outputs,
            agreement_compares='Exact status, ordered static word, ordered moving word, and rejection reason'),
        family_totals={f: dict(c) for f, c in sorted(family_totals.items())},
        elapsed_seconds=round(perf_counter()-started, 2),
        full_decoder_run=False, full_coverage_or_closure_proved=False,
        scope='All stored words diagnostically; actual 2DFT on phase-stratified full guarded rows. '
              'Isolated sources are not complete ready/program/ossifier observations.')
    write_json(output/'decoder-database-summary.json', summary)
    db.close()
    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=HERE/'results/decoder-database')
    parser.add_argument('--machine-phases', type=int, default=30,
                        help='Actual-machine phase strata per source family (default30).')
    args = parser.parse_args()
    if args.machine_phases < 1:
        parser.error('--machine-phases must be positive')
    summary = scan(args.database, args.output, args.machine_phases)
    if (summary['diagnostic']['semantic_mismatches'] or
            summary['actual_2dft']['semantic_mismatches'] or
            summary['actual_2dft']['diagnostic_disagreements'] or
            summary['independent_static_endpoint_failures']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
