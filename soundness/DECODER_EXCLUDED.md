# Physical diagnosis of the excluded pilot

The preserved pilot uses initial tape `NYYY` and the single appendant
`YNNNNY`. It violates the stated productivity condition at the first read:
with one appendant, reading the initial N already completes an unproductive
program rotation. Its mismatch therefore remains excluded from the admissible
campaign totals. That fact alone does **not** diagnose the mismatch.

An independent local Rule 110 replay now identifies a physical collision:
an incoming A-four bundle reaches an already stationary Y symbol. This is
an unsafe encounter outside the intended ossifier/moving-data process.
The investigation does not infer that encounter merely from inadmissibility.

## Evidence from the saved binary rows

The complete saved checkpoints are ready index 11 at native tick 207,596
and ready index 12 at tick 225,582. The latter is the first recorded
decoder/reference mismatch. The expected next tape is
`NNNYYNNNNYYNNNNYYNNNNYYNNNNY`; the decoder returns
`NNNYYNNNNYYNNNNYNNNNYYNNNNY`, missing one Y.

At index 11 the ordinary content recognizer reports 17 static and 12 moving
symbols. At index 12 it reports 15 static and the same 12 moving symbols.
The intended intervening read removes one N, so the extra loss is in the
static part, specifically its physically leftmost Y. These counts locate
the discrepancy; the following diagnosis uses **literal particle words
and Rule 110 only**, with no decoder or CTS oracle.

At native tick 209,633 the actual binary row contains exactly

```text
A4[2] ETHER^21 Y[2]
```

with the A-four binary core at x=224,714 and the Y core at x=225,018.
Indices `[2]` are zero-based temporal phases in `gliders.json`.
The A-four core is 10 cells wide, so the intervening space is
`225018 - 224714 - 10 = 294 = 21*14` ether cells. The complete Y is intact
and there is only ether between it and the approaching A-four bundle.

The actual 1,220-cell patch `[224480,225700)` equals the isolated pair with
ether on both sides. Rule 110 has radius one, so this input equality
**forces** equality on `[224980,225200)` for the next 500 ticks. That
220-cell band contains the Y cluster and its recognition context. Thus
the first collision is determined by this pair, independently of all
other gliders outside the causal patch.

In this isolated evolution, the first tick with no intact Y word in any
of its seven temporal phases is tick 428, corresponding to native tick
**210,061**. Its original C-two anchors were
`225024, 225069, 225114, 225151`. By relative tick 1,500 the first two no
longer appear there as intact C-two gliders; the last two remain at
`225114,225151`. This demonstrates physical disturbance of the encoded
static symbol, rather than an intact Y being overlooked by the catalogue.

As a separate consistency check, the original checkpoint at tick 207,596
was restricted to its known causal interval `[206714,243486)` and evolved
for 17,986 ticks with unsupported boundary cells discarded. Its final
800 cells `[224700,225500)` agree **exactly** with the saved failure row.
No new long global CA run or viewport-dependent reconstruction is involved.

## Reproduce

The small isolated collision needs only this checkout and Python's standard
library:

```sh
python soundness/decoder_excluded.py
```

To additionally verify provenance against the preserved pilot checkpoints:

```sh
python soundness/decoder_excluded.py \
  --archive soundness/results/decoder-seeded/outside-domain-pilot/ready-rows.jsonl.gz
```

The [collision receipt](decoder-excluded-collision.json) records the seed,
source-row/crop/archive hashes, exact causal intervals, particle snapshots,
and runtime/driver hashes. The original excluded mismatch is retained in
[decoder-excluded-diagnostic.json](decoder-excluded-diagnostic.json).
The runtime is unchanged.

## Conclusion and limits

This pilot demonstrably leaves the intended physical representation
language: a constituent of an ossifier hits static tape. The missing Y
cannot be explained solely as a missing finite word for an otherwise
intact, correctly spaced static symbol. This diagnosis does not establish
which global scheduling choice first made the encounter unavoidable, or
that the productivity violation alone is its cause. It also does not
exclude other omissions on arbitrary corrupted binary rows, nor prove
that no more elaborate reader could recover information outside the
specified representation language. Those stronger claims are unnecessary
for classifying this particular experiment.
