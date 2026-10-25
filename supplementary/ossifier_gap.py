#!/usr/bin/env python3
"""Check the recurring ossifier gap in fitted, 28-cell ether-piece units.

This checks agreement with the encoder and minimality for its finite affine
certificate. It does not establish the global Rule 110 collision invariant.
Uses the standard library and this checkout only; no simulation is run.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pyca_verifier.encoder import Encoder, GEOMETRY, Initialization
from pyca_verifier.patterns import DATA
from pyca_verifier.spacing_geometry import _program_geometry
from supplementary.birth_gap_bounds import default_programs


CLEARANCE = 573
ORDER_EXAMPLES = (
    ("YYYYYY", "NNNNNN", "YYYYYY", "NNNNNN"),
    ("YYYYYY", "YYYYYY", "NNNNNN", "NNNNNN"),
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def ceil_div(numerator, denominator):
    return -(-numerator // denominator)


def source_score(appendants, marker):
    """Enumerate candidates, independently of the certificate's maximum.

    The calibrated source geometry is shared with the runtime. This audit
    checks its use in the gap formula, not the calibration's CA derivation.
    All within-appendant seams are included, as in the runtime certificate;
    some will actually use the shorter within-group gap.
    """
    count = 0
    maximum = None
    witness = None
    z = len(appendants)
    for phase in range(30):
        entries = _program_geometry(appendants,
            GEOMETRY.moving_symbol_extra_tiles, marker, phase, 3*z)
        for i in range(z):
            packets = entries[i]
            candidates = [(j, 0, packets[j+1][0]-packet[-1])
                          for j, packet in enumerate(packets[:-1])]
            if packets:
                candidates.extend((len(packets)-1, d,
                    entries[i+d][0][0]-packets[-1][-1])
                    for d in range(1, 2*z) if entries[i+d])
            for symbol, reads, delta in candidates:
                count += 1
                score = delta-310*reads
                if maximum is None or score > maximum:
                    maximum = score
                    witness = dict(raw_leader_phase=phase, appendant=i,
                        earlier_symbol=symbol, reads=reads,
                        source_intercept_difference=delta)
    require(maximum is not None, "No source candidates were enumerated")
    return maximum, count, witness


def check_program(appendants):
    encoder = Encoder(Initialization("Y", appendants))
    text = "".join(appendants)
    nonempty = sum(bool(a) for a in appendants)
    nu = (76*text.count("Y") + 80*text.count("N") + 60*nonempty
          + 43*(len(appendants)-nonempty))
    baseline = 4*(nu//4)+64
    score, candidates, witness = source_score(appendants,
                                              encoder.cycle_marker_tiles)
    # In piece units the certificate is 21*g >= 168*mu+434-score.
    lower = ceil_div(21*CLEARANCE+score-434, 168)
    increments = max(0, ceil_div(lower-baseline, 7))
    mu = baseline+7*increments
    numerator = 168*mu+434-score
    residue = (4*(nu//4)+1) % 7
    require(2*mu+1 == encoder.long_distance,
            (appendants, "piece-unit formula differs from encoder"))
    require(score == encoder.long_gap_certificate.long_source_score,
            (appendants, "source maximum differs from certificate"))
    require(encoder.long_gap_certificate.adjacent_c2_clearance_cells == CLEARANCE,
            "The runtime's clearance target changed")
    require(mu % 7 == residue, (appendants, "wrong phase residue"))
    require(numerator >= 21*CLEARANCE,
            (appendants, "certified clearance below target"))
    require(mu >= nu+61, (appendants, "inherited lower bound changed"))
    # If a preceding permitted choice exists above the baseline, it must fail.
    require(increments == 0 or 168*(mu-7)+434-score < 21*CLEARANCE,
            (appendants, "chosen gap is not minimal for this certificate"))
    require((168*(mu+7)+434-score)-numerator == 21*56,
            "A seven-piece increment no longer gives 56 cells of clearance")
    return dict(appendants=list(appendants), nu=nu, baseline_mu=baseline,
        seven_piece_increments=increments, selected_mu=mu,
        raw_fourteen_cell_gap=encoder.long_distance, residue_mod_7=residue,
        source_score=score, source_candidates=candidates,
        certified_clearance=dict(numerator=numerator, denominator=21),
        maximizing_candidate=witness)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--appendants", nargs="+",
                        help="Check one program; use empty for epsilon")
    parser.add_argument("--output", type=Path,
                        default=ROOT/"supplementary/results/ossifier-gap")
    parser.add_argument("--record", action="store_true",
                        help="Also refresh supplementary/ossifier-gap-summary.json")
    args = parser.parse_args()
    if args.appendants:
        programs = [tuple("" if s.lower() == "empty" else s.upper()
                          for s in args.appendants)]
        corpus_count = 1
    else:
        corpus = default_programs()
        corpus_count = len(corpus)
        programs = sorted(set(corpus) | set(ORDER_EXAMPLES))
    checks = [check_program(program) for program in programs]
    if not args.appendants:
        examples = [next(c for c in checks if tuple(c["appendants"]) == p)
                    for p in ORDER_EXAMPLES]
        require(examples[0]["nu"] == examples[1]["nu"],
                "The order examples no longer have the same weighted count")
        require(examples[0]["selected_mu"] != examples[1]["selected_mu"],
                "The order examples no longer distinguish the selected gap")
    sources = [Path(__file__), ROOT/"supplementary/birth_gap_bounds.py",
        ROOT/"pyca_verifier/encoder.py", ROOT/"pyca_verifier/spacing_geometry.py",
        DATA/"encoder_geometry.json", DATA/"gliders.json",
        *sorted(DATA.glob("dict_*.json"))]
    result = dict(status="passed",
        scope="finite arithmetic agreement and certificate minimality; conditional on the intended ordered collision network",
        global_CA_embedding_proved=False, native_simulations_run=0,
        formula="mu=4*floor(nu/4)+64+7*k, least k>=0 with 168*mu+434-S >= 21*573",
        corpus_programs=corpus_count, program_count=len(checks),
        additional_order_examples=len(checks)-corpus_count,
        source_candidate_count=sum(c["source_candidates"] for c in checks),
        programs_requiring_increase=sum(c["seven_piece_increments"] > 0 for c in checks),
        checks=["encoder agreement", "independent source maximum", "phase residue",
                "certified clearance", "minimum within permitted class and baseline",
                "mu strictly exceeds nu", "increment gives 56-cell clearance"],
        programs=checks,
        source_sha256={str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest()
                       for p in sources})
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output/"report.json"
    text = json.dumps(result, indent=2)+"\n"
    destination.write_text(text)
    if args.record:
        (ROOT/"supplementary/ossifier-gap-summary.json").write_text(text)
    print(destination)
    print(json.dumps({k: result[k] for k in ("status", "corpus_programs",
        "program_count", "source_candidate_count", "programs_requiring_increase")}))


if __name__ == "__main__":
    main()
