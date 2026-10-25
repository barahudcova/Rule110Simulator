# Boundary collisions and the crossing ledger

This note verifies the accounting needed for the gap argument. Its setting
is Cook's intended, isolated, order-preserving scattering network. It does
not infer that network from a bare modular phase condition. The companion
source and density audits supply the corresponding local hypotheses.

The reproducible audit is:

```sh
python supplementary/crossing_balance.py
```

The output is `crossing-balance-summary.json`. It uses the release's binary
particles and Rule 110 update, independently of the decoder and ready
recognizers. Production code is not changed.

## What is being measured

For two neighboring static symbols in the ordinary passing stage, before
a consuming leader begins reading either symbol, choose their facing C2s:
the leftmost C2 of the older symbol on the right, and the rightmost C2 of
the newer symbol on the left. Write their normalized stationary anchors
as c_R and c_L and let g=c_R−c_L. Comparing this gap with distances
between other symbol anchors requires a bound on the four-C2 symbol's
internal span. Its unperturbed 111/127-cell width must not be assumed
unchanged during partial crossings; the [birth-gap report](BIRTH_GAP_BOUNDS.md)
handles that additional bound with the same ledger argument.

The local native reaction is

    (e,c,tau) -> (e−171,c+7,tau+24 mod 30),

where e is the E-bar affine trajectory coordinate, c the C2 anchor, and
tau the E-bar phase offset. Thus every ordinary passing particle moves
each stationary endpoint seven cells to the right. Its semantic role
(data or invisible garbage) does not change that displacement.

During a collision the binary C2 core need not be recognizable. The
ledger anchor is continued through that finite collision by assigning its
seven-cell jump to a chosen event instant. This convention is harmless:
comparison with a visible-core position then incurs only a bounded local
error. It is not a claim that the C2 literally jumps in one CA update.

## Condition 2: bounded boundary reactions

Cook 2004, §4.2, p. 29, gives the isolation requirements for the middle:
the absolute C2 spacing is at least his C2 [6] C2, while successive E-bars
must have ether between them. His conclusion is that these passing
collisions do not interfere. The statement is stronger than a congruence
of over distances alone.

The actual source spacing supplies a quantitative bound on simultaneous
boundary reactions. The proof below combines the full native reaction
windows with an independently checked lower bound on successive emitted
particles; it does not equate a first guarded match with the end of a
collision.

The audit enumerates all **210** pairs of C2 and E-bar temporal phases.
For each pair, exactly one of four successive 14-cell ether gaps has the
passing residue. It evolves that exact seed until the outgoing particles
remain individually recognizable for **210 consecutive updates**, a full
joint phase period, and the particles account for every non-ether
fourteen-cell window. Requiring a full period matters: a first outgoing
guarded match can precede later temporary failures of the guard.

All 210 checks passed. The maximum interval is **171 ticks**; the union
of disturbed fourteen-cell windows is contained in **[c−41,c+52)**,
relative to the incoming C2 anchor c. Adding 56 cells to the input
gap delays the encounter by 210 ticks and preserves both phases, so
arbitrarily long compatible approaches reduce to these finite encounters
plus free motion. The finite envelope establishes the bounded spatial
error for these isolated collisions.

A recognition collar can contain free particles as well as interacting
ones. We count the former by spatial density and the latter by the number
of active atomic windows, rather than equating missing guarded matches
with a distinct physical reaction.

The explicit numerical packing argument is as follows. Adjusting the
measured collar for the seven-cell anchor jump gives [c−48,c+52). E cores
have width at most 35, and their normalized position minus the core start
lies in [−28/5,196/15]. A distinguishing fourteen-cell window meeting such
a core therefore places its normalized position within
[c−438/5,c+961/15], safely inside [c−100,c+100]. FIFO order puts free pending
particles between the two enlarged endpoint collars, an interval of length
at most g+200. Their fourteen-cell density bound gives at most
(g+200)/14+1 free pending particles.

For interacting particles, the [emission-source audit](PASSING_SOURCE_SEAMS.md)
checks all data/garbage source interfaces and gives

    Delta_e_source >= 1325.

Before a **fixed surviving C2**, any intervening cyclic-tag read removes
four upstream C2s. Newly deposited symbols are downstream, to its left,
so they do not add upstream crossings. Consequently

    Delta_e_incoming = Delta_e_source + 684 d >= 1325,

where d >= 0 counts intervening reads. This is the necessary incoming
asymptotic-intercept bound; it is stronger than the free-pair density
statement and is established by a separate finite source audit and FIFO
history calculation.

The ideal collision time is tau_j=(e_j−15c_j)/4, with c_j=c_0+7j.
Successive ideal times therefore differ by at least

    (1325−15*7)/4 = 305 ticks.

Across the 210 native reactions, the active window relative to tau lies
in [−421/4,263/4), an interval of **171 ticks**. Since 305 > 171, at most
one such guarded interaction window can be active at a particular C2,
or **two** at the two endpoints. Thus the conservative numerical bound is

    B <= (g+200)/14 + 1 + 2 <= g/14 + 20.

The code hash-checks both companion receipts before using their bounds.
This proves the stated uniform allowance within the intended ordered
collision network. Its application to every encoded binary evolution
retains the agreed Cook scattering/embedding hypothesis.

The bound counts the E/C2 reactions during that ordinary passing stage.
The start of reading either symbol terminates the interval, even if its
particular facing C2 has not yet disappeared. Creation of the left
endpoint supplies its initial anchor through the finite ossification
reaction. It would be incorrect to include an arbitrary leader reaction
inside the same ordinary-passing ledger without treating it separately.

## Condition 3: exact cancellation of crossing histories

For each passing E-bar j, use states 0, 1, and 2 to mean that it has
crossed neither endpoint, the right endpoint only, or both endpoints.
Order preservation permits 0 -> 1 -> 2. Let B(t) count state-1 particles.
It includes the relevant boundary reactions according to the chosen
event convention; a free-particle density estimate adds only the bounded
boundary count above.

For any interval beginning at tau after the two anchors have been
created, before a leader begins consuming either symbol, the exact identity is

    g(t)−g(tau) = 7 [B(t)−B(tau)].

Proof: for each particle the indicator of having crossed the right
endpoint minus the indicator of having crossed the left is precisely
the indicator of state 1. Multiply by seven and sum. Earlier crossings
of both endpoints cancel. Crossings of particles initially between the
endpoints appear as the subtraction of B(tau), not as an accumulating
unrecorded history term. The code also checks all **55,987** allowed
initial/current state assignments for up to six particles.

Particle destruction after it has crossed the left endpoint causes no
problem: keep its completed ledger entry, which has zero net
contribution. Destruction between the two endpoints would invalidate the
argument, but the intended middle has only E/C2 passing reactions there.
Ossification lies to the left of the stationary tape, and the consuming
leader lies at its right boundary. These are necessary encounter-order
assumptions, not conclusions from the indicator identity.

Thus the answer to condition 3 is affirmative in the intended network:
every post-creation increase in this gap is charged to particles that
have passed the older endpoint but not the newer one, up to the fixed
binary boundary convention. It is not necessary to remember the entire
past computation.

## Do not assume an unproved birth-gap bound

The inequality g(t) <= g(tau)+7B(t) is exact for ledger anchors, but alone
does not prove a uniform bound: g(tau) itself could contain old-only
crossings before the newer endpoint was created. The sharper quantity
to bound is **g−7B**, rather than asserting that a calibrated deposition
baseline is already the actual visible gap at birth.

For consecutive accepted data constituents produced d tag reads apart,
the encoder's scattering calculation gives

    21 [g(t)−7B(t)]
      =84L−Delta_e_source+434+310d+kappa_old−kappa_new.

This uses the facing C2 endpoints just defined. Its constant already
includes the 2d invisibles and the newer creating E-bar crossing the
older C2. Other later E-bars belong to B. In particular the remaining
three gliders of a newly forming symbol are ordinary pending particles
until they pass its first deposited C2.

The independent [birth-gap audit](BIRTH_GAP_BOUNDS.md) explains this affine
identity and its uniform source bounds. Combining an upper bound K0 on g−7B with a
density bound B <= g/D + b gives

    g <= K0 + 7g/D + 7b,

and hence a uniform gap bound whenever D>7. With the verified
conservative allowance above, D=14 and b=20 give

    g <= 2 K0 + 280.
At finite collision phases, the bounded spatial envelope is absorbed into b or an additional fixed
constant. This avoids using a uniform actual birth gap as a premise for
the argument that is meant to prove it.

## Sources and scope

Cook's equal-displacement argument is in [2004 §3.2.3, pp. 17–20,
Figure 10](https://content.wolfram.com/sites/13/2023/02/15-1-1.pdf),
with the absolute isolation requirements in §4.2, p. 29.
The corresponding crossing diagram is [2009 Figure 5, p. 42](https://arxiv.org/pdf/0906.3248).

The binary finite checks establish the listed atomic reactions and
envelopes. The indicator proof establishes the stated accounting for any
number of order-preserving crossings. Neither claim establishes that
every encoded CA trajectory realizes only this scattering network.
