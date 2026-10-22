"""Check native ready signals and binary 2DFT decoding without graphics dependencies."""
import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path
from .encoder import Initialization
from .runner import run, run_multisteps

EXAMPLES = Path(__file__).parent/'data'/'initializations.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--examples', type=Path, default=EXAMPLES)
    parser.add_argument('--case', default='Two empty')
    parser.add_argument('--tape')
    parser.add_argument('--appendants', nargs='+', help='YN words; empty means an empty appendant')
    parser.add_argument('--multisteps', type=int,
                        help='Check N CTS transitions (N+1 decoded ready states), with automatic finite resources')
    parser.add_argument('--max-ticks', type=int,
                        help='Optional cap on automatic tick budgets with --multisteps')
    parser.add_argument('--ticks', type=int, help='Fixed tick horizon (default: 25000)')
    parser.add_argument('--program-cycles', type=int, help='Fixed program reservoir (default: 8 cycles)')
    parser.add_argument('--ossifiers', type=int, help='Extra ossifier packets in a fixed seed (default: 6)')
    parser.add_argument('--dynamic-padding', action='store_true',
                        help='Use exact periodic ether exteriors in fixed-horizon mode (automatic with --multisteps)')
    parser.add_argument('--readiness-only', action='store_true',
                        help='Recognize ready times without decoding the tape')
    parser.add_argument('--strict', action='store_true',
                        help='Exit unsuccessfully after writing reports if any ready row is unsupported or incorrect')
    parser.add_argument('--output', type=Path, default=Path('artifacts/ready-times'))
    args = parser.parse_args()
    if args.multisteps is not None:
        if any(value is not None for value in (args.ticks, args.program_cycles, args.ossifiers)):
            parser.error('--multisteps chooses --ticks, --program-cycles and --ossifiers automatically; '
                         'omit those options, or use fixed-horizon mode')
        if args.readiness_only:
            parser.error('--multisteps requires decoding; omit --readiness-only')
    elif args.max_ticks is not None:
        parser.error('--max-ticks requires --multisteps')
    try:
        examples = json.loads(args.examples.read_text())
        if args.case not in examples:
            parser.error(f'Unknown case {args.case!r}; choose from {list(examples)}')
        selected = examples[args.case]
        tape = selected['tape'] if args.tape is None else args.tape
        rules = selected['appendants'] if args.appendants is None else [
            '' if value == 'empty' else value for value in args.appendants]
        initialization = Initialization(tape, tuple(rules))
        if args.multisteps is not None:
            report = run_multisteps(initialization, multisteps=args.multisteps,
                                   max_ticks=args.max_ticks)
        else:
            report = run(initialization, ticks=25000 if args.ticks is None else args.ticks,
                         program_cycles=8 if args.program_cycles is None else args.program_cycles,
                         extra_ossifiers=6 if args.ossifiers is None else args.ossifiers,
                         decode_tape=not args.readiness_only,
                         dynamic_padding=args.dynamic_padding)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=True)
    snapshot = report.get('failure_snapshot')
    if snapshot is not None:
        checkpoint = args.output/f"failure-{snapshot['time']}.json.gz"
        with gzip.open(checkpoint, 'wt') as stream:
            json.dump(snapshot, stream, separators=(',', ':'))
        report['failure_snapshot'] = {key: snapshot[key] for key in ('origin', 'time', 'width')}
        report['failure_snapshot'].update({'file': checkpoint.name,
            'binary_sha256': sha256(snapshot['bits'].encode('ascii')).hexdigest(),
            'input': 'Complete binary row supplied to the decoder'})
    destination = args.output/'report.json'
    destination.write_text(json.dumps(report, indent=2)+'\n')
    pieces = []
    for signature in report['signatures']:
        pieces.append(
            f"{signature['cells']} cells: ether + C2[{signature['c2_phase']}] + 2 ether tiles + common ready head[2]\n"
            f"C2 starts at offset {signature['c2_offset']}; leader head at {signature['leader_offset']}.\n"
            f"Core-edge gap: {signature['gap_cells']} cells.\n"
            +signature['bits'])
    (args.output/'ready-sequences.txt').write_text('\n\n'.join(pieces)+'\n')
    events = report['readiness']['events']
    lines = ['ready_index,tick,return_ticks,c2_x,leader_x,c2_phase,c2_anchor']
    lines.extend(','.join(str(event[key]) if event[key] is not None else ''
                         for key in ('ready_index','tick','return_ticks','c2_x','leader_x',
                                     'c2_phase','c2_anchor'))
                 for event in events)
    (args.output/'ready-times.csv').write_text('\n'.join(lines)+'\n')
    if 'decoder' in report:
        import csv
        with (args.output/'decoded-tapes.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(('tick', 'status', 'appendant_index', 'tape', 'reason',
                             'expected_appendant_index', 'expected_tape',
                             'tape_matches_reference', 'phase_matches_reference'))
            for event in report['decoder']['events']:
                writer.writerow((event['tick'], event['status'], event['appendant_index'],
                    event['tape'], event['reason'], event['reference']['appendant_index'],
                    event['reference']['tape'], event['tape_matches_reference'],
                    event['phase_matches_reference']))
    print(f"Checked {report['readiness']['checked_ticks']} consecutive native CA ticks.")
    print('Ready ticks: '+(', '.join(str(event['tick']) for event in events) or 'none'))
    print(f"Multiple-match ticks: {len(report['readiness']['ambiguous_ticks'])}")
    if 'decoder' in report:
        print(f"Decoded: {report['decoder']['decoded_events']}; "
              f"unsupported: {report['decoder']['unsupported_events']}; "
              f"mismatches: {len(report['decoder']['mismatch_ticks'])}")
    if 'verification_goal' in report:
        goal = report['verification_goal']
        print(f"Multisteps: {goal['checked_multisteps']}/{goal['requested_multisteps']}; "
              f"{goal['status']} ({goal['reason']})")
        plan = goal['resource_plan']
        print(f"Automatic resources: {plan['program_cycles']} program cycles, "
              f"{7 + plan['extra_ossifiers']} ossifier packets; "
              f"{goal['simulation_runs']} run, {len(goal['horizon_stages'])} horizon stage(s).")
    print(f'Report: {destination}')
    if 'verification_goal' in report and report['verification_goal']['status'] != 'passed':
        raise SystemExit(1)
    if args.strict and 'decoder' in report and (
            report['decoder']['unsupported_events'] or report['decoder']['mismatch_ticks']):
        raise SystemExit(1)
