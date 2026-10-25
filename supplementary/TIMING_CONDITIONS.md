# Four spacing conditions for the timing argument

This report checks the four quantitative claims in the proposed bound on the
distance between neighboring stationary tape symbols. It uses the released
encoder and binary catalogue. The encoder, decoder and ready language are
unchanged.

The four estimates follow within the intended collision network, with two
important clarifications: separation is measured using phase-normalized
particle references, and the encoder directly bounds `g-7B`, not the raw
birth gap. The finite source calculation supplies the boundary bound needed
to turn this reduced-gap estimate into an actual gap bound.

The setting is Cook's intended, ordered particle/collision network. In
particular, passing particles survive their crossings, ossification occurs
to the left of the stationary tape, and the start of a consuming leader's
read ends the interval during which that symbol is followed. Establishing
this network for every infinite encoded Rule 110 evolution remains the
delegated global invariant.
The reports distinguish that hypothesis from the finite calculations below.

## First: how the decoder recovers the appendant index

The current implementation recognizes a complete intact program cycle,
starting at an unprepared leader for appendant zero and ending **after the
next appendant-zero leader**. The marker before that final leader is part of
the recognized word. It then returns to the first leader of this cycle and
counts raw leaders back towards the consuming prepared leader, modulo the
fixed number `z` of appendants. It includes the selected zero leader and
excludes the consuming prepared leader. If the count is `r`, it emits
`p[(-r) mod z]`.

Thus there are two distinct roles for the program portion retained in the
observation:

- The remaining current rotation connects the consuming leader to a known
  appendant-zero position. Its leaders supply the count.
- The following complete intact rotation, including its final zero leader,
  validates that position using a fixed binary template. Its contents are
  not an extra term in the count.

For example, with five appendants and current index two, the counted leaders
are those for indices three, four, and zero. The count is three, so
`(-3) mod 5 = 2`. The complete cycle beginning at that zero is the witness
that this is indeed a zero position. The current appendant's data may lie
between the prepared leader and the next raw leader; it is not separately
decoded to determine the pointer.

The full cycle is a choice of the implemented anchor recognizer, rather
than a necessity of the modulo arithmetic. A smaller marker recognizer
would require its own uniqueness and collision checks. This report makes
no such decoder change.

Implementation: [program.py](../pyca_verifier/program.py),
`compile_program` and `recognize_program_phase`; the actual finite-state
control is `find-cycle`, `to-anchor`, and `count` in
[program_control.py](../pyca_verifier/program_control.py).

## 1. Fourteen-cell separation: specify the reference position

For a free E-bar particle, let `x` be the left edge of its canonical binary
core, `p` its phase, and `t` the Rule 110 time. The native orbit gives

\[
e=15x+4t+\eta_E(p),\qquad b(t)=(e-4t)/15.
\]

The reference position `b` moves at the constant velocity `-4/15`. Its
distance from another free particle is the appropriate quantity for a
density bound. The left edges of the displayed cores change with phase.

The exhaustive free-pair classification checks 6,300 phase/gap classes,
including overlapping or reversed core cuts. Of 3,600 compatible native
inputs, 2,910 follow the prescribed complete free orbit. Their minimum
reference-position separation is

\[
\Delta b\geq357/15=119/5>14.
\]

The finite search also verifies every interface at three ether periods;
all larger separations follow by inserting more ether. It therefore covers
an infinite family of free pairs, rather than only a chosen finite range
of distances. The lemma does not depend on whether the particles belong
to one packet, different packets, moving data, or garbage.

A literal core-edge assertion would be false: an isolated compact E-bar
pair has phases with core edges only seven cells apart, while its reference
positions remain `385/15` cells apart. This control is not a demonstrated
reachable encoding counterexample.

During a collision there may be no intact E-bar core. The free-pair bound
must not be applied inside that collision. Those particles require the
boundary allowance in condition 2. The connection to an arbitrary encoded
trajectory is the assumed decomposition into the permitted free streams
and collision neighborhoods.

See [PASSING_PARTICLE_SPACING.md](PASSING_PARTICLE_SPACING.md) and its
[receipt](passing-particle-spacing.json). The additional source checks
cover 240 pairs of actually encoded accepted letters: core-edge separations
are at least 105 cells within a packet and 161 across these packet seams.

## 2. Boundary collisions: what the finite check establishes

All 210 incoming C2/E-bar phase pairs in the passing residue class give

\[
(e,c,\tau)\longmapsto(e-171,c+7,\tau+24\bmod30).
\]

The native audit follows each collision until both outgoing words remain
individually recognizable for a full 210-tick joint period. Its measured
transient lasts at most 171 ticks, with all disturbed fourteen-cell windows
inside `[c-41,c+52)` relative to the incoming stationary anchor. Phase
corrections and the seven-cell anchor displacement fit within a conservative
100-cell collar on either side.

These are finite duration and width bounds for the isolated reaction.
They do **not by themselves** prove that at most one such transient is
active at a C2: recognition intervals for successive particles can overlap.
Nor does instantaneous density of currently free particles automatically
bound the incoming asymptotic trajectories of particles at different stages
of upstream collisions.

An additional native source calibration closes this issue for the released
encoder. It checks the interfaces between data and garbage, between successive
garbage emissions, and through ordinary and short leaders. The smallest source
intercept difference is 1,325. For two successive passers emitted `d` reads
apart, their incoming intercept difference at a fixed surviving C2 is

\[
\Delta e_{\rm incoming}=\Delta e_{\rm source}+684d\geq1325.
\]

Indeed, each intervening read removes four upstream C2s, while each crossing
changes the moving intercept by `-171`. Newly deposited symbols are to the
left of the surviving target. In the intended encounter order, an earlier
emitted particle stays ahead of the later consuming leaders and has crossed
the four constituents that each such read removes. Common earlier crossings
cancel. This supplies the needed history argument, rather than assuming that
simultaneous free-word density also bounds successive arrivals.

For incoming intercept `e` and the pre-crossing anchor `c`, let
`tau=(e-15c)/4` be the ideal meeting time. The measured active intervals lie
within `[tau-421/4,tau+263/4)`, a 171-tick interval. The endpoint's seven-cell
advance makes consecutive ideal meeting times differ by at least

\[
\frac{1325-15\cdot7}{4}=305>171.
\]

Thus the active intervals at any one endpoint are disjoint in the intended
scattering network: at most one particle is active there, and at most two at
the facing endpoints of the pair. The same argument gives at most eight if
both complete four-C2 symbols are included in the boundary set.

Free pending particles have reference positions in the gap enlarged by at
most 100 cells at each end. The fourteen-cell density estimate and the two
active particles give

\[
B(t)\leq(g(t)+200)/14+1+2\leq g(t)/14+20.
\]

This is deliberately conservative. See
[CROSSING_BALANCE.md](CROSSING_BALANCE.md) for the phase, duration, and
incoming-source certificates and the composition assumptions.

## 3. Charging excess separation: an exact crossing identity

Choose the facing C2s of two neighboring surviving static symbols: the
leftmost constituent of the older symbol on the right, and the rightmost
constituent of the newer symbol on the left. Let their anchor gap be `g`.
Let `B(t)` count later E-bar particles that have crossed the right endpoint
but not the left endpoint. The interval excludes a consuming leader's read
of either symbol, even if its facing C2 has not disappeared yet. Ordinary
passing collisions are included.

Every crossing shifts an endpoint seven cells to the right. FIFO order
permits the successive states "neither crossed", "right only", and "both".
The difference of the two crossing indicators is exactly the indicator of
"right only". Hence, while both endpoints survive,

\[
g(t)-g(t_0)=7\bigl(B(t)-B(t_0)\bigr).
\]

Particles that crossed both endpoints cancel, regardless of how many such
crossings occurred. Already pending particles at `t0` are included in the
subtracted term. In particular, history before the newer symbol's birth
cannot simply be discarded. The proof holds for any number of crossings;
55,987 finite ledger assignments additionally check its implementation.

An interior disappearance or a different collision would violate the
specified network. This is why the survival/FIFO assumptions are explicit.

## 4. Creation geometry bounds a reduced gap, then the actual gap

The directly bounded quantity is `g-7B`, not the raw gap at birth. The
encoder's source coordinates and native scattering identities give

\[
21\bigl(g(t)-7B(t)\bigr)
 =84L-\Delta e+434+310d+
   \kappa_{\rm old}-\kappa_{\rm new},
\]

where `L` is the actual raw fourteen-cell ossifier gap, `Delta_e` is the
source-intercept difference, `d` is the number of reads between the two
productive endpoints, and each `kappa` is `-24` or `60`. The constant terms
already include the older endpoint's crossings by the `2d` intervening
invisibles and the particle creating the newer endpoint. Later particles
are counted by `B`.

For a fixed program, aligned-rotation productivity gives `d <= 2z-1`.
The source possibilities, all thirty phases, and short/long ossifier
boundaries therefore form a finite enumeration. Boundaries at multiples
of six inside a long appendant use the long gap too. Initial-to-first-deposit
boundaries admit a separate finite reduction: the dependence on initial
tape length cancels against the initial guard, leaving only the first
productive read and the length modulo five. Thus a computable constant
`K0`, depending on the program but not the initial length or elapsed time,
satisfies

\[
g(t)-7B(t)\leq K_0.
\]

The executable arithmetic audit checked 119 programs and 72,120 recurring
source candidates, together with 1,110 initial lookup entries, length
extensions, and composition variations. The proof for unbounded lengths
is the algebraic cancellation; the sampled extensions are checks of its
implementation.

Using the uniform boundary allowance `C_boundary=20` from condition 2,
condition 1 gives

\[
B(t)\leq g(t)/14+C_{\partial}.
\]

Combining the two inequalities yields

\[
g(t)\leq2K_0+14C_{\partial}=2K_0+280.
\]

This includes the gap when the later symbol has completed its stationary
formation, with the older symbol's earlier crossing history included.
It avoids assuming a uniform raw birth-gap bound in order to prove that
same bound. See
[BIRTH_GAP_BOUNDS.md](BIRTH_GAP_BOUNDS.md) and
[birth-gap-summary.json](birth-gap-summary.json) for the full derivation.

If the paper uses the same end-C2 reference for every whole symbol, also
include a bound on its internal span; a perturbed symbol need not have its
unperturbed width. The three internal reduced gaps sum to 127 for Y and 111
for N, as follows from the native whole-packet conversions. Applying the
same ledger and density inequality to those three gaps gives

\[
\text{span}\leq127+\tfrac12\text{span}+3\cdot7\cdot20,
\qquad \text{span}\leq1094.
\]

Consequently `2K0+1374` also bounds the distance between matching end-C2
references of neighboring symbols. This is an intentionally loose bound;
the proof only needs it to be independent of time and initial length.

The numerical collar above is for E-bar/C2 passing. It is not a measured
collar for a productive A4/E-bar conversion or for leader consumption.
Those bounded local transients must be treated separately if a claim is
intended to include physical pattern edges during creation or destruction.

## Scope for the paper

The finite free-pair classification, emission interfaces and crossing
contracts are verified. The crossing ledger, incoming-history cancellation,
and reduced-gap identities extend their consequences to arbitrarily many
steps **within the intended ordered collision network**. This verifies the
four quantitative conditions in that setting, with the corrected reference
positions and birth-gap argument above. The current receipts do not establish
an unconditional global collision invariant.

There is also a separate issue after these four conditions: if the next
logical symbol is still entirely moving, a bound on stationary-symbol gaps
alone does not bound the wait for its deposition. The draft's final
constant-time-per-read conclusion needs that waiting-time argument too.

## Reproduce

From the release root, with Python 3.10 or later and without `-O`:

```sh
python supplementary/passing_particle_spacing.py
python supplementary/passing_source_seams.py
python supplementary/crossing_balance.py
python supplementary/birth_gap_bounds.py --record
```

The scripts use only the standard library. The optional collision-database
search in the first audit is documented separately. These supplemental
checks are distinct from the existing encoder runner `supplementary/run.py`.
