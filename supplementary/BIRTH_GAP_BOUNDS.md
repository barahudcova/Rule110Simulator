# Gaps when a new stationary symbol is created

The encoder supplies a finite, computable upper bound on a **reduced gap**:
the actual stationary gap minus seven cells for each pending crossing. This
distinction accounts for the older symbol's entire crossing history. Together
with a uniform bound on the number of particles in the interval, it gives a
uniform upper bound on the actual gap once the newer stationary symbol's
conversion has completed, and at subsequent times while the endpoints survive.

These statements are conditional on the intended ordered collision network.
They do not establish that every binary Rule 110 trajectory realizes that
network. The companion [crossing audit](CROSSING_BALANCE.md) supplies the
bounded collision allowance using native source and reaction checks; the
encoder's existing lower-gap certificate alone does not provide it.

## Definitions

Coordinates increase to the right. Consider two consecutive represented
symbols after stationary formation and before a consuming leader begins
reading either symbol. Ordinary E-bar crossings are allowed. This restriction
ends the interval at the start of a read, even if its facing C2 still exists.
The quantitative ordinary-passing collar bound applies after the productive
A⁴/E conversion transient has completed. The affine anchors may be defined
earlier by their outgoing asymptotes; that convention does not identify an
ongoing conversion's binary pattern with an ordinary C₂/E crossing.
The older symbol is on the right and the newer symbol on the left. Let

- `c_old` be the normalized C₂ anchor of the **leftmost** constituent of the
  older symbol, created by that symbol's last accepted moving E-bar particle;
- `c_new` be the normalized C₂ anchor of the **rightmost** constituent of the
  newer symbol, created by that symbol's first accepted moving E-bar particle;
- `g = c_old - c_new`;
- `B(t)` count subsequent E-bar particles which have completed their crossing
  of `c_old` but have not completed their crossing of `c_new`.

The normalized anchors, used by the native calibration, remove the small
phase-dependent motion of the finite binary core. They are not necessarily
the first bit of a particle's displayed word. A comparison with core-start
distances must include this bounded coordinate difference.

For times inside a collision, one can use an anchor before or after the
collision and charge the finite discrepancy to the boundary allowance. The
equalities below concern completed crossings and the resulting asymptotic
anchors; they do not identify a perturbed core as an intact particle.

## Accounting for the older symbol's history

Write `d` for the number of cyclic-tag reads between production of the two
symbols and `Delta_e` for the source-intercept difference between the newer
symbol's first E-bar and the older symbol's last E-bar. The encoder's raw
fourteen-cell ether parameter at their ossifier boundary is `L`. The native
calibration gives

```text
2 * (a_old_source - a_new_source) = 84 L + 116
E-bar passing C2: e -> e - 171, c -> c + 7
invisible E-bar passing A4: a -> a - 175
productive conversion: 21 c = 2 a + e + kappa
kappa in {-24, 60}.
```

The ordered network fixes three differences in completed collision counts:

1. The newer converting E-bar crosses `1 - 4d` more C₂ particles than the
   older converting E-bar. The `+1` includes the older endpoint newly created
   between them; each intervening read removes four stationary constituents.
   Common earlier crossings cancel. This difference can be negative.
2. The newer A⁴ constituent has crossed `2d` more invisible E-bar particles.
   Each intervening read contributes two of these particles.
3. Before the newer endpoint is created, the older endpoint has been crossed
   by those `2d` invisible particles and by the E-bar creating the newer
   endpoint. These contribute `7(2d+1)` to its displacement. Every additional
   later particle contributes to `B(t)` until it crosses the newer endpoint
   as well.

Substitution gives the exact accounting identity

\[
21\bigl(g(t)-7B(t)\bigr)
 =84L-\Delta e+434+310d+\kappa_{\rm old}-\kappa_{\rm new}.
\]

The constants can be checked separately:

\[
116+171+147=434,\qquad
700-684+294=310.
\]

Thus the older symbol's pre-birth history has not been discarded. The
intervening invisible particles and the newer creating particle are already
in the affine expression. Later particles are in `B`, including the remaining
three constituents of the newer moving symbol while they pass its first C₂.
When any such particle subsequently passes both endpoints, its two seven-cell
displacements cancel in the gap.

This accounting uses FIFO encounter order and the fact that a passing particle
cannot disappear between the surviving endpoints: the ossifier region is to
their left, and a consuming leader would end the lifetime of the relevant
endpoint. It cannot be inferred from phase residues alone.

## A finite bound for each fixed cyclic tag system

Admissibility means that each aligned rotation of the `z` appendants has a
productive read. Consequently consecutive productive reads differ by at most
`2z-1`. Consecutive produced symbols either belong to one appendant (`d=0`),
or to such a pair of productive reads.

For a fixed program, enumerate all thirty raw-leader phases, all within-word
symbol boundaries and all pairs of nonempty appendant endpoints with
`1 <= d <= 2z-1`. The actual phase tables compute each `Delta_e`. For a
within-word boundary, use the long ossifier gap when the later symbol's
zero-based index is divisible by six, and the short gap otherwise. Between
appendants, use the long gap. This matters for appendants longer than six:
they include boundaries between different six-ossifier groups.

Define

\[
K_{\mathcal C}^{\rm recurring}
 =\max \frac{84L-\Delta e+518+310d}{21}.
\]

The `518` is `434 + 84`, where 84 bounds the difference of the two kappas.
Independent kappa extrema may overestimate what a phase-compatible pair can
realize; this is harmless for an upper bound. The enumeration is finite and
contains every permitted pair under the stated productivity and encounter
assumptions. Therefore it proves

\[
g(t)-7B(t)\leq K_{\mathcal C}^{\rm recurring}
\]

for arbitrary later appearances of such an adjacent pair, not just the
finite trajectories used in testing. The script implements this per-program
construction; the recorded sample programs test that implementation.

## Initial tape and first deposition

The initial tape pitch is 684 cells. The normalized span of a symbol is 127
cells for Y and 111 for N. Thus adjacent initial symbols have boundary gap
557 or 573, and their initial reduced gap is at most 573.

There is a separate junction between the leftmost surviving initial symbol
and the first deposited symbol. Let `n` be the initial length and `r` the
first productive read; admissibility gives `r < z`. The first converting
particle crosses `4(n-r-1)` surviving initial constituents, the relevant A⁴
has crossed `2(r+1)` invisible particles, and the old initial endpoint has
been passed by those invisible particles and the first converting particle.
The same cancellation gives

\[
21(g-7B)=C(n,r)+84D+60-\kappa_{\rm new},
\]

where `D` is `selected_guard_tiles` and `C` is exactly the intermediate
`constant` in `compact_initial_gap_certificate`. If the last initial symbol
has already been consumed, this mixed stationary pair does not exist; the
formula is used as a calibration, not as a claim that an absent symbol survives.

The apparent dependence on an arbitrarily long initial tape cancels. At a
fixed `r`, adding one initial symbol increases the source position by 684
cells. The constant therefore changes by

\[
-15\cdot684+684=-9576=-84\cdot114.
\]

The initial guard grows by 114 raw ether tiles per added symbol, apart from
its bounded rounding. Composition does not affect this calculation: the
initial pitch is constant and Y/N have the same first C₂ anchor in each
selected phase. The phase is fixed by whether `r=0` or `r>0`.

For a fully finite bound, enumerate every possible `r` and each of the five
residues of `n mod 5`. Choose the smallest `n0 >= r+1` in that residue and
evaluate the implemented formula there. For `n=n0+5q`, the target rounding
residue modulo ten is unchanged, the unrounded guard increases by `570q`,
and the fixed minimum-guard floor can only reduce the resulting reduced gap.
In particular

\[
D(n_0+5q)\leq D(n_0)+570q,
\qquad C(n_0+5q,r)=C(n_0,r)-84\cdot570q.
\]

The finite maximum of `(C(n0,r)+84D(n0)+84)/21` therefore bounds the mixed
initial/first-deposit reduced gap for **all** initial lengths and compositions
with the specified first productive read. No unbounded crossing-history term
remains in this reduction.

## From a reduced-gap bound to an actual birth-gap bound

Take `K0` to be the maximum of 573 and the two finite bounds above. Suppose
the particle-density/boundary argument supplies a constant `C_boundary`
such that, while the two endpoints survive,

\[
B(t)\leq g(t)/14+C_{\rm boundary}.
\]

Then

\[
g(t)\leq K_0+7B(t)
       \leq K_0+\tfrac12g(t)+7C_{\rm boundary},
\qquad
g(t)\leq2K_0+14C_{\rm boundary}.
\]

This applies at the first completed stationary representation of the newer
symbol, including the older endpoint's crossing history, and continues while
both survive. If the
stronger 21-cell density bound is applicable with the same definition of the
boundary allowance, replace the last bound by
`g <= (3/2) K0 + (21/2) C_boundary`.

The companion [crossing audit](CROSSING_BALANCE.md) establishes the conservative
choice `C_boundary = 20`, under the intended collision network. Its source
calibration bounds incoming intercept separations at a surviving C₂; this
ensures that successive transient intervals at that C₂ do not overlap.
Instantaneous free-particle density alone would not establish that fact.
Combining the two certificates gives

\[
g(t)\leq 2K_0+280.
\]

Here "birth gap" means the gap at completed formation of the new stationary
representation. The 100-cell collars and `C_boundary = 20` concern ordinary
E/C₂ passages. They have not been asserted for the distinct productive A⁴/E
conversion. A bound for a picture cut inside that conversion requires its
own finite spatial allowance, even though the outgoing-anchor accounting is
already defined there.

The script here computes `K0` independently of the companion bound. The case
in which no stationary symbol remains, so that the next symbol is still
entirely moving, also needs a separate waiting-time argument; there are no two
stationary endpoints to which this gap identity can be applied.

## Reference positions for whole four-C₂ symbols

A fixed reference C₂ of a whole symbol differs from the facing endpoint used
above by the span of some or all of that symbol. This span is also uniformly
bounded, even while particles pass through the symbol. One must not assume
that its instantaneous width is always the unperturbed width.

In deposition order, from right to left, the three differences between the
source A⁴ anchors inside one ossifier are

\[
(1108,1612,1192).
\]

The corresponding differences between the four accepted E-bar source
intercepts are `(1757,2597,1757)` for Y and `(1757,2933,1757)` for N. All four
conversions have the same kappa: the native whole-packet audit verifies this
for 120 productive phase contexts. There are no intervening invisible
particles between these four constituents. Thus, for consecutive internal
anchors, the reduced gap is

\[
g_i-7B_i=\frac{2\Delta a_i-\Delta e_i+318}{21}.
\]

This yields `(37,45,45)` for Y and `(37,29,45)` for N, in right-to-left order.
Their sums are 127 and 111. The native source identities are checked in
`program_joins.absolute_packets`; whole-packet conversions and kappa equality
are checked in `static_ossifier_joins.native_ossifications`.

Let `S` be the current span of a surviving complete symbol. Summing the three
internal gap bounds and applying the same density allowance to each gives

\[
S\leq127+7\sum_{i=1}^{3}B_i
 \leq127+\tfrac12S+7\cdot3\cdot20,
\qquad S\leq1094.
\]

This is conservative; the finite native conversion templates have much
smaller spans. The estimate includes later crossing histories. Choosing the
same extreme C₂ as the reference for every symbol changes the distance between
two consecutive symbol references by at most one such span. Accordingly

\[
\text{distance between corresponding extreme references}
 \leq 2K_0+280+1094=2K_0+1374.
\]

Other reference conventions need their own bounded offset, for example the
sum of two spans if unrelated points are chosen in the two symbols. This
statement concerns surviving symbols and ordinary passing collisions; the
finite consumption/creation transients must be treated with their specified
event conventions.

## Checks and reproduction

Run from the repository root:

```bash
python supplementary/birth_gap_bounds.py --record
python supplementary/birth_gap_bounds.py --appendants YYYYYY empty empty
```

The first command checks every six-letter appendant and all distinct programs
from the recorded decoder campaigns. The second prints the complete table
for a chosen program. These are arithmetic checks; they do not rerun those
native campaigns.

The [recorded receipt](birth-gap-summary.json) reports:

- 119 distinct programs;
- 72,120 recurring source-boundary candidates, including all thirty phases;
- 1,110 initial lookup entries;
- 4,440 larger-length checks, including extensions by 1,000 symbols;
- 2,220 checks varying the suffix composition;
- no failed identities or bounds.

Examples of the resulting conservative `K0` values, in normalized cells:

| Program | `K0` |
| --- | ---: |
| `(YYYYYY)` | 4,193 |
| `(YYYYYY, empty, empty)` | 4,481 |
| Three copies of `YNNNNYYNNNNY` | 24,513 |
| `(YNNYNY, empty, YYNYYYYYNYYY)` | 12,801 |

The mixed initial/first-deposit reduced bound was 613 cells for every recorded
program. The much larger recurring constants come from the deliberately large
inter-group ossifier gaps. They depend on the fixed cyclic tag system, not on
the initial tape length or elapsed simulation time.

The reusable proof is the finite enumeration and the length-cancellation
argument, conditional on the specified collision accounting. The 119-program
receipt alone would be only a finite test and is not presented as a proof for
all programs.
