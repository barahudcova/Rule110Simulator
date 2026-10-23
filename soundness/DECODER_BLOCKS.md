# Mixed inputs with proved admissibility

The [block campaign](decoder_blocks.py) complements the all-Y examples and
finite-prefix tests with mixed Y/N inputs whose nonhalting and productivity
conditions hold for all future cyclic-tag steps. It uses the same complete
native runner, independent queue comparison and binary-row recording as the
[structured campaign](DECODER_CTS.md).

## Elementary invariant

Let z be the number of appendants and fix an offset q with `0 <= q < z`.
Suppose the initial tape and every nonempty appendant are concatenations of
z-letter blocks with Y at position q. Suppose also that appendant q is
nonempty and has length at least z, and that the initial tape contains at
least one complete block.

At the start of an aligned program rotation, the tape consists of complete
blocks. The next z reads therefore consume one original block; newly appended
letters cannot replace these reads. At read q, the consumed letter is Y, so
appendant q adds at least one complete block. All additional appendants
preserve the block condition. Thus the tape cannot halt during the rotation,
the rotation is productive, and at its end the tape again consists of at
least as many complete blocks. Induction proves both assumptions forever.
The test driver checks each finite premise directly.

This proves admissibility of the *cyclic-tag inputs*. Correct Rule 110 decoding
of their entire infinite evolutions is still not claimed from finite tests.

## Inputs

Every case requests 24 transitions (25 complete ready rows):

| Case | Initial tape | Appendant list | Block condition |
| --- | --- | --- | --- |
| `block6-sparse` | `(YNNNNY)^3` | `(YNNNNY, empty, empty, empty, empty, empty)` | z=6, q=0; five consecutive empty appendants |
| `block6-n-head` | `(NNNNNY)^3` | `(NNNNNY, empty, empty, empty, empty, NNNNNY)` | z=6, q=5; initial N and first productivity at the last read |
| `block3-unequal` | `(YNNYNY)^3` | `(YNNYNY, empty, YYNYYYYYNYYY)` | z=3, q=0; mixed six/twelve-letter appendants |

All three cases passed: **72 transitions and 75 ready rows**, covering
806,652 native Rule 110 ticks. Every decoded tape and pointer agrees with the
independent reference, and there were no unsupported rows or readiness
anomalies.

| Case | Last native tick | Result |
| --- | ---: | --- |
| `block6-sparse` | 156,534 | 24/24 transitions passed |
| `block6-n-head` | 218,778 | 24/24 transitions passed |
| `block3-unequal` | 431,340 | 24/24 transitions passed |

Here powers in the input table denote ordinary string repetition. Each
nonempty appendant has length divisible by six, and appendant zero is
nonempty. The invariant allows the N values and the empty/unequal appendants;
it does not assume that every read is productive.

## Reproduce

From the repository root, using Python 3.10 or later and only the standard
library:

```sh
python soundness/decoder_blocks.py
```

The [recorded summary](decoder-blocks-summary.json) gives the actual outcomes,
the invariant certificate for each input, and runtime/driver hashes. Exact
binary rows and detailed reports are generated in ignored
`soundness/results/decoder-blocks/`. They can be replayed with
`decoder_replay.py`. Completed cases with identical input, runtime and helper
driver are
reused; `--no-resume` requests a fresh run, and `--record` updates the compact
versioned summary after reviewing the results.
