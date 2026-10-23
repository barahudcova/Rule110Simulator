# Encoder verification

This folder checks the encoder shipped in this repository against Cook's local
alignment conditions. It contains the report, executable checks, and a
[compact record of the verified run](verified-summary.json). The checks use
the actual binary catalogue and phase tables in `pyca_verifier/data/`; they
derive particle phases directly from native Rule 110 evolution.

The separate [database report](DATABASE.md) describes the collision corpus.
The [ready-word database audit](READY_DATABASE.md) reports an exhaustive scan
of that corpus and checks the meaning and motion of every detected approach.
It has its own [recorded summary](ready-database-summary.json) and optional
external-database command, separate from the encoder checks below.

The [decoder testing report](DECODER.md) covers the collision vocabulary,
actual finite-state content-reader executions, and complete native Rule 110
runs compared with independent cyclic-tag calculations. It links to the test
drivers, per-input results, and exact-row replay instructions. These are
separate tests; `run.py` runs the encoder checks below.

**All recorded encoder checks pass.** The result establishes finite source-alignment
identities and local binary collision contracts. The spacing argument is
conditional on Cook's intended collision network, including its encounter
order and isolation. Global ready-language uniqueness and decoder completeness
remain separate questions; the optional database scan establishes its stated
finite coverage.

## Reproduce

From the repository root, with Python 3.10 or later:

```sh
python soundness/run.py
```

No installation or third-party packages are required. The command returns a
nonzero exit status on a failed check and writes detailed receipts to
`soundness/results/`, which is ignored by Git. `--output PATH` changes that
destination. Do not use Python's `-O` option: the checks require assertions.

The receipts identify the audited source files by SHA-256. The runner also
checks that those files remain unchanged during the run. After reviewing a
change to the encoder or checks, `python soundness/run.py --record` updates
the small versioned `verified-summary.json`; ordinary runs leave it unchanged.

## Measured connections

Cook's distances refer to the ether between particles, rather than the
bounding boxes of their binary cores. With an E-bar particle involved, over
distance is considered modulo four and up distance modulo six. Distances
between two C₂s or two A⁴s below are absolute distances in his convention.

| Connection | Measured value or native contract |
| --- | --- |
| Internal C₂s of Y | Over distances 18, 18, 14 |
| Internal C₂s of N | Over distances 18, 10, 14 |
| Y followed by either stationary symbol | Over distance 274 |
| N followed by either stationary symbol | Over distance 282 |
| Initial Y–L and N–L | Over distance 1 modulo 4 from the final C₂ to the consuming head |
| Standard/principal components and the preceding leader's tail | Up 2 modulo 6; over 0 modulo 4, in 181 cases |
| Component followed by raw R or S | Exact ordinary or short prepared leader after the native collision |
| Short leader followed by S′ or R | Exact prepared successor, with the following source frontier retained |
| Internal A⁴s of a complete ossifier O | Up distances 83, 113, 77 |
| Neighboring complete ossifiers, raw gap g | Up distance 3g+2; every selected g is odd |
| First invisible and first A⁴ | Up 0 modulo 6 |
| Productive moving data and A⁴ | Up 5 modulo 6 under the verified source/crossing phase arithmetic |

The stationary-symbol distances are all 2 modulo 4 and exceed Cook's minimum
six. All internal and inter-ossifier up distances are 5 modulo 6. The 56-cell
program-cycle marker adds 28 over units and 12 up units, preserving both
phase classes.

The implemented ossifier has Cook-width ether powers `(13,18,12)`, whereas
Cook's 2009 illustration uses `(13,11,12)`. Beyond checking congruences, 120
whole-packet conversions verify that the implemented cluster produces the
exact four C₂s of Y or N, with no unexplained outgoing disturbance. Both
conversion phases tested are recorded separately; the initial phase arithmetic
selects Cook's intended up-five branch.

## Why the program check covers arbitrary words

The source grammar records the carrier phase, whether a symbol is first or
subsequent in an appendant, whether the current appendant is empty, and its
length modulo six. Exhaustive reachability from the initial leader gives
**120 states, 270 edges, and 60 appendant-closing transitions**. Both Y and N
choices and the distinct S/S′ transitions are included. Thus consecutive
empty appendants are not restricted to a fixed tested run length.

Every applicable transition satisfies the source identities. Those identities
therefore extend by induction along this finite graph to arbitrary grammatical
appendant words. The checks retain full E-bar temporal phases: a trajectory
intercept alone loses information needed to distinguish collision outcomes.
Fresh native component emissions also agree with the runtime calibration.

The exact emitted Y/N packet shapes are independent of the entering phase
and of whether the symbol is first in its appendant. They match the packets
used in the whole-ossifier checks. Native leader tests compare the complete
prepared successor, including the retained next leader; they also require
exactly two outgoing garbage particles and account for every non-ether
fourteen-cell window at the short-leader consumption endpoints.

The first invisible's alignment with the initial tape and ossifier, and the
first productive packet's alignment, are checked for both initial head
values. The algebraic reductions are independent of tape length: the initial
guard has the required odd residue, and added symbols contribute multiples
of the relevant phase period. These bootstrap calculations use Cook's
prescribed crossing history.

## Absolute gaps and incremental supply

For z appendants, productivity in each aligned complete rotation bounds the
distance between consecutive productive reads by `2z−1`. The runtime gap
routine enumerates the relevant endpoints and all thirty source phases for
the supplied program. If Q is the maximum source-separation score, its
collision-network bound has the form

```text
21 × completed stationary boundary gap ≥ 84g − Q + 350.
```

The routine chooses g so the right side is at least `21×573`, then rounds
upwards in the permitted residue class. The initial guard uses the analogous
inequality for the actual first productive read. This is an all-input
arithmetic argument within the prescribed collision network. In addition,
1,859 productive initial words across eight program structures check the
implementation of those inequalities. The initial padding's symbolic lookup
is described in [INITIAL_GAP.md](../INITIAL_GAP.md).

Source continuation is checked byte for byte: complete program strings equal
successive chunks in 7,680 cases, and ossifier strings in 162 cases. The
encoder's persistent phase and group state make these concatenations
associative. The viewer's 840-tick insertion interval is a multiple of the
common 210-tick free-particle period.

## Scope of the soundness claim

Conditional on the intended collision invariant, these results establish
the audited source-alignment obligations for the released encoder. Three
limits remain explicit:

1. Raw leaders start with Eⁿ particles. Cook's special numerical distance
   association through Eⁿ is not implemented here. Complete native preparation
   and successor-packet checks establish those local reactions directly.
2. The gap inequalities bound completed-deposition separations. Inferring
   that an ossifier cannot encounter old stationary data earlier also uses
   the assumed encounter order and isolation. Continuing productivity is an
   input-trajectory hypothesis, not a consequence of syntactic validation.
3. Source concatenation and insertion phases are checked. Equivalence of
   every viewport-dependent live splice with one fixed infinite evolution
   additionally needs a causal boundary argument.

These checks do not provide a new global Rule 110 universality proof or an
exhaustive database of all simultaneous collision neighborhoods.

## Code and references

| File | Checks |
| --- | --- |
| [distance_conventions.py](distance_conventions.py) | Geometric ether references for all 40 C₂/A⁴/E-bar phases |
| [program_joins.py](program_joins.py) | Finite phase grammar, 181 Cook measurements, 361 free joins, component emissions and R/S/S′ reactions |
| [program_geometry.py](program_geometry.py) | Native free-orbit and join geometry used by the program audit |
| [static_ossifier_joins.py](static_ossifier_joins.py) | Y/N and O spacings, bootstrap phases, 120 whole conversions, 1,020 atomic input contexts, initial/recurring gap bounds |
| [chunk_generation.py](chunk_generation.py) | Source continuation and insertion-clock phases |
| [run.py](run.py) | Run all checks and collect source hashes, counts and results |

The atomic input matrix includes control phases with other outcomes; it does
not certify all 1,020 inputs as intended simulation reactions. Detailed
receipts distinguish the intended crossings/conversions from those controls.

- Matthew Cook, [Universality in Elementary Cellular Automata](https://content.wolfram.com/sites/13/2023/02/15-1-1.pdf)
  (2004), §§3.2–4.4: distance definitions, crossing rules, and component conditions.
- Matthew Cook, [A Concrete View of Rule 110 Computation](https://arxiv.org/pdf/0906.3248)
  (2009), §2, pp. 40–41 and Figs. 5–11: propagation around ether regions and
  the local collision diagrams. Page references are printed page numbers.

The S/S′ correction and original binary patterns are credited in
[THIRD_PARTY.md](../THIRD_PARTY.md). No paper PDFs, development figures, or
external source checkouts are needed to run the code in this folder.
