# Structured cyclic-tag decoder tests

This campaign runs the released encoder, native Rule 110 evolution, ready
matcher, and complete binary two-way finite-state decoder together. It uses
the ordinary `run_multisteps` entry point, without modifying the implementation
or supplying missing data to the decoder. The [driver](decoder_cts.py) uses
only Python's standard library; Python 3.10 or later is required.

The [recorded summary](decoder-cts-summary.json) identifies the exact source
files and reports each tested input separately. Detailed reports and every
complete ready row are generated locally in `supplementary/results/decoder-cts/`,
which is ignored by Git.

**All 24 structured cases passed:** 662 verified transitions, 686 independently
checked ready rows, and 9,568,946 native Rule 110 updates. Readiness was checked
at all 9,568,970 observed ticks, including each seed at tick zero. There were
no unsupported ready rows, tape or pointer mismatches, ambiguous ready ticks,
or consecutive ready detections. Every initial seed was ready.

Every observed ready word used C₂ phase 1. All four signatures were searched
at every native tick, but this end-to-end campaign provides no positive
full-decoder examples for ready phases 2, 5, or 6.

The historical repeated-twelve-letter regression passed **40 transitions and
41 ready rows**, through tick **1,417,450**. In particular, both formerly
rejected ready indices, 24 and 30, decoded correctly. The two-empty regression
passed 36 transitions through tick 368,322; three and five consecutive empty
appendants passed 28 and 30 transitions respectively. The two long-horizon
probes passed 60 and 64 transitions. All these comparisons include both the
full tape and the absolute appendant pointer, checked independently.

| Case | Verified transitions | Final native tick |
| --- | ---: | ---: |
| Two consecutive empty appendants | 36 | 368,322 |
| Three consecutive empty appendants | 28 | 258,388 |
| Five consecutive empty appendants | 30 | 225,780 |
| Historical repeated twelve-letter appendant | 40 | 1,417,450 |
| Two identical appendants | 24 | 494,040 |
| Three identical appendants | 24 | 539,490 |
| One all-Y appendant, rapid growth | 24 | 449,820 |
| Long empty-program horizon | 64 | 328,258 |
| Long mixed-payload horizon | 60 | 345,660 |
| Unequal lengths 6/12/18 | 24 | 807,036 |
| Unequal lengths 6/24 with empty appendants | 12 | 240,366 |
| Unequal lengths 24/6 | 12 | 434,028 |
| Initial N, productivity on the next read | 24 | 303,282 |
| Five leading N symbols | 24 | 302,718 |
| Seven leading N symbols | 24 | 164,412 |
| N-only payloads | 24 | 410,256 |
| N-only and Y-rich payloads | 24 | 329,028 |
| Alternating payload values | 28 | 323,710 |
| Long all-Y payload with empty appendants | 12 | 183,960 |
| Y at the end of each six-letter block | 24 | 408,450 |
| Y at the start of each six-letter block | 24 | 408,450 |
| Alternating initial tape | 24 | 332,808 |
| Historical visualization program, extended initial tape | 24 | 250,470 |
| Final empty run followed by the next cycle marker | 28 | 242,764 |

The precise input words and appendant lists are recorded in the summary and
the driver. The historical visualization-program case intentionally extends
its original `NYY` tape with Y symbols, so its entire requested prefix meets
the productivity condition; it does not claim to reproduce the original
inadmissible trajectory.

## What is checked

For each input, an independent literal queue algorithm removes its first
letter, appends the selected appendant only when that letter is Y, and
increments the appendant pointer modulo the program length. It does not import
or call the runtime `CTSState`. Before the Rule 110 run, it checks that the
requested reference prefix stays nonempty and that every complete, aligned
rotation through the appendant list contains a productive read. The final
incomplete rotation is reported separately.

At every ready time, including tick zero, a read-only observer compares both
the decoded tape and the decoded pointer with that independent queue. It
also checks the runner's own CTS reference against the independent one.
The observer cannot influence the CA, readiness, or decoder. The runtime
checks readiness at every native tick. A goal of N transitions requires
N+1 successfully decoded ready rows. An unsupported row, mismatch, ambiguous
ready tick, consecutive ready ticks, or incomplete horizon never passes.

The campaign contains historical regressions, equal appendants that require
the cycle marker to identify the pointer, long sequences of empty appendants,
unequal appendant lengths, both values at the initial tape head, late first
productivity, N-only payloads, and both low and high growth. The longest
requested prefixes have 60 and 64 transitions. The historical repeated
twelve-letter example is checked for 40 transitions, beyond both previously
reported failure indices.

## Admissibility and scope

Every case is syntactically valid: appendant lengths are multiples of six,
empty appendants are allowed, and the first appendant is nonempty. The driver
requires nonhalting and productivity on the *entire requested prefix* before
testing it. It does not infer admissibility of an infinite trajectory from a
finite prefix.

Seven included families additionally have a direct global admissibility
argument. Their initial tape and all nonempty appendants contain only Y,
the initial tape length is at least the number z of appendants, and the total
number of appended letters in each rotation is at least z. Hence all future
letters remain Y, every rotation is productive, and a rotation cannot exhaust
the tape. The per-case summary marks these families explicitly. Apart from
the two block-structured inputs below, the remaining cases make a finite-prefix
claim, including examples with N-only output that would eventually leave the
admissible regime.

Two further mixed-symbol cases have a global block argument, recorded with
their exact blocks in [decoder-cts-block-proofs.json](decoder-cts-block-proofs.json).
They have three nonempty appendants, and both the initial tape and every
appendant are concatenations of three-letter blocks containing Y. Each
appendant contains at least two such blocks. One aligned three-step rotation
consumes exactly one block, hence encounters Y and appends at least two whole
blocks. The block property is preserved and the number of blocks increases;
the tape cannot empty even during the rotation. This proves continuing CTS
productivity and nonhalting for these inputs independently of a finite test.

For the historical example, write B = `YNNNNY`: the initial tape is B³ and
each appendant is B². The three-letter blocks are `YNN` and `NNY`. For the
unequal 6/12/18-letter example, the blocks are `YYY` initially and `YNY`,
`YNN`, or `NNY` in the appendants. Thus nine structured cases have a global
admissibility argument. This establishes an input property; Rule 110
correctness on these inputs is still measured by the recorded finite runs.

Successful trials establish the exact decoded states and pointers on their
recorded ready rows. They do not establish completeness on every reachable
configuration, the whole abstract ready language, or arbitrary simultaneous
collision arrangements. The primitive collision-database audit is a separate
check with a separate scope.

## Reproduce and replay

From the repository root:

```sh
python supplementary/decoder_cts.py
```

The campaign can take considerably longer than the finite encoder checks.
Completed cases with identical driver and runtime hashes are reused, so an
interrupted run can continue using the same command. Use `--no-resume` for a
fresh execution. To inspect or select cases:

```sh
python supplementary/decoder_cts.py --list
python supplementary/decoder_cts.py --cases two-empty repeated-twelve-historical
```

Each case directory contains `result.json`, the ordinary runtime `report.json`,
`decoded.csv`, and `ready-rows.jsonl.gz`. The compressed archive starts with
metadata and then records every complete binary row, its origin and tick,
initial tape, appendant list, expected state, actual decoder event, and binary
hash. A failure also gets its own diagnostic file immediately. These are
actual full decoder inputs, so a repair can be checked without replaying the
whole CA trajectory:

```sh
python supplementary/decoder_cts.py --replay \
  supplementary/results/decoder-cts/two-empty/ready-rows.jsonl.gz
```

After reviewing a full campaign, `--record` updates the small versioned
`decoder-cts-summary.json`. Ordinary runs keep that recorded result unchanged.

During the recorded campaign, three not-yet-started, high-resource probes
were shortened to twelve transitions. Every active or completed native run
kept its original goal. The [driver lineage](decoder-cts-driver-lineage.json)
records the old and current hashes and confirms that the verification logic
is identical after excluding case descriptors. Runtime code was unchanged.
The final summary retains each native receipt's actual producer hash, and
its actual requested and verified transition counts. A deferred helper job
is not a test result and contributes no passing transitions.
