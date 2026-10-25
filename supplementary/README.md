# Supplementary specifications and verification

This folder collects the paper's implementation details, local arguments,
executable checks, and recorded test results. All commands below run from the
repository root with Python 3.10 or later. The checks use the shipped
`pyca_verifier` implementation and require only the standard library.

## Specifications and reports

| Topic | Specification or report | Executable check |
| --- | --- | --- |
| Recurring gap between six-ossifier groups, $\mu$ | [Exact choice, units, examples, and justification](OSSIFIER_GAP.md) | [ossifier_gap.py](ossifier_gap.py) |
| Initial ossifier guard, $\mu'_c$ | [Finite lookup table and encoder correspondence](INITIAL_GAP.md) | Initial-guard cases in [static_ossifier_joins.py](static_ossifier_joins.py), run by `run.py` |
| Encoder components, phases, and reservoir continuation | [Encoder verification](ENCODER.md) | [run.py](run.py) |
| Stationary-symbol distances and the linear-time argument | [Summary and remaining timing lemma](TIMING_SUMMARY.md) | Existing distance and timing audits below |
| Passing-particle separation, boundary collisions, and tape gaps | [Timing conditions and proof scope](TIMING_CONDITIONS.md) | Commands listed below |
| Collision corpus and its coverage | [Database description](DATABASE.md) | Inventory and external database described in the report |
| Ready-pattern occurrences in the corpus | [Ready-language audit](READY_DATABASE.md) | [ready_database.py](ready_database.py) |
| Decoder on collisions and cyclic-tag computations | [Decoder testing and replay](DECODER.md) | Drivers and individual reports linked there |

The recurring gap depends on the program. The initial guard also depends on
the initial tape; the two constants have different definitions. The runtime
calculations remain in [spacing_geometry.py](../pyca_verifier/spacing_geometry.py)
and [encoder.py](../pyca_verifier/encoder.py).

## Reproduce the local checks

```sh
python supplementary/run.py
python supplementary/ossifier_gap.py
```

The first command checks native particle geometry, the finite program grammar,
ossifier conversions, spacing bounds, and source continuation. The second
checks the explicit paper-unit formula for $\mu$ against the encoder, including
the required phase class and the smallest permitted correction.

For the additional timing arguments, run these in order: the boundary check
validates the source hashes in the first two generated receipts.

```sh
python supplementary/passing_particle_spacing.py
python supplementary/passing_source_seams.py
python supplementary/crossing_balance.py
python supplementary/birth_gap_bounds.py --record
```

See [TIMING_CONDITIONS.md](TIMING_CONDITIONS.md) for the individual claims and
their limits. These checks do not run the decoder campaigns. The
[decoder report](DECODER.md) gives short trial commands, larger campaigns,
and binary-row replay instructions. Database checks take an explicit path to
the external collision database, which is not bundled with this repository.

Detailed generated results belong in `supplementary/results/`, ignored by
Git. Compact JSON receipts are kept beside their reports. The timing commands
above refresh their compact receipts; the encoder and gap runners do so only
with `--record`. Do not use Python's `-O` option: the audits use assertions.

## What the evidence establishes

Finite catalogue checks exhaust their stated phase and source-grammar cases.
The spacing arguments are conditional on the intended ordered collision
network and on the stated productivity assumption. Native cyclic-tag trials
test finite trajectories. The collision corpus is not proved closed under
all reachable interactions. These distinctions are recorded in each report;
the folder is not a claim of a complete global simulation proof.

## Recorded results and the folder rename

This folder was previously named `soundness/`. The root-level initial-gap
note has also been moved here. Maintained commands, links, output paths, and
source-distribution rules use the new layout.

Historical JSON receipts and saved binary-row archives retain their original
contents, including `soundness/...` source paths and the hashes of the drivers
used for those runs. Such a path now corresponds to the same relative file
under `supplementary/`; it is a historical identifier, not a current command.
[relocation.json](relocation.json) records the old and new check-file hashes
and identifies changes limited to folder references. Freshly rerun audits
record the new paths and current hashes. Moving a result does not count as
rerunning its experiment, and decoder campaign results have not been relabelled
as new runs.
