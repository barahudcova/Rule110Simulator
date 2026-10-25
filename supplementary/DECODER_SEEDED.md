# Deterministic seeded decoder campaign

This complements the structured regressions with newly generated inputs. The
checks run the shipped encoder, native Rule 110 dynamics, ready detector, and
full binary two-way finite transducer. They compare both the decoded tape
and the absolute appendant pointer with a separate CTS implementation in
[`decoder_seeded.py`](decoder_seeded.py).

All 32 selected finite-prefix cases passed: 462 transitions and 494 decoded
ready rows. All 128 separate initialization checks also passed. The excluded
out-of-domain discrepancy is recorded explicitly below.

## Coverage and admissibility

The random seed is `11020261023`. Four parameter families at each program size
from one through eight appendants give 32 cases. Nonempty words have length
6, 12, or 18; families include equal appendants, empty blocks, N-biased words,
Y-biased words, and unequal lengths. The first productive read is deliberately
placed at offsets covering zero through seven. Each input is selected and
recorded before its CA trajectory is run.

Twenty-four cases request 12 transitions and seven request 24. The remaining
case, `seeded-z1-v3`, requests six transitions through an 18-letter appendant.
Its initial 24-transition design allocated 432 ossifiers for produced letters
and a 4,887,986-cell seed; that redundant reservoir dominated runtime. The test
was refined to six transitions (108 produced letters) while the other 31 input
descriptors remained unchanged. Five ready rows of the interrupted original
run, through tick 167,944, were recovered into a separate closed gzip log and
are not counted as a passed 24-transition test. Both driver hashes and the
refinement are recorded in the summary. A second active partial case was also
preserved before the orchestration restart and rerun to its original goal.
Completed receipts for unchanged input descriptors and runtime hashes were
reused. The archived original driver and its hash identify those earlier
executions; the current driver hash identifies the refined harness. The
independent CTS comparison and runtime algorithms are the same in both.
All seven recovered rows of the other interrupted case, `seeded-z2-v1`, agree
byte for byte, including their decoded events, with the completed rerun's first
seven rows.

Preflight executes a separate CTS implementation until the end of the aligned
program rotation containing the final requested transition. It rejects a
candidate if its tape halts or an aligned full rotation produces no nonempty
appendant. Eight candidates were rejected before any CA execution and are not
counted as passing tests. The accepted inputs satisfy this condition throughout
the tested prefix. This finite check does not establish admissibility for an
infinite future trajectory.

A separate initialization matrix runs all 64 binary six-letter appendants with
both a Y and an N initial head, giving 128 direct full-decoder checks of encoded
ready configurations. It tests initialization and syntactic coverage, including
inputs that need not remain admissible during subsequent computation; it is
not counted as 128 dynamic simulations.

## What is compared

The independent reference removes the first tape letter, appends the current
word exactly when that letter is Y, and advances the pointer modulo the fixed
appendant-list length. It does not import the runtime CTS module. At every
native-tick ready event, the completed decoder output is compared against the
corresponding independent reference state. A request for N transitions requires
N+1 successfully decoded ready configurations, including the initial row.

The normal `run_multisteps` API chooses finite source reservoirs from its CTS
resource plan and evolves the CA with exact periodic ether exteriors. Its
`on_ready` hook supplies immutable rows and completed outputs to the recorder;
the recorder's return value has no effect. Neither the independent expected
tape nor its pointer supplies data to the decoder. There are no fallback
symbols, trajectory substitutions, skipped ready events, or alternative
catalogues in these tests.

Every decoded-ready input is saved, including rejected or mismatching decoder
inputs. The test also checks initial
readiness, unsupported outputs, wrong tapes, wrong pointers, ambiguous ready
events, consecutive ready ticks, and failure to reach the requested number of
returns. A tick limit or missing return is inconclusive and cannot pass.

## Reproduce

From the release repository root, using Python 3.10 or later:

```sh
python supplementary/decoder_seeded.py --workers 2
```

Only the standard library is required. Detailed reports, independent expected
states, input manifests, and gzip-compressed complete ready rows are written
under the ignored `supplementary/results/decoder-seeded/` directory. Each row record
includes its case, initial tape, appendants, native tick, origin, width, complete
binary input, ready index, decoder event, and independent expected output.
The full campaign is intentionally a long-running check: some cases allocate
millions of cells. For a quicker targeted run, select a case and omit the
separate initialization matrix:

```sh
python supplementary/decoder_seeded.py --cases seeded-z6-v0 \
  --skip-initialization-matrix
```

Matching completed case receipts are reused when their complete input descriptor
and runtime SHA-256 map agree. Use a different `--output` directory for an
independent rerun. `--cases seeded-z3-v1` selects a particular recorded case.
`--record` updates the small versioned results file after all selected cases
finish; it does not alter any runtime component. The final summary records
whether the complete 32-case and 128-initialization matrix was run.

After generating the logs, replay a particular binary input without rerunning
the CA, optionally using the interpreter without transition memoization:

```sh
python supplementary/decoder_replay.py \
  supplementary/results/decoder-seeded/seeded-z6-v0/ready-rows.jsonl.gz \
  --ready-index 12 --no-memoization
```

## Recorded results

**All 32 selected finite-prefix cases passed.** They verify **462 CTS
transitions**, using **494 complete decoded ready rows** and **10,154,856 native
Rule 110 updates**. Every encoded initial row was ready at tick zero. There
were **no unsupported ready rows, wrong tapes, wrong appendant pointers,
ambiguous ready ticks, or consecutive ready detections**. All 128 separate
initialization checks also passed.

All observed dynamic ready matches use C2 phase 1: `{1: 494}`. This campaign
therefore supplies no additional positive dynamic examples of phases 2, 5, or
6. The distinction matters when interpreting finite coverage.

The versioned [compact results](decoder-seeded-summary.json) store all tested
tapes and appendant lists, per-case outcomes, and source SHA-256 maps. Each
row below denotes an actual completed CA run; no interrupted or deferred
execution is counted as a passed goal. The one out-of-domain discrepancy is
reported separately below.

| Case | Appendant count | First productive offset | Verified transitions | Final native tick |
| --- | ---: | ---: | ---: | ---: |
| `seeded-z1-v0` | 1 | 0 | 12 | 205,464 |
| `seeded-z1-v1` | 1 | 0 | 12 | 205,464 |
| `seeded-z1-v2` | 1 | 0 | 12 | 357,672 |
| `seeded-z1-v3` | 1 | 0 | 6 | 251,916 |
| `seeded-z2-v0` | 2 | 0 | 12 | 234,648 |
| `seeded-z2-v1` | 2 | 1 | 12 | 205,872 |
| `seeded-z2-v2` | 2 | 1 | 12 | 287,820 |
| `seeded-z2-v3` | 2 | 1 | 24 | 880,476 |
| `seeded-z3-v0` | 3 | 0 | 12 | 151,776 |
| `seeded-z3-v1` | 3 | 2 | 12 | 153,348 |
| `seeded-z3-v2` | 3 | 1 | 12 | 260,562 |
| `seeded-z3-v3` | 3 | 2 | 24 | 776,142 |
| `seeded-z4-v0` | 4 | 0 | 12 | 207,030 |
| `seeded-z4-v1` | 4 | 3 | 12 | 169,068 |
| `seeded-z4-v2` | 4 | 2 | 12 | 332,178 |
| `seeded-z4-v3` | 4 | 2 | 24 | 705,054 |
| `seeded-z5-v0` | 5 | 0 | 12 | 179,436 |
| `seeded-z5-v1` | 5 | 4 | 12 | 165,630 |
| `seeded-z5-v2` | 5 | 2 | 12 | 231,456 |
| `seeded-z5-v3` | 5 | 3 | 24 | 568,500 |
| `seeded-z6-v0` | 6 | 0 | 12 | 97,800 |
| `seeded-z6-v1` | 6 | 5 | 12 | 154,086 |
| `seeded-z6-v2` | 6 | 3 | 12 | 267,018 |
| `seeded-z6-v3` | 6 | 3 | 24 | 720,318 |
| `seeded-z7-v0` | 7 | 0 | 12 | 205,806 |
| `seeded-z7-v1` | 7 | 6 | 12 | 152,526 |
| `seeded-z7-v2` | 7 | 3 | 12 | 178,842 |
| `seeded-z7-v3` | 7 | 4 | 24 | 551,712 |
| `seeded-z8-v0` | 8 | 0 | 12 | 290,526 |
| `seeded-z8-v1` | 8 | 7 | 12 | 168,402 |
| `seeded-z8-v2` | 8 | 4 | 12 | 219,726 |
| `seeded-z8-v3` | 8 | 4 | 24 | 618,582 |

## Source and receipt checks

The encoder, ready recognizer, decoder, and all shipped runtime Python/JSON
files remained unchanged throughout the campaign. Disjoint groups ran in
parallel; their 17 copied case folders (51 files) were verified byte for byte
against the original completed receipts and row archives. Canonical summaries
and progress were refreshed from all 32 actual completed receipts after the
parallel work finished. No deferred status remains in those final results.

Sixteen cases were executed by the original test driver and sixteen by its
refined version; the initialization matrix used the original driver. Each
case and matrix receipt retains its actual producer's SHA-256. The aggregate
identifies those producer hashes separately from the current driver's hash.
After native testing finished, a metadata-only change captured the driver hash
at module load, recorded each receipt's producing driver, and made the
completion flag stricter.
AST comparisons establish that the independent CTS function, case generator,
complete observation/comparison callback, native-run calls, and initialization
loops were unchanged. Regenerated descriptors for all 32 cases also agree
exactly. The final aggregation reused completed receipts and performed **zero
additional CA runs**; the audit is included in the compact results.

## Out-of-domain diagnostic

An exploratory pilot, initial tape `NYYY` with the sole appendant `YNNNNY`,
has decoded output disagreeing with the CTS reference at tick **225,582**,
zero-based ready index **12** (the thirteenth ready configuration). The expected
tape is
`NNNYYNNNNYYNNNNYYNNNNYYNNNNY`; the decoder returns
`NNNYYNNNNYYNNNNYNNNNYYNNNNY`, omitting one Y. The pointer is correctly zero.
Eleven preceding transitions agree.

This input violates the stipulated productivity assumption immediately: with
one appendant, the initial N causes a complete rotation to append nothing.
It is therefore excluded from the valid-prefix campaign and provides no
counterexample within that domain. The discrepancy remains explicitly recorded
instead of being silently discarded. Its complete 13 ready rows, runtime report,
independent comparison, and failure snapshot are retained in
`results/decoder-seeded/outside-domain-pilot/`.
The small versioned [`decoder-excluded-diagnostic.json`](decoder-excluded-diagnostic.json)
also preserves the exact discrepancy, first violated condition, and source and
row hashes if generated logs are later removed.
The comparison alone does not establish whether the reader misinterpreted the
actual CA row or the CA dynamics ceased to represent the CTS after the
productivity violation. Assigning a cause requires an independent physical
analysis of that row.
That analysis has now been performed in [DECODER_EXCLUDED.md](DECODER_EXCLUDED.md):
an isolated A-four/static-Y collision witness and a bounded replay of the
actual saved row confirm physical disturbance of the stationary Y.

To reproduce that diagnostic alone without counting it as an admissible test:

```sh
python verify.py --tape NYYY --appendants YNNNNY --multisteps 12 \
  --output supplementary/results/outside-domain-pilot
```

These results concern finite tested inputs and finite observation horizons.
They do not prove decoder completeness on every reachable representation or on
the whole formal ready language.
