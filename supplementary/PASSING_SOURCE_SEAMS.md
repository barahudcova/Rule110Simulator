# Absolute spacing of the emitted E-bar stream

The [free-particle spacing report](PASSING_PARTICLE_SPACING.md) bounds two
coexisting free particles. To bound the number of simultaneous encounters at
one stationary C₂, we also need the separation of the *incoming reference
trajectories*, even when the particles undergo upstream crossings at different
times. This report supplies that additional finite source calculation.

Run [passing_source_seams.py](passing_source_seams.py) to reproduce the native
calibrations and the table inequalities. The exact values, witnesses and source
hashes are retained in [passing-source-seams.json](passing-source-seams.json).
No runtime catalogue, encoder, decoder or readiness function is changed.

## Coordinates and the source calculation

For an E-bar particle with canonical core left edge `x`, temporal phase `p`,
and native time `t`, use

\[
 e=15x+4t+\eta_E(p).
\]

This is constant during free travel. Dividing an intercept difference by 15
gives the separation of the corresponding free reference trajectories.
The native C₂ crossing subtracts 171 from `e` and moves C₂ seven cells to the
right, as checked in [CROSSING_BALANCE.md](CROSSING_BALANCE.md).

Use G for an emitted garbage particle and D for a productive moving-data
particle. Every CTS read emits two G particles; a productive nonempty read
then emits four D particles per appended letter. Rejected or empty appendants
emit no D particles. This yields a short exhaustive list of possible
neighboring emission types, regardless of the program's length.

The source values below are measured after a component has produced its
outgoing E particles but before their subsequent crossings of surviving tape
symbols. The particles produced by consumption of the current symbol are
already calibrated *after that consumption*. Its four deleted C₂ gliders must
not be charged to them again.

## Native calibration, including short leaders and approach phases

Normalize the prepared head to its canonical L[2] row. The outgoing garbage
intercepts, minus fifteen times the left edge of that head, are:

| Consuming leader and symbol | First G | Second G |
| --- | ---: | ---: |
| Ordinary, Y | −446 | 4587 |
| Ordinary, N | −446 | 1395 |
| Prepared short, Y or N | −446 | 1731 |

This is not calibrated only at the encoder's initial ready cut. The script
checks all seven phases of each whole Y/N symbol against both ordinary and
prepared short heads. It enumerates four consecutive ether-gap residues and
selects the approach using Cook's over-distance condition 1. All 28 selected
cases evolve to exactly the correct control and two E particles, with no
remaining C₂ or unexplained non-ether region. The intercept table is identical
throughout. Adding four ether tiles changes the approach by 210 ticks, a
multiple of both particle periods; the intercept relative to the initial
leader core is unchanged. Thus the four gap residues cover longer isolated
approaches as well.

For a raw leader whose core starts at `x_R`, let the prepared canonical head
occur at `(x_L,t)`. Its normalization offset is

\[
 \gamma(p)=15(x_L-x_R)+4t.
\]

All 30 raw phases are checked. Ordinary and short raw leaders have the same
phase-indexed values, ranging from 94 to 318. The script verifies 180 native
SC-to-raw preparations, including both acceptor and rejector entries and the
extra four-tile cycle marker. Direct short-leader preparations are checked
in every phase. Adding two ether tiles to a compatible control/leader approach
delays the collision by 30 ticks while the leader moves eight cells left;
`15(−8)+4·30=0`. This explains why the recorded offset is independent of an
arbitrarily longer compatible approach.

The repaired consecutive-empty interfaces are checked explicitly. For each
of the 30 short-leader phases, the script keeps the following raw S or R
frontier, consumes Y and N, and checks both the exact next prepared word and
its absolute source offset. There are 180 such cases after including the
marker variant. **The emitted G pair is also checked to have exactly
(−446,1731) relative to the first prepared head.** Thus this step verifies
both sides of the S/S′ or S/R transition, rather than just recognizing the
next leader's shape.

Finally, 360 native P/standard-component experiments supply the data emission
intercepts used by the table calculation.

## Every neighboring source-particle type

The resulting lower bounds are in intercept units, so divide by 15 for
spatial reference separation:

| Neighboring output particles | Lower bound for `e_next−e_previous` |
| --- | ---: |
| Within a garbage pair | 1841 |
| Data followed by data | 1757 |
| Last garbage followed by first accepted data, GD | 2541 |
| Last accepted data followed by the next read's first garbage, DG | 1885 |
| Last garbage of an empty read followed by the next read's first garbage | **1325** |
| Garbage across a rejected nonempty appendant | at least 39755 |
| Initial prepared L bootstrap, GD | 2541 |
| Initial rejected nonempty appendant, GG | at least 39923 |

The script enumerates every phase of the GD, DG and empty-GG seams directly
through the actual `yn`, `rl`, `sc_sl`, `sl_rl` and `sl_sl` tables. It checks
all 240 adjacent accepted-letter cases for DD. Marker padding can only add
840 to the source intercept difference; omitting it in a lower bound is
conservative. The native calibrations separately include that marker.

A rejected nonempty appendant has at least six letters, hence twelve
components. Every P/standard core has at least 196 cells, the preceding raw
ordinary leader has at least 324 cells, and the trailing program padding has
112 cells. All additional ether counts in the actual tables are nonnegative.
Together with the bounded `gamma` values, these facts give the coarse 39755
bound; any further letters increase it. This is an inequality for arbitrary
admissible appendant lengths, rather than a test limited to length six.
The initial L uses its own width and offset, giving the separate bootstrap
bound. The encoder requires a nonempty first appendant, so no initial
short-leader bootstrap is omitted.

It follows that every neighboring pair in the intended outgoing source stream
has

\[
 \Delta e_{\mathrm{source}}\ge1325.
\]

## Transfer to a fixed surviving C₂

Fix a C₂ that already exists and survives the passage of the particles under
consideration. In Cook's intended FIFO collision network, particles reach it
in source order. Between emission of two successive relevant particles,
`d≥0` complete reads can delete four stationary C₂s each to its right.
Newly deposited tape symbols are created on the other side of this surviving
target; they do not add crossings on this incoming path. All other prior
crossings are common to the two paths and cancel in the difference.

Consequently

\[
 \Delta e_{\mathrm{incoming}}
   =\Delta e_{\mathrm{source}}+171\cdot4d
   =\Delta e_{\mathrm{source}}+684d
   \ge1325.
\]

This is the required bridge from source spacing to incoming trajectories.
It relies on the encounter order and deposition side of the intended
collision network. It does not assume that every pair happens to be visibly
free at the same native instant. If the target is newly created, begin this
argument with particles that reach it after creation; there are no fictitious
crossings of that target before it exists. The separate birth-gap ledger
accounts for its creation.

For successive arrivals at one C₂, each completed passage increases the C₂
anchor by seven. Their ideal encounter times are therefore separated by at
least

\[
 \frac{1325-15\cdot7}{4}=305\text{ ticks}.
\]

The complete guarded collision interval in the native C₂/E audit has length
at most 171 ticks. Thus two such intervals cannot overlap at the same C₂.
There is at most one involved E at each chosen endpoint, or two at the two
endpoints of an inter-symbol gap. With fixed spatial collars this gives the
bounded correction used in [CROSSING_BALANCE.md](CROSSING_BALANCE.md).

These are checked absolute source inequalities plus conditional deductions
inside the intended ordered collision network. They strengthen a residue-only
phase audit. They do not independently prove the global CA trajectory has
that network; that remains the Cook-style simulation invariant being assumed.

## Reproduce

From the release root:

```sh
python supplementary/passing_source_seams.py
```

The check uses Python's standard library and runs in a few seconds. It writes
a compact receipt beside this report. Its source hashes allow the companion
collision audit to reject a stale calibration.
