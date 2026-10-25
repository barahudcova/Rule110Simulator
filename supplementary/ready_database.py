"""Search an external collision database for the release's exact ready words.

Only Python's standard library and this checkout are used. SQLite is opened
read-only. No encoder, ready language, decoder, or database record is changed.
"""
from __future__ import annotations

import argparse
from collections import Counter
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
from pyca_verifier.automaton import BitRow, step
from pyca_verifier.patterns import ETHER, TABLES, word
from pyca_verifier.ready import C2_OFFSETS, ReadyDetector, ReadySignature

READ_FAMILIES = frozenset(('ordinary-read-Y', 'ordinary-read-N',
                           'short-read-Y', 'short-read-N', 'short-read-RL', 'short-read-SL'))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def file_hash(path):
    digest = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def source_hashes():
    paths = [Path(__file__).resolve(), HERE/'database-inventory.json']
    paths += [ROOT/'pyca_verifier'/name for name in (
        'automaton.py', 'patterns.py', 'ready.py', 'matching.py', 'optimized_ready_matching.py',
        'data/gliders.json', 'data/dict_sc_sl.json', 'data/encoder_geometry.json')]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def positions(text, pattern):
    at = text.find(pattern)
    while at >= 0:
        yield at
        at = text.find(pattern, at+1)  # Include overlaps.


def matcher_controls(detector, signatures):
    """Exercise all literals at all packed-bit alignments, not CA reachability."""
    count = 0
    for phase, bits in signatures:
        for padding in range(8):
            text = '0'*padding+bits+'0'*20
            literal = sorted((p, at) for p, pattern in signatures for at in positions(text, pattern))
            production = sorted((m.c2_phase, m.start) for m in detector.observe(BitRow.from_word(text)).matches)
            require((phase, padding) in literal and literal == production,
                    ('Literal positive control', phase, padding))
            count += 1
    return count


def unpack(blob, width):
    raw = zlib.decompress(blob)
    value = int.from_bytes(raw, 'little')
    require(len(raw) == (width+7)//8 and value.bit_length() <= width, 'Invalid packed word')
    return value, format(value, f'0{width}b')[::-1], raw


def slice_bits(row, left, right):
    require(row.origin <= left < right <= row.origin+row.width, 'Requested context outside saved frame')
    return (row.value >> (left-row.origin)) & ((1 << (right-left))-1)


def prepared_short_core():
    """Prepare S natively using the shipped SC→SL table, not a ready oracle."""
    calibration = json.loads((ROOT/'pyca_verifier/data/encoder_geometry.json').read_text())
    ap, gap = calibration['components']['SC']['0']['witnesses'][0]
    phase, padding = TABLES['sc_sl']['0']
    row = BitRow.from_word(ETHER*300+word('acceptor', ap)+ETHER*gap
                           +word('SC', 0)+ETHER*(8+padding)+word('SL', phase)+ETHER*300)
    for _ in range(2400):
        row = step(row)
    head = word('L', 2)[:99]
    for _ in range(30):
        text = row.word()
        hits = list(positions(text, ETHER+head))
        if hits:
            require(len(hits) == 1, 'Ambiguous prepared-short phase normalization')
            end = text.rfind(ETHER)
            while end >= 14 and text.startswith(ETHER, end-14):
                end -= 14
            core = text[hits[0]+14:end]
            require(len(core) > len(head), 'Missing complete prepared-short body')
            return core, dict(SC_phase=0, incoming_acceptor_phase=ap,
                              incoming_gap_tiles=gap, raw_SL_phase=phase,
                              table_gap_tiles=padding, preparation_tick=row.time,
                              cells=len(core), sha256=sha256(core.encode()).hexdigest())
        row = step(row)
    raise AssertionError('Native short-leader preparation did not normalize')


def head_orbits(cores):
    records = []
    head = word('L', 2)[:99]
    for kind, core in cores.items():
        initial = BitRow.from_word(ETHER*100+core+ETHER*100, origin=-1400)
        row, samples = initial, []
        for tick in range(211):
            actual = [row.origin+i for i in positions(row.word(), head)]
            expected = [-8*(tick//30)] if tick % 30 == 0 else []
            require(actual == expected, ('Head orbit/alias', kind, tick, actual, expected))
            if actual:
                samples.append([tick, actual[0]])
            if tick < 210:
                row = step(row)
        # All possible disturbed cells lie inside this known cone; 210 ticks
        # and a 56-cell translation also restore the ether on both exteriors.
        offset = row.origin+56-initial.origin
        expected_value = (initial.value >> offset) & ((1 << row.width)-1)
        require(row.value == expected_value, ('Free packet translation closure', kind))
        records.append(dict(kind=kind, rows_checked=211, head_samples=samples,
                            translation_period=210, translation_cells=-56,
                            complete_known_cone_translation=True))
    return records


def semantic_context(text, hit, expected_symbol, kind, cores):
    signature = ReadySignature(hit['phase'])
    c2_start = hit['offset']+14
    c2_end = c2_start+len(word('C2', hit['phase']))
    head_start = hit['offset']+signature.leader_offset
    statics = []
    for symbol in 'YN':
        for phase in range(7):
            core = word(symbol, phase)
            start = c2_end-len(core)
            if start >= 14 and text[start-14:c2_end+14] == ETHER+core+ETHER:
                statics.append(dict(symbol=symbol, phase=phase, offset=start,
                                    rightmost_C2=core.endswith(word('C2', hit['phase']))))
    core = cores[kind]
    leader_ok = text[head_start-14:head_start+len(core)] == ETHER+core
    reasons = []
    if len(statics) != 1 or not statics[0]['rightmost_C2']:
        reasons.append('No unique intact static symbol ending at the matched C2')
    elif statics[0]['symbol'] != expected_symbol:
        reasons.append('Static symbol disagrees with the source participant')
    if not leader_ok:
        reasons.append('Complete expected prepared leader does not match')
    return dict(passed=not reasons, reasons=reasons, static_matches=statics,
                leader_kind=kind, complete_leader_matches=leader_ok,
                leader_core_cells=len(core), head_offset=head_start,
                C2_offset=c2_start, C2_end_offset=c2_end,
                extra_right_ether_guard=(text[head_start+len(core):head_start+len(core)+14] == ETHER))


def approach_windows(db, event, symbol, static_phase, core):
    """Check 30 ticks of actual motion, and prior 30 ticks where recorded."""
    sid, tick = event['source_id'], event['tick']
    cp, c2x, hx0 = event['phase'], event['C2_x'], event['leader_x']
    anchor = c2x-C2_OFFSETS[cp]
    head = word('L', 2)[:99]
    records = []
    for shift in ([0, -30] if tick >= 30 else [0]):
        start = tick+shift
        hx = hx0-8*(shift//30)
        reference = BitRow.from_word(ETHER*100+core+ETHER*100, origin=hx-1400)
        rows = list(db.execute(
            'SELECT f.tick,f.origin,p.cells,p.packed_zlib FROM frames f '
            'JOIN patterns p ON p.id=f.pattern_id WHERE f.source_id=? '
            'AND f.tick BETWEEN ? AND ? ORDER BY f.tick', (sid, start, start+30)))
        require([r[0] for r in rows] == list(range(start, start+31)), ('Incomplete approach window', sid, start))
        for dt, (actual_tick, origin, width, blob) in enumerate(rows):
            value, text, _ = unpack(blob, width)
            row = BitRow(value, width, origin, actual_tick)
            p = (cp+shift+dt) % 7
            c2end = anchor+C2_OFFSETS[p]+len(word('C2', p))
            static = word(symbol, (static_phase+shift+dt) % 7)
            left = c2end-len(static)
            require(text[left-origin-14:c2end-origin+14] == ETHER+static+ETHER
                    and static.endswith(word('C2', p)), ('Perturbed static observation band', sid, actual_tick))
            require(slice_bits(row, hx-8, hx+110) == slice_bits(reference, hx-8, hx+110),
                    ('Perturbed 118-cell head context', sid, actual_tick))
            heads = [origin+i for i in positions(text, head) if hx-8 <= origin+i <= hx+8]
            expected = [hx-8*(dt//30)] if dt % 30 == 0 else []
            require(heads == expected, ('Head temporal/spatial alias', sid, actual_tick))
            if dt < 30:
                reference = step(reference)
        records.append(dict(source_id=sid, event_tick=tick, interval=[start, start+30],
                            lookback=shift < 0, rows_compared=31, passed=True))
    return records


def scan(database, output):
    started = perf_counter()
    before = source_hashes()
    stat = database.stat()
    database_digest = file_hash(database)
    inventory = json.loads((HERE/'database-inventory.json').read_text())
    detector = ReadyDetector()
    signatures = [(s.c2_phase, s.bits) for s in detector.signatures]
    control_cases = matcher_controls(detector, signatures)
    maximum = max(len(bits) for _, bits in signatures)
    short, short_recipe = prepared_short_core()
    cores = {'ordinary': word('L', 2), 'short': short}
    free_orbits = head_orbits(cores)
    db = sqlite3.connect(database.resolve().as_uri()+'?mode=ro', uri=True)
    db.execute('PRAGMA query_only=ON')
    metadata = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
    require(metadata['schema'] == 1 and metadata['build_complete'], 'Unsupported or incomplete database')
    guard = metadata['frame_guard_cells']
    require(guard >= maximum, 'Ether guards shorter than the longest ready word')
    rotations = [ETHER[i:]+ETHER[:i] for i in range(len(ETHER))]
    guarded = {(tile*((guard+13)//14))[:guard] for tile in rotations}
    require(not any(bits in tile*((maximum+27)//14) for _, bits in signatures for tile in rotations),
            'A ready word occurs in pure ether')
    sources = {}
    for sid, family, ticks, details in db.execute('SELECT id,family,ticks,details_json FROM sources'):
        sources[sid] = dict(family=family, ticks=ticks, details=json.loads(details))
    ranges = list(db.execute('SELECT source_id,count(*),min(tick),max(tick) FROM frames GROUP BY source_id'))
    require(len(ranges) == len(sources) > 0, 'Missing source frame ranges')
    frames = 0
    families = {}
    for sid, count, first, last in ranges:
        source = sources[sid]
        require(first == 0 and last == source['ticks'] and count == last+1, ('Incomplete source tick range', sid))
        frames += count
        family = families.setdefault(source['family'], dict(sources=0, frames=0, ready_sources=0, ready_frames=0))
        family['sources'] += 1
        family['frames'] += count
    failures, positive, pattern_phase_counts = [], {}, Counter()
    pattern_count = matcher_comparisons = hashed = guarded_count = 0
    for pid, digest, width, blob in db.execute('SELECT id,sha256,cells,packed_zlib FROM patterns ORDER BY id'):
        value, text, raw = unpack(blob, width)
        require(sha256(width.to_bytes(8, 'little')+raw).hexdigest() == digest, ('Pattern hash', pid))
        hashed += 1
        require(text[:guard] in guarded and text[-guard:] in guarded, ('Non-ether exterior guard', pid))
        guarded_count += 1
        literal = sorted((phase, at) for phase, bits in signatures for at in positions(text, bits))
        production = sorted((m.c2_phase, m.start) for m in detector.observe(BitRow(value, width)).matches)
        require(literal == production, ('Production/literal matcher disagreement', pid, literal, production))
        matcher_comparisons += 1
        if literal:
            hits = [dict(phase=p, offset=at) for p, at in literal]
            positive[pid] = dict(sha256=digest, cells=width, text=text, hits=hits)
            pattern_phase_counts.update(p for p, _ in literal)
            if len(hits) != 1:
                failures.append(dict(problem='Multiple ready occurrences in one local pattern', pattern_id=pid))
        pattern_count += 1
        if pattern_count % 50000 == 0:
            print(f'Scanned {pattern_count:,} distinct words...', flush=True)
    require(pattern_count > 0, 'No patterns were scanned')
    represented_frames = db.execute('SELECT count(*) FROM frames f JOIN patterns p ON p.id=f.pattern_id').fetchone()[0]
    require(represented_frames == frames, 'Some source frames reference a missing pattern')
    expected_sources = {sid for sid, s in sources.items() if s['family'] in READ_FAMILIES}
    events, per_source, windows = [], {}, []
    phase_counts, static_counts, leader_counts = Counter(), Counter(), Counter()
    for pid, pattern in positive.items():
        for sid, tick, origin in db.execute('SELECT source_id,tick,origin FROM frames WHERE pattern_id=? ORDER BY source_id,tick', (pid,)):
            source = sources[sid]
            family = source['family']
            per_source.setdefault(sid, []).append(tick)
            families[family]['ready_frames'] += 1
            for hit in pattern['hits']:
                expected = family in READ_FAMILIES
                kind = 'ordinary' if family.startswith('ordinary-read-') else 'short'
                symbol = source['details'].get('parameters', {}).get('symbol')
                context = semantic_context(pattern['text'], hit, symbol, kind, cores)
                signature = ReadySignature(hit['phase'])
                event = dict(source_id=sid, family=family, tick=tick, pattern_id=pid,
                             origin=origin, phase=hit['phase'], start=origin+hit['offset'],
                             C2_x=origin+hit['offset']+14,
                             leader_x=origin+hit['offset']+signature.leader_offset,
                             expected_consumption_source=expected, context=context)
                events.append(event)
                phase_counts[hit['phase']] += 1
                if not expected or not context['passed']:
                    failures.append(dict(problem='Unexpected or unclassified ready occurrence', event=event))
                    continue
                static = context['static_matches'][0]
                static_counts[f"{static['symbol']}[{static['phase']}]"] += 1
                leader_counts[kind] += 1
                try:
                    windows += approach_windows(db, event, static['symbol'], static['phase'], cores[kind])
                except AssertionError as exc:
                    failures.append(dict(problem='Approach motion/context', source_id=sid, tick=tick, detail=str(exc)))
    for sid in per_source:
        families[sources[sid]['family']]['ready_sources'] += 1
    missing = sorted(expected_sources-set(per_source))
    repeated = {sid: sorted(ticks) for sid, ticks in per_source.items() if len(ticks) != 1}
    if missing:
        failures.append(dict(problem='Consumption source without a ready row', sources=missing))
    if repeated:
        failures.append(dict(problem='Source with multiple ready rows', sources=repeated))
    require(source_hashes() == before, 'Runtime or scan source changed during the scan')
    after = database.stat()
    require((stat.st_size, stat.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Database changed during the scan')
    summary = dict(
        schema=1, status='passed' if not failures else 'failed',
        database=dict(filename=database.name, bytes=stat.st_size, sha256=database_digest,
                      matches_reference_inventory=(database_digest == inventory['database']['sha256']),
                      sources=len(sources), source_families=len(families), frames=frames,
                      distinct_patterns=pattern_count, guard_cells_per_side=guard),
        signatures=[dict(c2_phase=p, cells=len(bits), sha256=sha256(bits.encode()).hexdigest()) for p, bits in signatures],
        counts=dict(literal_positive_control_cases=control_cases,
                    pattern_hashes_checked=hashed, ether_guard_pairs_checked=guarded_count,
                    production_literal_comparisons=matcher_comparisons,
                    matching_distinct_patterns=len(positive), ready_source_tick_frames=sum(v['ready_frames'] for v in families.values()),
                    ready_occurrences=len(events), sources_with_ready_rows=len(per_source),
                    expected_consumption_sources=len(expected_sources), missing_consumption_sources=len(missing),
                    sources_with_multiple_ready_rows=len(repeated),
                    occurrences_by_phase={str(p): phase_counts[p] for p, _ in signatures},
                    matching_patterns_by_phase={str(p): pattern_phase_counts[p] for p, _ in signatures},
                    static_symbols=dict(static_counts), consuming_leaders=dict(leader_counts),
                    native_context_windows=len(windows), lookback_windows=sum(w['lookback'] for w in windows),
                    forward_windows=sum(not w['lookback'] for w in windows),
                    stored_row_context_comparisons=sum(w['rows_compared'] for w in windows)),
        families=dict(sorted(families.items())), prepared_short_recipe=short_recipe,
        free_head_orbits=free_orbits, source_sha256=before, failures=failures,
        source_files_unchanged=True, database_read_only=True, elapsed_seconds=round(perf_counter()-started, 3),
        coverage_limits=[
            'Exhaustive search of all recorded words and source/tick frames, not all globally reachable configurations.',
            'The corpus has no proven global closure; joins of independently recorded contexts are not enumerated.',
            'Positive detection coverage is measured by phase; an absent phase is not positively tested by this scan.',
            'Source labels identify local experiments. Full static and leader cores and actual approach motion are checked independently at every positive occurrence.',
        ],
    )
    details = dict(summary=summary,
                   positive_patterns=[dict(pattern_id=pid, **{k:v for k,v in p.items() if k != 'text'}) for pid,p in positive.items()],
                   events=events, approach_windows=windows)
    output.mkdir(parents=True, exist_ok=True)
    (output/'ready-database-details.json').write_text(json.dumps(details, indent=2)+'\n')
    (output/'ready-database-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    db.close()
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path, help='External collisions.sqlite3 file; opened read-only')
    parser.add_argument('--output', type=Path, default=HERE/'results/ready-database', help='Generated detailed reports')
    parser.add_argument('--record', action='store_true', help='Update the small versioned ready-database-summary.json')
    args = parser.parse_args()
    try:
        summary = scan(args.database, args.output)
    except Exception as exc:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output/'ready-database-error.json').write_text(json.dumps(dict(status='failed', error=f'{type(exc).__name__}: {exc}'), indent=2)+'\n')
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    if args.record and summary['status'] == 'passed':
        (HERE/'ready-database-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(dict(status=summary['status'], counts=summary['counts'], failures=summary['failures']), indent=2))
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
