"""Check every native CA tick, with finite or exact periodic ether exteriors."""
from copy import deepcopy
from hashlib import sha256
from time import perf_counter
from .automaton import step
from .encoder import Initialization, GEOMETRY, build_seed, make_encoder
from .ready import ReadyDetector, ReadyTrace


def run(initialization=Initialization(), *, ticks=25000, program_cycles=8,
        extra_ossifiers=6, decode_tape=True, stop_after_ready_states=None,
        stop_on_failure=False, stop_when_reference_halts=False,
        dynamic_padding=False, horizon_growth_stages=1, max_ticks=None,
        on_ready=None):
    """Run native CA dynamics; optionally observe each decoded ready event.

    ``on_ready(row, event)`` receives an immutable BitRow and a deep copy of
    the recorded event. Its return value is ignored. This diagnostic hook
    supplies no state or missing output to the CA, readiness or decoder.
    """
    if type(ticks) is not int or ticks < 0:
        raise ValueError('ticks must be a nonnegative integer')
    if stop_after_ready_states is not None:
        _positive_integer('stop_after_ready_states', stop_after_ready_states)
    if (stop_after_ready_states is not None or stop_when_reference_halts) and not decode_tape:
        raise ValueError('Decoded ready-state stopping requires decode_tape=True')
    if on_ready is not None:
        if not callable(on_ready):
            raise TypeError('on_ready must be callable or None')
        if not decode_tape:
            raise ValueError('on_ready requires decode_tape=True')
    _positive_integer('horizon_growth_stages', horizon_growth_stages)
    if max_ticks is not None:
        _positive_integer('max_ticks', max_ticks)
        ticks = min(ticks, max_ticks)
    if horizon_growth_stages > 1 and (
            not dynamic_padding or stop_after_ready_states is None or ticks < 1):
        raise ValueError('Growing the horizon requires dynamic padding, a decoded-state goal and positive ticks')
    seed = build_seed(initialization, program_cycles=program_cycles,
                      extra_ossifiers=extra_ossifiers,
                      padding_cells=2048 if dynamic_padding else ticks+14)
    row = seed.row
    background = None
    if dynamic_padding:
        from .background import EtherBackground
        background = EtherBackground(row, guard_cells=2048)
        row = background.row
    detector = ReadyDetector()
    trace = ReadyTrace()
    decoder = None
    decoded_events = []
    failure_snapshot = None
    if decode_tape:
        from .canonical_decoder import Decoder
        from .cts import CTSState
        from .program import recognize_program_phase, ProgramPhaseError
        decoder = Decoder(initialization.appendants)
        reference = CTSState(initialization.tape)
    started = perf_counter()
    stop_reason = 'tick_budget_exhausted'
    budget = ticks
    stages = []
    stage_start = 0
    stage_started = started
    while True:
        observation = detector.observe(row)
        trace.observe(observation)
        if decoder is not None and observation.is_ready:
            result = decoder.decode(row)
            try:
                phase = recognize_program_phase(row, observation.matches[0].leader_x,
                                                decoder.program)
                phase_diagnostic = {'appendant_index': phase.appendant_index,
                    'leaders_to_anchor': phase.leaders_to_anchor,
                    'anchor_x': phase.anchor_x,
                    'matches_reference': phase.appendant_index == reference.appendant_index}
            except ProgramPhaseError as exc:
                phase_diagnostic = {'unsupported': str(exc)}
            decoded_events.append({'tick': row.time, **result.as_dict(),
                'reference': reference.as_dict(),
                'tape_matches_reference': result.tape == reference.tape if result.supported else None,
                'phase_matches_reference': result.appendant_index == reference.appendant_index
                                           if result.supported else None,
                'program_phase_diagnostic': phase_diagnostic})
            if failure_snapshot is None and (not result.supported or
                    result.tape != reference.tape or
                    result.appendant_index != reference.appendant_index):
                # Keep the actual complete binary input, so a later decoder
                # repair can be checked without replaying its CA trajectory.
                failure_snapshot = row
            if on_ready is not None:
                on_ready(row, deepcopy(decoded_events[-1]))
            # The reference never supplies missing symbols to the decoder.
            # Its one-step-per-signal alignment is an experimental hypothesis.
            reference = reference.advance(initialization.appendants)
        if stop_on_failure:
            failure = _observed_failure(trace.as_dict(), decoded_events)
            if failure is not None:
                stop_reason = failure
                break
        if stop_after_ready_states is not None and len(decoded_events) >= stop_after_ready_states:
            stop_reason = 'requested_ready_states_observed'
            break
        if stop_when_reference_halts and not reference.tape:
            stop_reason = 'halting_ready_returns_not_implemented'
            break
        if row.time >= budget:
            if (len(stages) + 1 < horizon_growth_stages
                    and (max_ticks is None or budget < max_ticks)):
                stages.append({'stage': len(stages) + 1, 'start_tick': stage_start,
                    'end_tick': row.time, 'tick_budget': budget,
                    'observed_ready_states': len(decoded_events),
                    'elapsed_seconds': perf_counter() - stage_started,
                    'status': 'continued_without_restart'})
                stage_start = row.time
                stage_started = perf_counter()
                budget *= 2
                if max_ticks is not None:
                    budget = min(budget, max_ticks)
            else:
                if horizon_growth_stages > 1:
                    stop_reason = ('tick_limit_reached' if max_ticks is not None
                                   and budget >= max_ticks else 'automatic_horizon_limit_reached')
                break
        row = background.step() if background is not None else step(row)
    seconds = perf_counter()-started
    stages.append({'stage': len(stages) + 1, 'start_tick': stage_start,
        'end_tick': row.time, 'tick_budget': budget,
        'observed_ready_states': len(decoded_events),
        'elapsed_seconds': perf_counter() - stage_started, 'status': stop_reason})
    first = trace.events[0]['tick'] if trace.events else None
    report = {
        'milestone': ('state-only 2DFT decoding at native-tick ready signals'
                      if decoder is not None else 'native-tick readiness recognition'),
        'initialization': {'tape': initialization.tape,
                           'appendants': list(initialization.appendants),
                           'geometry': GEOMETRY.as_dict()},
        'signatures': [signature.as_dict() for signature in detector.signatures],
        'signature_family': {'leader_phase': 2, 'leader_prefix_cells': 99,
            'gap_cells': 28, 'c2_phases': [s.c2_phase for s in detector.signatures],
            'leader_to_c2_anchor_band': [34, 41]},
        'evolution': {'native_ticks': row.time, 'tick_budget': budget,
                      'stop_reason': stop_reason, 'tick_stride': 1,
                      'reservoir_splices': 0,
                      'boundary': ('exact independently phased periodic ether exteriors'
                                   if background is not None else 'shrinking exact known light cone'),
                      'dynamic_padding': dynamic_padding, 'simulation_restarts': 0,
                      'horizon_stages': stages,
                      'seed': seed.metadata, 'last_origin': row.origin,
                      'last_width': row.width,
                      'last_row_sha256': sha256(row.word().encode()).hexdigest(),
                      'elapsed_seconds': seconds},
        'readiness': trace.as_dict(),
        'initial_seed_is_ready': bool(trace.events and first == 0),
        'first_ready_tick': first,
        'formal_status': {
            'ready_predicate': 'exactly one occurrence in the known row; state-only',
            'initialization': ('encoded nonempty tape is ready at tick zero'
                if first == 0 else 'initial readiness not established for this seed'),
            'decoded_tape_checked': False,
            'decoded_appendant_phase_checked': False,
            'two_way_decoder_implemented': decoder is not None,
            'decoder_complete_on_ready_language': False,
            'local_simulation_witness_completed': False,
            'halting_ready_returns_implemented': False,
            'finite_word_observation_witness_implemented': False,
            'infinite_background_witness_implemented': False,
            'polynomial_return_bound_proved': False,
        },
    }
    if background is not None:
        report['evolution']['ether_background'] = background.as_dict()
    if failure_snapshot is not None:
        report['failure_snapshot'] = {'origin': failure_snapshot.origin,
            'time': failure_snapshot.time, 'width': failure_snapshot.width,
            'bits': failure_snapshot.word()}
    if decoder is not None:
        supported = [event for event in decoded_events if event['status'] == 'decoded']
        mismatches = [event['tick'] for event in supported if not (
            event['tape_matches_reference'] and event['phase_matches_reference'])]
        complete = bool(decoded_events) and len(supported) == len(decoded_events)
        report['decoder'] = {**decoder.as_dict(), 'events': decoded_events,
            'decoded_events': len(supported),
            'unsupported_events': len(decoded_events)-len(supported),
            'mismatch_ticks': mismatches,
            'all_observed_ready_rows_decoded': complete and not mismatches,
            'reference_alignment': 'One independent CTS step per ready signal; '
                                   'this alignment is tested, not assumed as a proved witness'}
        report['formal_status'].update({
            'decoded_tape_checked': bool(supported),
            'decoded_appendant_phase_checked': bool(supported)})
    return report


def _positive_integer(name, value):
    if type(value) is not int or value < 1:
        raise ValueError(f'{name} must be a positive integer')


def _observed_failure(readiness, events):
    """Do not let a later good return conceal an earlier failure."""
    if readiness['ambiguous_ticks']:
        return 'ambiguous_readiness'
    if readiness['consecutive_ready_ticks']:
        return 'consecutive_ready_events'
    if events:
        event = events[-1]
        if event['status'] != 'decoded':
            return 'unsupported_ready_row'
        if not (event['tape_matches_reference'] and event['phase_matches_reference']):
            return 'decoded_state_mismatch'
    return None


def plan_multisteps(initialization, multisteps):
    """Size fixed reservoirs using a CTS prefix, without supplying decoder data.

    The tick estimate is a geometric heuristic, not a return-time theorem.
    Each appended symbol can consume one complete O packet; three additional
    packets and three additional program cycles leave intact decoder anchors.
    """
    from .cts import CTSState

    _positive_integer('multisteps', multisteps)
    if not isinstance(initialization, Initialization):
        raise TypeError('initialization must be an Initialization')
    encoder = make_encoder(initialization)
    reference = CTSState(initialization.tape)
    produced = 0
    maximum_tape = len(reference.tape)
    planned_steps = 0
    halted_after = 0 if not reference.tape else None
    for index in range(multisteps):
        if not reference.tape:
            break
        if reference.tape[0] == 'Y':
            produced += len(initialization.appendants[reference.appendant_index])
        reference = reference.advance(initialization.appendants)
        planned_steps = index + 1
        maximum_tape = max(maximum_tape, len(reference.tape))
        if not reference.tape:
            halted_after = planned_steps
    z = len(initialization.appendants)
    prefix_cycles = (planned_steps + 1 + z - 1) // z
    program_span = len(encoder.program(prefix_cycles))
    tape_span = len(encoder.tape())
    # Program packets travel at -4/15. Four ticks per encoded cell gives a
    # useful first budget, while horizon continuation handles slower trajectories.
    first_budget = max(1000, 4 * (program_span + tape_span) + 840)
    return {'program_cycles': prefix_cycles + 3,
            'extra_ossifiers': max(0, produced + 3 - 7),
            'produced_symbols': produced,
            'maximum_reference_tape_length': maximum_tape,
            'reference_halts_after_steps': halted_after,
            'first_tick_budget': first_budget,
            'spare_program_cycles': 3, 'spare_ossifier_packets': 3,
            'resource_basis': 'Independent CTS prefix for finite resource planning only',
            'tick_estimate_is_proved_bound': False}


def _verified_prefix(events):
    count = 0
    for event in events:
        if not (event['status'] == 'decoded' and event['tape_matches_reference']
                and event['phase_matches_reference']):
            break
        count += 1
    return count


def run_multisteps(initialization=Initialization(), *, multisteps,
                  max_ticks=None, on_ready=None):
    """Check N first-return transitions using N+1 independently decoded rows.

    One execution continues with exact infinite ether outside the fixed
    program/O reservoirs. A larger horizon never replays earlier ticks.
    An incomplete run, including a missing terminal empty-tape return, never
    passes. A semantic failure is never retried with different resources.
    """
    if max_ticks is not None:
        _positive_integer('max_ticks', max_ticks)
    plan = plan_multisteps(initialization, multisteps)
    required = multisteps + 1
    budget = plan['first_tick_budget']
    if max_ticks is not None:
        budget = min(budget, max_ticks)
    report = run(initialization, ticks=budget,
                 program_cycles=plan['program_cycles'],
                 extra_ossifiers=plan['extra_ossifiers'],
                 decode_tape=True,
                 stop_after_ready_states=required, stop_on_failure=True,
                 stop_when_reference_halts=True, dynamic_padding=True,
                 horizon_growth_stages=8, max_ticks=max_ticks, on_ready=on_ready)
    events = report['decoder']['events']
    verified = _verified_prefix(events)
    reason = _observed_failure(report['readiness'], events)
    if reason is None and verified != len(events):
        reason = ('unsupported_ready_row' if report['decoder']['unsupported_events']
                  else 'decoded_state_mismatch')
    if reason is not None:
        status = 'failed'
    elif verified >= required:
        status, reason = 'passed', 'requested_multisteps_checked'
    else:
        status, reason = 'inconclusive', report['evolution']['stop_reason']
    attempts = [{'attempt': 1, 'tick_budget': report['evolution']['tick_budget'],
                 'native_ticks': report['evolution']['native_ticks'],
                 'observed_ready_states': len(events), 'verified_ready_states': verified,
                 'seed_sha256': report['evolution']['seed']['seed_sha256'],
                 'elapsed_seconds': report['evolution']['elapsed_seconds'],
                 'status': status, 'reason': reason}]
    report['verification_goal'] = {
        'requested_multisteps': multisteps, 'required_ready_states': required,
        'verified_ready_states': verified, 'checked_multisteps': max(0, verified - 1),
        'status': status, 'reason': reason, 'resource_plan': plan,
        'attempts': attempts, 'simulation_runs': 1, 'maximum_horizon_stages': 8,
        'horizon_stages': report['evolution']['horizon_stages'], 'max_ticks': max_ticks,
        'count_convention': 'N first-return transitions require N+1 decoded ready states',
        'empty_tape_return_supported': False}
    return report
