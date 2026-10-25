# Spacing of passing particles

This audit concerns Cook's left-moving E-bar particles: the four constituents
of a moving data symbol and the particles serving as garbage (invisibles).
The distinction between these roles does not change their binary particle
orbit. This report supplies a finite spacing lemma usable in the conditional
collision-network argument. It does not establish that every encoded global
trajectory has that network decomposition.

The reproducible implementation is [passing_particle_spacing.py](passing_particle_spacing.py).
Its compact receipt is [passing-particle-spacing.json](passing-particle-spacing.json).
The native updates, glider words and phase tables are read from this release;
the encoder and decoder have not been changed.

## Which distance is at least fourteen?

The left edge of a phase-dependent JSON word is not a fixed spatial reference
on a glider. Write `x` for that edge, `p` for its temporal phase and `t` for
native time. The normalization measured from the free orbit is

\[
 e=15x+4t+\eta_E(p),\qquad b(t)=\frac{e-4t}{15}.
\]

For a free particle, `e` is constant and `b(t)` moves uniformly at speed
\(-4/15\). Use the distance between these reference trajectories in a density
argument. The corrections \(\eta_E(p)\) are measured from native free orbits
by the existing soundness helpers, not fitted to an expected decoded tape.

**Finite pair lemma.** Among all ether-compatible isolated pairs whose two
E-bar cores follow their free orbits and whose complete word returns after
30 ticks translated by eight cells to the left,

\[
 b_2(t)-b_1(t)\geq\frac{357}{15}=\frac{119}{5}>14.
\]

The stated fourteen-cell bound is therefore conservative for this class.
It applies across packet boundaries as well as within a packet: the proof
uses only the two phases and the actual intervening binary ether.

A literal word-edge formulation would be false. For example the isolated
concatenation `E[0] E[20]` with no intervening ether tile is an exactly
translating compact pair. Its two canonical word edges approach to seven
cells in some phases, although its reference-trajectory distance is
\(385/15\) cells. This is a coordinate warning, not a counterexample to a
valid encoded computation. The full guarded compact-pair orbit was also
searched in all 165,297 database words; none of its 30 phase words occurred.
That absence is an empirical observation, not a reachability proof.

## Why the pair check is finite

Each canonical E word has an ether-aligned left and right cut. For ordered
neighboring particles with these cuts, the displacement between the two
left cuts is

\[
 d=|E_p|+14k.
\]

There are 30 choices of each phase. The check includes \(k=-3,-2,-1,0,1,2,3\).
All candidates are ordered by positive normalized distance, even if their
canonical word edges coincide or appear in the opposite order. Overlapping
cores are merged cell by cell. None of the overlapping or reversed-cut
candidates has consistent bits. There is therefore no omitted close pair
caused by ordering the word edges incorrectly. For smaller values of \(k\),
positive normalized distance is impossible: the largest core has 35 cells,
and the largest difference of phase corrections is 280.

The displacement congruence follows from the cuts: each word starts with the
same specified ether phase, and its right ether starts at its core length.
An intervening pure ether interval must therefore have length divisible by
14. Another residue would be an additional disturbance, rather than the
free-particle/ether interface covered by this lemma.

For each compatible candidate the script evolves the complete finite input
through 30 ticks with sufficient ether guards for its causal cone. At every
tick it checks the two predicted core words and at tick 30 checks the entire
remaining known light cone against the initial word shifted by eight cells.
The 112-cell guards exceed the 30-tick light-cone radius; all potentially
created disturbance lies inside the checked row. Thus no escaping debris
can be hidden beyond the tested pair endpoints. The exterior half-lines are
ether with the same phase after that translation, giving equality of the
complete infinite row and hence repetition by determinism.
Thus the passing cases describe complete periodic free-pair orbits, not
merely correct endpoints. There are 2,910 passing small-gap pairs. Their
minimum normalized separation is 357/15 cells.

For every one of the 900 phase pairs with \(k=3\), the gap between canonical
cores is at least 14 ether cells throughout the orbit and both particle
words have their full ether guards. Adding any number of complete ether
periods therefore keeps the two radius-one update neighborhoods independent:
the endpoint neighborhoods are translated copies of the checked ones and
the intervening cells remain ether. Each added period increases `e₂−e₁`
by 210. This covers the infinite large-gap tail without testing an arbitrary
cutoff.

The local lemma assumes a neighboring *free-particle* interface of this
form. It does not classify arbitrary collective bound states or collision
interiors as independent E-bar particles. Cook's intended particle/collision
decomposition is what permits its use along a computation.

## Checks on particles actually emitted by the encoder

The script independently repeats 360 acceptor/component native experiments
to obtain the outgoing E-bar trajectories for every P and standard-component
phase. It then applies the release's actual phase tables to all 240 pairs
of consecutive accepted letters:

- first component P or a later standard component;
- all 30 source phases;
- each of YY, YN, NY and NN.

All 30 temporal phases of each resulting eight-particle stream are checked.
Within each data symbol the minimum canonical-word-edge separation is
105 cells. Across the boundary between consecutive accepted symbols it is
161 cells. These checks include the actual packet-to-packet seam rather
than just a free four-particle data word. They do not include a leader or
an empty-appendant transition between the two letters.

There is a second purely combinatorial check: two distinct occurrences of
any guarded words \(\eta E_p\eta\) in *any* binary row have left-cut distance
at least 21. All 900 word pairs and all overlapping offsets are checked.
This stronger-looking literal statement has the additional guard hypothesis;
it cannot be applied to the compact example above during its guardless
phases, nor to a collision interior.

## Use in the gap argument and the remaining premise

For compatible free particles with reference anchors in an interval of
length \(G\), the pair lemma gives

\[
 N_{\mathrm{free}}\leq
 \left\lfloor\frac{5G}{119}\right\rfloor+1
 \leq\left\lfloor\frac{G}{14}\right\rfloor+1.
\]

Near a C₂ crossing, a particle may not follow its free orbit or have any
intact E word. It must be charged to a bounded boundary-collision allowance,
not counted using a nonexistent word. The companion
[crossing balance audit](CROSSING_BALANCE.md) measures the elementary collision
collar and explains the additional isolation/decomposition premise.

Consequently this audit verifies the numerical free-stream density needed
by condition 1, conditional on the intended local particle network. It does
not independently prove that arbitrary-length encoded evolutions contain
only those free streams and the bounded permitted collision neighborhoods.
That is the global/local-isolation hypothesis being delegated to Cook's
collision construction. No conclusion of global closure is recorded in
the receipt.

## Reproduce

From the release root, using Python 3.10 or later:

```sh
python supplementary/passing_particle_spacing.py
```

The optional compact-control search uses the external database:

```sh
python supplementary/passing_particle_spacing.py \
  --database /path/to/collisions.sqlite3
```

Both modes write the compact receipt. The optional database is read-only;
its content hash is recorded. The complete test uses only the standard
library and does not depend on an expected CTS computation or the decoder.
