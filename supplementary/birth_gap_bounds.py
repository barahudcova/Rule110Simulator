#!/usr/bin/env python3
"""Finite bounds on the *reduced* deposition gap g-7B.

Arithmetic certificate conditional on the intended ordered collision network.
This does not simulate Rule 110, infer the invariant, or certify density during
overlapping collisions. See BIRTH_GAP_BOUNDS.md for the definitions and proof.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pyca_verifier.encoder import Encoder, GEOMETRY, Initialization
from pyca_verifier.patterns import DATA, word
from pyca_verifier.spacing_geometry import (
    _program_geometry, calibration, compact_initial_gap_certificate,
)


def as_fraction(value):
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def recurring_bound(appendants):
    """Bound g-7B over all thirty phases and consecutive production endpoints.

    Within a word the long gap applies at multiples of six symbols. Between
    productive words it always applies. The 2z-1 read bound follows from the
    aligned-rotation productivity assumption, not Initialization validation.
    """
    init = Initialization("Y", appendants)
    encoder = Encoder(init)
    z = len(appendants)
    maximum = None
    minimum = None
    witness = None
    cases = 0
    categories = {}
    for phase in range(30):
        entries = _program_geometry(
            appendants, GEOMETRY.moving_symbol_extra_tiles,
            encoder.cycle_marker_tiles, phase, 3*z,
        )
        for i in range(z):
            packets = entries[i]
            candidates = []
            for j in range(len(packets)-1):
                long = (j+1) % GEOMETRY.ossifier_group_size == 0
                candidates.append((j, 0, packets[j+1][0]-packets[j][-1],
                                   encoder.long_distance if long else encoder.short_distance,
                                   "within_appendant_long" if long else "within_appendant_short"))
            if packets:
                for d in range(1, 2*z):
                    if entries[i+d]:
                        candidates.append((len(packets)-1, d,
                                           entries[i+d][0][0]-packets[-1][-1],
                                           encoder.long_distance, "between_appendants"))
            for j, d, delta, gap, kind in candidates:
                # Each productive kappa is -24 or 60. The independent extrema
                # deliberately overapproximate phase-compatible pairs.
                low = 84*gap-delta+350+310*d
                high = 84*gap-delta+518+310*d
                assert low >= 21*573
                cases += 1
                categories[kind] = categories.get(kind, 0)+1
                minimum = low if minimum is None else min(minimum, low)
                if maximum is None or high > maximum:
                    maximum = high
                    witness = dict(raw_phase=phase, appendant=i,
                                   earlier_symbol=j, intervening_reads=d,
                                   source_intercept_difference=delta,
                                   raw_ossifier_gap_tiles=gap, category=kind)
    assert cases and maximum is not None
    return dict(candidate_count=cases, categories=categories,
                short_gap_tiles=encoder.short_distance,
                long_gap_tiles=encoder.long_distance,
                lower_bound=as_fraction(Fraction(minimum, 21)),
                reduced_gap_upper_bound=as_fraction(Fraction(maximum, 21)),
                maximizing_candidate=witness)


def initial_bound(appendants):
    """A finite table bounds the initial-to-first-deposit reduced gap for all n.

    Increasing n by five changes the unrounded guard by 570 and leaves its
    modulo-ten target unchanged. The fixed minimum-guard floor can only make
    the reduced gap decrease as n grows. See the symbolic proof in the report.
    """
    values = []
    extension_checks = 0
    composition_checks = 0
    for r, appendant in enumerate(appendants):
        if not appendant:
            continue
        for residue in range(5):
            n0 = r+1+(residue-r-1) % 5
            tape0 = "N"*r+"Y"+"N"*(n0-r-1)
            first = compact_initial_gap_certificate(Initialization(tape0, appendants))
            assert first is not None and first.first_productive_step == r
            c0 = first.gap_lower_bound_numerator-84*first.selected_guard_tiles
            high = first.gap_lower_bound_numerator+84
            for q in (1, 2, 17, 200):
                n = n0+5*q
                tape = "N"*r+"Y"+"N"*(n-r-1)
                cert = compact_initial_gap_certificate(Initialization(tape, appendants))
                const = cert.gap_lower_bound_numerator-84*cert.selected_guard_tiles
                assert const == c0-9576*(n-n0)
                assert cert.selected_guard_tiles <= first.selected_guard_tiles+114*(n-n0)
                assert cert.gap_lower_bound_numerator+84 <= high
                extension_checks += 1
            # Vary suffix composition, including the far-left initial symbol.
            for suffix in ("Y"*(n0-r-1), "YN"*((n0-r-1)//2)+"Y"*((n0-r-1) % 2)):
                alternate = compact_initial_gap_certificate(
                    Initialization("N"*r+"Y"+suffix, appendants))
                assert alternate == first
                composition_checks += 1
            values.append(dict(first_productive_read=r, length_mod_5=residue,
                               smallest_length=n0, selected_guard_tiles=first.selected_guard_tiles,
                               reduced_gap_upper_bound=as_fraction(Fraction(high, 21))))
    assert values
    high = max(Fraction(v["reduced_gap_upper_bound"]["numerator"],
                        v["reduced_gap_upper_bound"]["denominator"]) for v in values)
    return dict(table=values, reduced_gap_upper_bound=as_fraction(high),
                extension_checks=extension_checks, composition_checks=composition_checks)


def certify(appendants):
    recurring = recurring_bound(appendants)
    initial = initial_bound(appendants)
    def f(v):
        return Fraction(v["numerator"], v["denominator"])
    k0 = max(Fraction(573), f(recurring["reduced_gap_upper_bound"]),
             f(initial["reduced_gap_upper_bound"]))
    return dict(appendants=list(appendants), recurring=recurring,
                first_deposit=initial, K0_cells=as_fraction(k0),
                conditional_bound_14="g <= 2*K0 + 14*C_boundary",
                conditional_bound_21="g <= (3/2)*K0 + (21/2)*C_boundary")


def catalogue_identities():
    """Check the constants used to eliminate initial tape length/composition."""
    records = []
    data = calibration()
    for head, phase in (("Y", 0), ("N", 4)):
        assert data["static_cores"]["Y"][str(phase)][0] == data["static_cores"]["N"][str(phase)][0]
        for s in "YN":
            pitch = len(word(s, phase))+14*(1+(6 if s == "Y" else 7)+32)
            assert pitch == 684
            records.append(dict(head=head, phase=phase, symbol=s, pitch=pitch,
                                first_anchor=data["static_cores"][s][str(phase)][0]))
    assert -15*684+684 == -9576
    assert 9576//84 == 114 and 9576 % 84 == 0
    assert 5*114 % 10 == 0 and 5*28 % 10 == 0
    # Algebra from the native scattering laws, before the pending-crossing term.
    assert 116+171+147 == 434
    assert 700-684+294 == 310
    return records


def default_programs():
    programs = {("".join(chars),) for chars in product("YN", repeat=6)}
    for name in ("decoder-cts-summary.json", "decoder-seeded-summary.json", "decoder-blocks-summary.json"):
        path = ROOT/"supplementary"/name
        if path.exists():
            data = json.loads(path.read_text())
            programs.update(tuple(result["case"]["appendants"]) for result in data["results"])
    return sorted(programs)


def main():
    if not __debug__:
        raise RuntimeError("Run without -O: arithmetic audit assertions must remain enabled")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--appendants", nargs="+", help="Y/N words; use empty for epsilon")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    programs = ([tuple("" if s.lower() == "empty" else s.upper() for s in args.appendants)]
                if args.appendants else default_programs())
    identities = catalogue_identities()
    checks = [certify(program) for program in programs]
    source_paths = [Path(__file__), ROOT/"pyca_verifier/encoder.py",
                    ROOT/"pyca_verifier/spacing_geometry.py", DATA/"encoder_geometry.json",
                    DATA/"gliders.json", *sorted(DATA.glob("dict_*.json"))]
    result = dict(
        status="passed", scope="finite arithmetic certificate conditional on the intended FIFO collision network",
        actual_CA_closure_proved=False, boundary_density_proved_here=False,
        raw_birth_gap_bound_requires_boundary_density=True,
        core_identity="g(t)-7*B(t) = (84*L-delta_e+434+310*d+kappa_old-kappa_new)/21",
        program_count=len(checks),
        source_candidate_count=sum(c["recurring"]["candidate_count"] for c in checks),
        initial_table_entries=sum(len(c["first_deposit"]["table"]) for c in checks),
        initial_length_extension_checks=sum(c["first_deposit"]["extension_checks"] for c in checks),
        initial_composition_checks=sum(c["first_deposit"]["composition_checks"] for c in checks),
        initial_catalogue_identities=identities,
        programs=checks,
        source_sha256={str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest() for path in source_paths},
    )
    if args.record:
        out = ROOT/"supplementary/birth-gap-summary.json"
        # Keep the versioned receipt small; the unabridged per-program table
        # is reproducible with --appendants and is printed without --record.
        for check in result["programs"]:
            table = check["first_deposit"].pop("table")
            check["first_deposit"]["table_entries"] = len(table)
            check["first_deposit"]["maximizing_table_entry"] = max(
                table, key=lambda v: Fraction(v["reduced_gap_upper_bound"]["numerator"],
                                              v["reduced_gap_upper_bound"]["denominator"]))
        out.write_text(json.dumps(result, indent=2)+"\n")
        print(out)
    else:
        print(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ("status", "program_count", "source_candidate_count",
        "initial_table_entries", "initial_length_extension_checks", "initial_composition_checks")}))


if __name__ == "__main__":
    main()
