"""Check phase/group continuation of the release encoder's source strings."""
from hashlib import sha256
from itertools import product
import json
from math import lcm
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from pyca_verifier.encoder import Encoder, Initialization, PROGRAM_CYCLE_MARKER_TILES
from pyca_verifier.gui.simulation import Simulation
from pyca_verifier.patterns import ETHER


def program_encoder(appendants, phase):
    # These are exactly the fields read by the unchanged program() method.
    # Its metric gap calculation is unrelated to source-fold associativity.
    encoder = object.__new__(Encoder)
    encoder.initialization = Initialization('Y', appendants)
    encoder.phase = phase
    encoder.trace = []
    encoder.cycle_marker_tiles = PROGRAM_CYCLE_MARKER_TILES
    return encoder


def ossifier_encoder(phase, count, short, long):
    encoder = object.__new__(Encoder)
    encoder.oss_phase = phase
    encoder.ossifier_count = count
    encoder.short_distance = short
    encoder.long_distance = long
    return encoder


def run(output_dir=None):
    if not __debug__:
        raise RuntimeError('Run soundness checks without Python -O; assertions are required.')
    output_dir = HERE/'results' if output_dir is None else Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    programs = []
    for letters in product('YN', repeat=6):
        w = ''.join(letters)
        programs.extend(((w,), (w, ''), (w, '', ''), (w, '', '', w*2)))
    program_cases = ossifier_cases = 0
    failures = []
    for appendants in programs:
        for phase in range(30):
            whole = program_encoder(appendants, phase)
            expected = whole.program(4)
            chunks = program_encoder(appendants, phase)
            actual = ''.join(chunks.program(k) for k in (1, 2, 1))
            if actual != expected or whole.phase != chunks.phase:
                failures.append(dict(kind='program', appendants=appendants, phase=phase))
            program_cases += 1
    for phase, count, short, long in product(range(3), range(6), (179, 267, 281), (353, 367, 969)):
        whole = ossifier_encoder(phase, count, short, long)
        expected = whole.ossifiers(13)
        chunks = ossifier_encoder(phase, count, short, long)
        parts = [chunks.ossifiers(k) for k in (3, 4, 6)]
        if (''.join(reversed(parts)) != expected or whole.oss_phase != chunks.oss_phase
                or whole.ossifier_count != chunks.ossifier_count):
            failures.append(dict(kind='ossifier', phase=phase, count=count, short=short, long=long))
        ossifier_cases += 1
    marker = len(ETHER)*PROGRAM_CYCLE_MARKER_TILES
    batch_ticks = Simulation.rows_per_batch*Simulation.ticks_per_row
    common_period = lcm(3, 7, 30)
    result = dict(
        passed=not failures,
        program_chunk_cases=program_cases, ossifier_chunk_cases=ossifier_cases,
        program_initial_phases=list(range(30)), ossifier_state_space='3 phases x 6 group positions',
        marker_cells=marker, marker_over_increment=marker//2,
        marker_up_increment=3*marker//14,
        marker_preserves_cook_phase_classes=(marker//2) % 4 == 0 and (3*marker//14) % 6 == 0,
        gui_insertion_ticks=batch_ticks, gui_free_phase_period=common_period,
        gui_insertion_preserves_free_temporal_phases=batch_ticks % common_period == 0,
        failures=failures,
        scope='Source-fold continuation and free carrier phases; no proof of arbitrary live-splice causality.',
        source_sha256={str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in
                       (Path(__file__).resolve(), ROOT/'pyca_verifier/encoder.py',
                        ROOT/'pyca_verifier/gui/simulation.py')},
    )
    (output_dir/'chunk-generation.json').write_text(json.dumps(result, indent=2)+'\n')
    assert not failures, failures[:3]
    assert result['marker_preserves_cook_phase_classes']
    assert result['gui_insertion_preserves_free_temporal_phases']
    return result


if __name__ == '__main__':
    result = run()
    print(f"Passed {result['program_chunk_cases']} program and {result['ossifier_chunk_cases']} ossifier continuation cases.")
