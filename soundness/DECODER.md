# Decoder testing

These campaigns test the decoder shipped in this repository. They use its
unchanged encoder, ready language, binary catalogues and finite transducer.
The expected output is specified independently of the decoder. Runtime source
and catalogue hashes are saved with the results, and the scripts check that
those files remain unchanged during testing.

## Recorded results (23 October 2026)

| Check | Coverage | Discrepancies |
| --- | --- | ---: |
| Exhaustive collision-vocabulary diagnostic | 165,297 distinct stored rows | 0 semantic mismatches |
| Actual finite-state content transducer | 1,068 full guarded rows | 0 mismatches or diagnostic disagreements |
| Independent static endpoint matches | 5,188 endpoints | 0 |
| Initial configurations | 64 six-letter appendants, each with Y and N heads: 128 checks | 0 |
| Structured native trials | 24 inputs; 662 transitions, 686 ready rows | 0 |
| Seeded native trials | 32 inputs; 462 transitions, 494 ready rows | 0 |
| Mixed block-invariant native trials | 3 inputs; 72 transitions, 75 ready rows | 0 |

All **59 distinct tape/program inputs passed**, covering **1,196 transitions**,
**1,255 complete ready rows** and **20,530,454 native Rule 110 updates**. Every
decoded tape and appendant pointer agrees with the independent CTS reference.
There were no unsupported ready rows, ambiguous ready events or consecutive
ready detections, and every requested horizon was reached. The 128 initial-row
checks are additional and are not counted as dynamic trials.

All 1,255 dynamic ready rows matched C₂ phase 1. These runs therefore do not
directly exercise the other three alternatives of the ready language. The
database audit covers additional temporal phases of the content reader;
neither test establishes global ready-language uniqueness.

The historical input `YNNNNYYNNNNYYNNNNY` with three identical appendants
`YNNNNYYNNNNY` passed **40 transitions through tick 1,417,450**. Both the
tape and pointer agree at all 41 ready rows, beyond the older failures at
indices 24 and 30. Its all-time CTS admissibility follows from the
three-letter-block argument in the structured report.

The excluded pilot below is a recorded discrepancy outside the input
hypotheses, with an independently reproduced physical explanation. It is
not included in passing trial counts.

## Collision database

The [database audit](DECODER_DATABASE.md) checks the content reader on labelled
native collision experiments. Its expectations include preservation of a
stationary symbol during a crossing, preservation of the passing moving
symbol, exactly one logical output throughout ossification, and no tape
output for garbage-only ossifier crossings.

An exhaustive literal-vocabulary diagnostic covers all distinct stored rows.
A phase-stratified subset additionally runs the actual two-way finite-state
content transducer, with every diagnostic discrepancy selected for machine
confirmation. These two counts are reported separately. The diagnostic is
an inspection tool; it is not presented as a second finite-state decoder.

Most isolated experiments lack the ready/program/ossifier boundaries required
by the complete decoder. Such a row is tested as a content word only where
its source gives an appropriate semantic contract. A leader consuming tape
is a boundary reaction, so its entire collision interior is not assumed to
be a valid content word. The [database report](DATABASE.md) explains why the
finite corpus does not establish closure under arbitrary future collisions.

## Complete cyclic-tag runs

The [structured campaign](DECODER_CTS.md) targets historical regressions,
repeated appendants, empty runs, unequal lengths, late productivity and
different packet values. The [seeded campaign](DECODER_SEEDED.md) complements
it with reproducibly generated inputs and an initialization matrix. The
[block campaign](DECODER_BLOCKS.md) adds mixed Y/N inputs with a short proof
that their trajectories remain admissible forever.

Each native run checks readiness after every Rule 110 tick. Every ready row,
including the initial row, is fed to the complete binary two-way transducer.
Both the output tape and the appendant pointer are compared with an
independent queue implementation of cyclic tags. An observer saves the
complete binary row and comparison; it supplies no data to the decoder.
Unsupported outputs, wrong symbols, wrong pointers, ambiguous readiness and
unfinished horizons are reported separately from successful trials.

A decoder/reference mismatch is an end-to-end alarm. It may expose a reader
omission or a physical simulation error, so the complete binary input is
preserved before assigning a cause or extending the recognition catalogue.
The excluded pilot below illustrates this distinction.

The inputs must satisfy the nonhalting and productive-rotation assumptions
throughout the tested reference prefix. This is checked before running the
CA. Nine structured inputs also have elementary proofs of these assumptions
for their entire infinite trajectories: seven all-Y families and two mixed
families built from three-letter blocks. All three additional block cases
have such proofs too. The remaining cases
make a finite-prefix claim. Initialization tests check syntactically valid
seeds without asserting that their future computations are admissible.

## Reproduce

From the repository root, with Python 3.10 or newer:

```sh
python soundness/decoder_database.py --database /path/to/collisions.sqlite3
python soundness/decoder_cts.py
python soundness/decoder_seeded.py --workers 2
python soundness/decoder_blocks.py
```

These commands require only the standard library and this checkout. The
database remains external and is opened read-only. Outputs and exact binary
rows go to ignored `soundness/results/`. The full native campaigns can take
hours on a laptop: high-growth cases reserve millions of cells. The individual
reports explain case selection, resuming completed work, and replay. A smaller
targeted campaign check is:

```sh
python soundness/decoder_cts.py --cases two-empty identical-two
```

A quick check of the ordinary checkout entry point is:

```sh
python verify.py --tape YYY --appendants YYYYYY empty empty --multisteps 3 \
  --output soundness/results/decoder-cli-smoke
```

This also passed: four ready rows through tick 24,216, with tape lengths
3, 8, 7, 6 and pointers 0, 1, 2, 0. It is a separate interface check and
is not added to the campaign totals.

Replay a particular ready row from either campaign without rerunning the CA:

```sh
python soundness/decoder_replay.py \
  soundness/results/decoder-cts/two-empty/ready-rows.jsonl.gz --ready-index 10
```

The replay tool verifies the saved binary hash and compares the complete
decoder's tape and pointer with the recorded independent expectation. It
returns a nonzero exit status for a mismatch or a missing requested index.
`--no-memoization` executes without the interpreter's per-run transition
cache. The two-empty case at ready index 10 also passed that uncached check
(tick 105,220, 564,694 finite-machine transitions). The mixed
`block3-unequal` case at index 24 passed it as well (tick 431,340,
1,081,882 transitions), with both Y and N in the output tape.

After generating all three native campaign archives, check their integrity
and independently recompute every expected state:

```sh
python soundness/decoder_receipts.py
```

This [archive checker](decoder_receipts.py) verifies every saved binary hash,
the ordered ready indices, exact requested horizons, runtime hashes, and the
agreement of all recorded decoder outputs with a freshly computed CTS queue.
It also checks that the aggregate counts equal the individual archives. It
does not reexecute the CA or decoder. The completed
[integrity receipt](decoder-archive-integrity.json) records all 59 archive
hashes and the three campaign-summary hashes. Large binary archives remain
in ignored `soundness/results/`; the small reports and receipts are shipped.

## Outside-domain diagnostic

A preliminary run with tape `NYYY` and sole appendant `YNNNNY` reproduces a
tape mismatch at tick **225,582**, ready index **12**, after eleven verified
transitions. The pointer is correct. The expected tape is
`NNNYYNNNNYYNNNNYYNNNNYYNNNNY`; the decoded tape is
`NNNYYNNNNYYNNNNYNNNNYYNNNNY`.

This is a real recorded discrepancy, excluded from the passing campaign
counts. With one appendant, an initial N makes the first aligned rotation
unproductive, so this input violates the encoder's hypothesis immediately.
It is not a counterexample on an admissible computation. Its exact ready
rows, failure row and comparison are retained under
`soundness/results/decoder-seeded/outside-domain-pilot/` for investigation;
the seeded report gives the command to reproduce it. No runtime change was
made to conceal or accommodate the discrepancy.

Replaying the preserved indices 11 and 12 independently reproduces a correct
row followed by this mismatch; the replay tool returns a nonzero exit status.

The [physical diagnosis](DECODER_EXCLUDED.md) goes further: a bounded causal
replay identifies an A⁴ bundle approaching an intact stationary Y at tick
209,633. Its local input equals `A4[2] ETHER^21 Y[2]`; the Y becomes disturbed
at tick 210,061. The replay reproduces the saved failure region exactly.
Thus this case leaves the intended physical tape representation, rather
than merely presenting an intact symbol absent from the recognition catalogue.
The [small isolated-collision check](decoder_excluded.py) needs no external
data or decoder calls. This diagnoses the local encounter; it does not prove
which global scheduling choice caused it.

Successful finite tests support the decoder on the reported observations.
They do not prove completeness on all reachable configurations or all words
of the abstract ready language, and do not supply the global collision
invariant assumed from Cook's construction.
