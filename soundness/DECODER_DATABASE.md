# Decoder checks against the native collision database

This audit tests the **content reader** used by the release decoder. It checks
the labels and multiplicities emitted for static symbols, moving symbols and
partially ossified symbols. The full decoder also needs a ready occurrence,
an intact program cycle and ossifier boundaries. Most isolated collision
experiments do not contain those structures; invoking the full decoder on
their complete rows would test a different input domain. Full finite
observations are covered by the cyclic-tag campaign.

The database is external to this repository. Its construction and limits are
described in [DATABASE.md](DATABASE.md). The independently specified source
participants are the expected labels. No expected CTS tape is supplied to
either the recognizer or the transducer.

## Reproduce

From the repository root, using Python 3.10 or newer:

```sh
python soundness/decoder_database.py \
  --database /path/to/collisions.sqlite3
```

Only the Python standard library and this checkout are required. SQLite is
opened read-only. Detailed diagnostics, exact failing binary rows, and a
machine-execution cache go to ignored `soundness/results/decoder-database/`.
The script records hashes of the database, decoder modules, pattern catalogues
and audit driver. A nonzero exit status denotes a semantic mismatch, an
independent endpoint failure, or disagreement between the diagnostic and the
actual transducer.

## What is tested

Every distinct stored binary row is scanned by an explicit literal-word
diagnostic. It uses exactly the runtime's frozen vocabulary, canonical
anchors, alias handling, conversion ownership and moving-packet ownership.
It collects coordinates for inspection, so this diagnostic is **not itself a
finite-state implementation** and is not described as running the production
2DFT on all 8,447,759 frames.

The independent expectations are:

| Experiment | Required logical outputs throughout its recorded evolution |
| --- | --- |
| Static Y/N crossed by moving Y/N | Exactly the original static symbol and exactly the original moving symbol |
| Static Y/N crossed by one E-bar or any garbage-pair variant | Exactly the original static symbol; no moving symbol |
| Complete ossifier converting moving Y/N | Exactly one copy of the original symbol across the two sweeps; its classification may transfer from moving to static |
| Ossification with preceding productive/empty garbage, including the V4 extensions | The same exactly-once conversion requirement |
| Ossifier/A-four crossed by garbage, including two garbage pairs | No logical tape symbol |
| Free static Y/N | Exactly the original static symbol |

For the static and conversion families, intact static outputs at the recorded
endpoints are additionally checked by literal matches to the independent
glider catalogue in all seven phases. This checks the imported participant
labels against the actual native Rule 110 endpoint, rather than accepting
the old source-description claim without inspection.

A separate, deterministic phase-stratified selection executes the **unchanged
`LocalContentTransducer.decode`**. It retains all 2,048 ether cells on each
side of each row. Every semantic diagnostic failure is also scheduled for
actual machine execution and saved as an exact source/tick/word replay.

The exhaustive diagnostic omits distant pure ether, retaining at least 148
ether cells at each boundary. The largest primitive's side context is only
32 cells. A pure-ether scan checks that no semantic word can be introduced
by the cut, and full/cropped diagnostic outputs are compared on every
selected actual-machine row. The actual transducer's bounded registers and
endmarker draining operate on the full saved row.

## Domain controls

The complete rows of a prepared leader consuming static tape are included as
**controls**, rather than being declared valid content words at every native
tick. The full decoder normally places that leader at the right boundary
of the content and is invoked at ready times, before the consumption
collision. Its intermediate reaction products are not additional tape data
to be decoded by applying the bare content reader indiscriminately to the
whole collision row.

Accordingly, any nontrivial content-reader output within these reaction
interiors is logged separately. It is not silently counted as a successful
semantic conservation check, and it is not by itself a counterexample to
the full decoder on a ready finite observation. Other isolated raw program,
acceptor/rejector and atomic-particle experiments are likewise identified
as controls where their complete rows need not be legitimate content words.

## Scope

This is a finite regression audit, including the temporal phases of all
stored local collisions. Some of these native experiments also supplied
the recognition catalogue, so this is not wholly independent test data.
It can expose missing descriptions, conflicting labels, duplicate outputs
and errors in canonicalization or ownership. It does not prove closure of
the corpus under all future collisions, reachability of every isolated
source, or preservation under arbitrary compositions of neighbouring
packets. The independent cyclic-tag runs test longer compositions and
complete decoder boundaries.

The compact result receipt is [decoder-database-summary.json](decoder-database-summary.json).

## Recorded result

The completed run used the external database with SHA-256
`74f6f7f4961c1603edf498f1e3306604fdefc251d3e091a1428329b6d10b32cd`.
Its runtime and catalogue hashes are recorded in the receipt. No runtime
encoder, decoder, ready-language or catalogue file was changed.

| Check | Result |
| --- | ---: |
| Distinct rows scanned by the literal/ownership diagnostic | 165,297 |
| Source/tick frames represented by those rows | 8,447,759 |
| Sources with exact static/moving/epsilon conservation contracts | 2,703 |
| Native frames in those exact contracts | 6,971,272 |
| Sources with exactly-once conversion contracts | 144 |
| Native frames in conversion contracts | 309,778 |
| Independent intact-static endpoint checks | 5,188 |
| Actual unchanged 2DFT executions on distinct full guarded rows | 1,068 |
| Full/cropped diagnostic comparisons | 1,068 |
| Semantic mismatches | **0** |
| Independent endpoint failures | **0** |
| Diagnostic/actual 2DFT disagreements | **0** |
| Unexpected control outputs | **0** |

The semantic contracts therefore cover 2,847 experiments and 7,281,050
native source/tick frames. This includes whole-packet crossings, partial
ossification, the productive/empty-garbage conversion extensions and
garbage-only ossifier encounters. The remaining 799 sources are the
consumption or noncontent controls described above. Actual-machine cases
were selected by family and tick residue modulo 30, then deduplicated by
the complete binary row. Identical rows can have several source-family
witnesses; the receipt's per-family machine counts name one witness per
replayed word. Exact agreement includes output **order**, labels, status
and rejection reason, rather than counts alone.

The consuming-leader controls include 3,420 positive row/contract pairs
(29,220 source/tick frames). Each emits only the expected original static
symbol during its approach/early consumption, with no moving output. These
are expected positive controls, not failures. Other noncontent controls
produce no logical tape output. There is no observed exception requiring
a decoder repair in this corpus. The run took 644.08 seconds on the audit
machine; runtime depends on hardware and concurrent work.
