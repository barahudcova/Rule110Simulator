# Stationary-symbol distances and simulated time

The calculation establishes a uniform bound on the distance between
neighboring surviving stationary tape symbols, conditional on the intended
ordered collision network. It does not yet complete the argument that every
cyclic-tag step takes a uniformly bounded number of Rule 110 updates. The
remaining issue is the wait for the next symbol when it is still entirely
moving. This note summarizes both the established bound and that distinction.

Throughout, the cyclic program C is fixed. Constants may depend on C and the
encoder, but not on the initial tape length or elapsed time. The complexity
under discussion counts native Rule 110 updates, rather than Python running
time or decoder execution time.

## Distance between neighboring stationary symbols

Choose the two facing C2 gliders of adjacent stationary symbols. The older
symbol is on the right, the newer on the left. Let g(t) be the distance
between their phase-normalized anchors. Let B(t) count subsequent passing
particles that have crossed the right endpoint but not yet the left one.
Moving data and invisible garbage both contribute to this count.

Every ordinary passage shifts a C2 anchor seven cells to the right. A
particle that has passed both endpoints therefore makes no net change to
their separation. The exact crossing ledger gives

\[
 g(t)-g(t_0)=7\bigl(B(t)-B(t_0)\bigr).
\]

The creation calculation must include the older symbol's earlier crossing
history. The useful bounded quantity is the **reduced gap**, g(t)-7B(t).
For two consecutively deposited symbols, the local scattering equations give

\[
 21\bigl(g(t)-7B(t)\bigr)
 =84L-\Delta e+434+310d+\kappa_{\rm old}-\kappa_{\rm new},
 \qquad \kappa\in\{-24,60\}.
\]

Here L is the actual short or long ossifier gap in raw 14-cell ether words,
d is the number of cyclic-tag reads separating the productive endpoints,
and Delta e is their moving-particle source-intercept difference. These
quantities are defined in [BIRTH_GAP_BOUNDS.md](BIRTH_GAP_BOUNDS.md).

Admissibility bounds d by 2z-1, where z is the number of appendants; within
one appendant d=0. Enumerating the finite program geometry and its thirty
phases therefore bounds the recurring reduced gap. Initial-to-initial pairs
have reduced gap at most 573. For the junction with the first deposited
symbol, dependence on initial tape length cancels against the initial guard;
only the first productive read and the length modulo five remain to check.
Taking the maximum of these three bounds defines a computable K0(C) with

\[
 g(t)-7B(t)\le K_0(C).
\]

The density and boundary-collision calculation independently gives

\[
 B(t)\le \frac{g(t)}{14}+20.
\]

The allowance 20 includes finite collision collars and active endpoint
reactions. In particular, native reactions last at most 171 ticks, whereas
the source spacing gives at least 305 ticks between successive ideal
encounters at a surviving endpoint. See
[CROSSING_BALANCE.md](CROSSING_BALANCE.md).

Combining the inequalities, rather than assuming a bounded raw birth gap,
gives

\[
 g(t)\le K_0+\tfrac12g(t)+140,
 \qquad \boxed{g(t)\le 2K_0+280.}
\]

The internal span of a complete four-C2 symbol also needs accounting: partial
crossings can change it. Applying the same ledger and density bound to its
three internal gaps gives a span at most 1094 cells. Consequently the distance
between corresponding extreme-C2 references of neighboring symbols is at most

\[
 \boxed{D_C=2K_0(C)+1374.}
\]

These intentionally conservative bounds apply after completed stationary
formation, while both symbols survive and before a consuming leader starts
reading either one. Ordinary passing collisions are included using the
anchor convention and bounded collars. Physical edges during productive
ossification or consumption require the corresponding transient allowance.

## What was checked

The [birth-gap receipt](birth-gap-summary.json) records 119 programs and
72,120 recurring production-boundary cases, plus 1,110 initial lookup entries,
4,440 initial-length extensions, and 2,220 composition variations. There were
no failed identities or bounds. The
[crossing receipt](crossing-balance-summary.json) records all 210 native
passing-phase cases and 55,987 finite ledger checks. The algebraic identities
and finite parameter reduction supply the arbitrary-time argument within the
assumed network; the recorded sample counts check their implementation.

| Program | K0(C) | Facing-C2 bound | Corresponding extreme-C2 bound D_C |
| --- | ---: | ---: | ---: |
| `(YYYYYY)` | 4,193 | 8,666 | 9,760 |
| `(YYYYYY, empty, empty)` | 4,481 | 9,242 | 10,336 |
| Three copies of `YNNNNYYNNNNY` | 24,513 | 49,306 | 50,400 |

These are proven upper estimates in the stated model, not measured typical
spacings. The long ossifier gaps make them much larger than initial spacings.

## Consequence for a linear slowdown

Let T(m) be the Rule 110 time of the m-th ready return. A uniform bound
delta_R <= H_C on each ready-return interval would immediately give

\[
 T(m)=\sum_{j=0}^{m-1}\delta_R(c_j)\le H_C m,
\]

and hence the paper's resource condition with the linear polynomial
Q(s)=H_C s, since m <= |c|+m.

When the next symbol is already stationary, the distance bound is the spatial
ingredient of this argument: program leader separations are bounded for fixed
C, free prepared leaders travel left at speed 4/15, and local processing
involves fixed finite clusters. Passing shifts move the stationary target
toward the approaching leader.

The present calculation does not finish the case in which the next logical
symbol is entirely moving and no stationary pair exists. Knowing its eventual
deposition position, and knowing that deposition precedes consumption, does
not give a uniform bound on the time until deposition. A separate uniform
formation-wait lemma, together with the bounded leader-preparation geometry,
is needed to turn the spatial estimates into a uniform H_C. This remaining
requirement is already identified in
[TIMING_CONDITIONS.md](TIMING_CONDITIONS.md).

For example, if W_C bounds that extra wait, P_C bounds the relevant leader
separation, and A_C covers fixed local processing, preparation, and ready-phase
offsets, an argument establishing

\[
 \delta_R\le W_C+A_C+
       \left\lceil\frac{D_C+P_C}{4/15}\right\rceil=:H_C
\]

would complete the linear-time conclusion. This is the sufficient bound to
prove, not a numerical timing certificate already established by the current
audits. The stationary-distance result itself also retains the agreed
assumption that the full binary evolution realizes the intended ordered
collision network.

## Reports and reproduction

- [Timing conditions](TIMING_CONDITIONS.md): complete statement of the four
  conditions and their scope.
- [Creation and initial-junction bounds](BIRTH_GAP_BOUNDS.md): finite K0(C)
  construction and cancellation of initial-length dependence.
- [Crossings and density](CROSSING_BALANCE.md): bounded reactions and exact
  accounting of arbitrary crossing histories.

The reproduction commands and dependency order are in the
[supplementary index](README.md). No new native simulations were run to write
this summary; its values come from the recorded, previously reproduced audits.
