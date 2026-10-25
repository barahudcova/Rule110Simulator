# Ready-word occurrences in the collision database

**The ready detector behaves as intended on every recorded experiment in
this database.** The exhaustive scan found 122 occurrences, each beside the
final C₂ of an intact stationary symbol and the complete consuming leader.
Every recorded consumption experiment has exactly one ready row. No other
source family contains a ready word, and no source has repeated detections.

This is a result about the stored collision corpus. Its construction and
coverage limits are described in [DATABASE.md](DATABASE.md). The corpus is
not proved closed under all interactions reachable from encoded computations.
These results support the ready-language specification but do not alone prove
one ready return per cyclic-tag step for every input.

## Data, language, and method

The scan uses the four exact words from the release's
[`ReadySignature.bits`](../pyca_verifier/ready.py):

```text
P_p = eta c_p eta^2 h,  p in {1,2,5,6}.
```

Here eta is the fourteen-cell ether word, c_p is the C₂ core in phase p,
and h is the first 99 cells of L[2]. The ether gap before h is 28 cells.
P₁, P₅ and P₆ have length 158; P₂ has length 144. The short phase-2 C₂
word is intentional. Readiness requires exactly one occurrence in total
among all four words, including overlaps.

The reference SQLite file has SHA-256
`74f6f7f4961c1603edf498f1e3306604fdefc251d3e091a1428329b6d10b32cd`.
It was opened read-only. The scan:

1. Verifies every word's width/packed-bit hash and both 2,048-cell ether
   guards, plus every source's complete consecutive tick range.
2. Searches every spatial position of all 165,297 distinct stored words with
   independent overlapping `str.find` searches for all four signatures.
3. Compares those positions with the production `ReadyDetector` on every
   word, including negative words. The 8,447,759 source/tick frames reference
   these exact words, so deduplication omits no recorded observation.
4. Expands every positive word back to every source, native tick, and physical
   coordinate where it occurs. It checks complete stationary and leader
   cores, then the actual motion around the detection.

No ready word occurs in pure ether. Since the guards exceed the longest
signature and the builder retains the whole disturbance, extending the
words with their actual ether exteriors cannot add a match at an outer
cropping boundary. The scan does not join different experiments into new rows.

There are also 32 literal positive controls: each of the four signatures at
all eight packed-bit alignments. These exercise all four signatures and
alignments, but are tests of literal recognition rather than reachable collisions.
An independent second scan agreed on the complete set of positive
`(source, tick, phase, position)` witnesses and all production comparisons.

## Counts

| Check | Result |
| --- | ---: |
| Distinct stored words searched | 165,297 |
| Recorded source/tick frames represented | 8,447,759 |
| Stored context words containing a ready word | 10 |
| Ready occurrences / ready source/tick frames | 122 / 122 |
| Different sources with a ready row | 122 |
| Expected consumption sources without a ready row | 0 |
| Sources with multiple ready rows | 0 |
| Unexpected or unclassified ready occurrences | 0 |
| Production/literal matcher disagreements | 0 |

The ten positive database words are large contexts, not ten different ready
signatures. All 122 observed signatures are P₁:

| Ready signature | Recorded occurrences |
| --- | ---: |
| P₁ | 122 |
| P₂ | 0 |
| P₅ | 0 |
| P₆ | 0 |

Thus this corpus positively exercises phase 1 only. The negative scan still
checks for all four words everywhere; the literal controls exercise all four.
Positive collision coverage for phases 2, 5 and 6 must not be inferred.

The positive sources are precisely the six consumption families:

| Source family | Sources | Ready rows |
| --- | ---: | ---: |
| Ordinary leader reading Y | 8 | 8 |
| Ordinary leader reading N | 8 | 8 |
| Prepared short leader reading Y | 8 | 8 |
| Prepared short leader reading N | 8 | 8 |
| Prepared short leader with following raw SL | 30 | 30 |
| Prepared short leader with following raw RL | 60 | 60 |

All other 46 families, comprising 3,524 sources, have no occurrence. These
include free particles, C₂/data and C₂/garbage crossings, ossification,
ossifier/garbage passages, accepted/rejected components, and isolated
raw-leader preparation. This directly checks the concern that a collision
interior could imitate a ready word in one of those recorded situations.

## Checking what each occurrence means

The semantic check does not accept a source-family name as sufficient
evidence. At every hit it verifies:

- A unique complete Y or N packet, with fourteen-cell ether guards. Its last
  C₂ is exactly the C₂ in the ready match. Its symbol agrees with the source
  participant: 61 matches are Y[0], and 61 are N[4].
- The entire expected consuming-leader core, not only its shared 99-cell
  head: 16 matches have ordinary L[2] (314 cells), and 106 have the complete
  prepared short leader (216 cells).
- The full stationary packet and a 118-cell head context remain on their
  free trajectories through the following thirty native ticks. The 28
  detections with earlier history also pass the preceding thirty ticks.
  These are 150 windows and 4,650 stored-row context comparisons.

The prepared short core is obtained independently from a native preparation
using the shipped SC→SL table and an acceptor witness. It is not inferred
from the ready head or copied from a matching database frame. Its SHA-256 is
`a9a824530296c8206a4c8904d77d5f5431c818c52377db62c862b416420d4cb8`.

For both complete leader types, the isolated free orbit was checked at every
tick through tick 210. The head appears exactly at ticks 0,30,…,210, at
positions 0,−8,…,−56, with no shifted or temporal aliases. An exact whole-cone
translation by −56 at tick 210, with compatible periodic ether, closes each
isolated orbit. This certifies that head orbit beyond the finite test horizon
for these two canonical packets.

Thirty `short-read-SL` experiments put the following raw leader seven cells
after the complete prepared-short core. An additional fourteen-cell ether
guard after that core would wrongly reject these valid local matches. The
test checks the complete core and observed head context without imposing
that extra spacing.

For example, `archive/prepared-reads/10` has its sole ready occurrence at
tick 390. The full stationary Y starts at cell 8; the matched final C₂ starts
at 129, and the leader head starts at 174. The C₂ ends at 146, leaving
exactly 28 ether cells. Its stationary anchor is 133, so the head distances
at ticks 360,390,420 are respectively 49,41,33. The middle observation is P₁;
the adjacent observations of that head phase lie above and below the ready
distance band. The corresponding static and head contexts are checked directly.

Ninety-four experiments begin at their ready cut, so earlier rows are not
stored for them. Their forward motion and uniqueness over the recorded
source are checked; the report does not invent missing prehistory.

## Interpretation and remaining coverage

There is no counterexample in this database: no spurious ready hit, no missing
hit in a designated consumption experiment, and no duplicate hit during one
such experiment. Every positive is an undisturbed consuming approach rather
than an accidental substring with an unrelated participant label.

The remaining qualification is specific: the database has no proven global
closure and contains isolated experiments, including historical source joins.
It does not enumerate every legal combination of neighboring collisions,
every program/tape interface, or the finite-observation boundary construction.
The result therefore does not establish exclusion in contexts absent from
the database, nor positive coverage of its unobserved ready phases. The
[encoder report](ENCODER.md) and these checks supply complementary finite
evidence for an eventual invariant-based readiness proof.

## Reproduce and inspect

From the repository root, with Python 3.10 or later and no extra packages:

```sh
python supplementary/ready_database.py --database /path/to/collisions.sqlite3
```

The database stays external and read-only. Generated reports go to
`supplementary/results/ready-database/`, ignored by Git:

- `ready-database-summary.json`: counts, signatures, source/database hashes,
  free-orbit checks, source-family totals, and failures.
- `ready-database-details.json`: every positive pattern identifier, all 122
  source/tick/coordinate witnesses, complete-core checks, and temporal windows.

Use `--output PATH` to change the destination. After reviewing a new run,
`--record` updates the compact versioned
[ready-database-summary.json](ready-database-summary.json). A failed check
returns a nonzero exit status. This optional scan is separate from
`python supplementary/run.py`, which needs no external database and checks the
encoder only. Neither command changes the runtime ready language or decoder.
