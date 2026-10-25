# The recurring ossifier gap

The encoder chooses one fixed gap for each cyclic program. It starts with a
simple count-based value, then increases it, if necessary, until a finite
spacing certificate passes. The gap does not depend on the initial tape,
the viewport, or decisions made during the simulated computation.

The exact rule is

\[
 \mu=\mu_0+7k,\qquad
 \mu_0=4\lfloor\nu/4\rfloor+64,
\]

where \(k\) is the least nonnegative integer for which all the certificate's
lower bounds on the gap between facing stationary \(C_2\) anchors are at
least **573 cells**. Each increment of seven ether pieces increases these
lower bounds by 56 cells and preserves the required phase residue. The
implementation computes the maximum directly rather than trying successive
values of \(k\).

This is the least gap satisfying **this certificate and its inherited
baseline**. It is not a claim that every smaller gap fails in Rule 110.
The certificate assumes the intended ordered collision process; it is not
an independent proof that every full CA trajectory has that process.

## Units and the six-ossifier group

Here \(\mathbb E\) is the fitted right-moving ether puzzle piece with a
28-cell horizontal translation. A complete ossifier is

\[
 \mathbb O=\mathbb A_4\mathbb E^{13}\mathbb A_4
       \mathbb E^{18}\mathbb A_4\mathbb E^{12}\mathbb A_4.
\]

The within-group gap is 89 fitted ether pieces. With

\[
 \mathcal G=\mathbb O(\mathbb E^{89}\mathbb O)^5,
\]

the repeated left reservoir has the symbolic form
\(\cdots\mathbb E^\mu\mathcal G\mathbb E^\mu\mathcal G\).
The separate gap from the initial group to the initial tape is described in
[INITIAL_GAP.md](INITIAL_GAP.md).

The runtime's `long_distance`, denoted \(r\) below, counts raw 14-cell ether
words between phase-dependent catalogue cuts. It includes a different cut
convention from the fitted puzzle pieces. The conversion is

\[
 r=2\mu+1,\qquad \mu=(r-1)/2.
\]

In the native up-distance convention, the corresponding boundary distance
is \(3r+2=6\mu+5\). Thus one more fitted \(\mathbb E\) increases that
distance by six units. The phase-dependent raw joins are checked in
[`ossifier_joins`](static_ossifier_joins.py). In particular, the runtime's
short gap of 179 raw words gives \((179-1)/2=89\) fitted pieces. Simply
dividing `long_distance` by two misses the catalogue-cut correction.

A nonempty appendant emits a multiple of six symbols. Each six-symbol block
uses six ossifiers without waiting for six additional productive CTS reads.
There is therefore no automatic factor of six multiplying the wait between
productive reads. This observation explains the grouping; the finite
certificate below supplies the actual spacing justification.

## Weighted count and baseline

For \(\mathcal C=(\alpha_0,\ldots,\alpha_{z-1})\), let \(n_Y,n_N\) count
the letters in all appendants, and let \(m,e_0\) count nonempty and empty
appendants. We use Cook's weighted count

\[
 \nu=76n_Y+80n_N+60m+43e_0.
\]

The inherited raw gap in
[`_base_ossifier_gap`](../pyca_verifier/encoder.py) is
\(b=8\lfloor\nu/4\rfloor+3\). The encoder retains the lower bound
\(r\ge b+126\), where 126 is its 112-word group margin plus a 14-word
adjustment associated with the program-cycle marker. Converting this bound
to fitted pieces gives exactly \(\mu\ge\mu_0\).

The constant 64 in \(\mu_0\) is this implementation's inherited margin;
it is not a new fundamental constant from Cook's proof. Nevertheless,

\[
 \mu\ge\mu_0=\nu+64-(\nu\bmod4)\ge\nu+61>\nu.
\]

The current encoder does **not** implement \(\mu=6\nu+\delta\). Nor does
the inequality \(\mu>\nu\) alone specify the encoder or guarantee safe
spacing: the phase condition and the certificate must also hold.

## The finite certificate

The assumed productivity condition is at least one productive read in each
aligned rotation of \(z\) CTS reads. Consecutive productive reads can then
be separated by at most \(2z-1\) reads. This condition is an assumption on
the CTS trajectory, not something the initializer proves from the syntax
of the appendants.

The encoder enumerates all 30 raw leader phases, following its actual
phase tables and cycle marker, and considers:

- Every pair of consecutive symbols within an appendant, with \(d=0\).
  This includes the boundaries after multiples of six symbols, where a
  long gap is used. Including the other within-word boundaries is a
  conservative extension of the candidate set.
- The last symbol of a nonempty appendant and the first symbol of a
  nonempty appendant \(d\) reads later, for \(1\le d\le2z-1\).

For each candidate, \(\Delta e\) is the source-intercept difference between
the first constituent moving glider of the later symbol and the last
constituent of the earlier symbol. These are affine trajectory coordinates
of the form \(e=15x+4t+\eta_E(p)\); the phase offsets and component emission
offsets are stored in
[`encoder_geometry.json`](../pyca_verifier/data/encoder_geometry.json).
They are computed from the finite encoded program geometry, without running
the CTS or choosing which appendants will actually be emitted.

Write

\[
 S=\max_{\text{enumerated candidates}}(\Delta e-310d).
\]

In the intended collision network, the completed deposition gap \(g\)
between the facing \(C_2\) anchors satisfies

\[
 21g\ge84r-\Delta e+350+310d
       =168\mu+434-\Delta e+310d.
\]

Consequently the test in the opening paragraph is exactly

\[
 168\mu+434-S\ge21\cdot573.
\]

The target 573 is the chosen 684-cell initial symbol pitch minus the
111-cell normalized span of an N symbol. It is a conservative target of
this encoder, not the smallest collision-compatible separation.
The coefficients account for the accumulated local scattering shifts;
see [BIRTH_GAP_BOUNDS.md](BIRTH_GAP_BOUNDS.md) and
[CROSSING_BALANCE.md](CROSSING_BALANCE.md). The finite source calculation
and raw-gap rounding are implemented in
[`compact_long_gap_certificate`](../pyca_verifier/spacing_geometry.py) and
[`Encoder.__init__`](../pyca_verifier/encoder.py).

Equivalently, a fully explicit specification is

\[
 k=\max\left\{0,\left\lceil
       \frac{21\cdot573+S-434-168\mu_0}{1176}
       \right\rceil\right\},\qquad \mu=\mu_0+7k.
\]

This automatically selects
\(\mu\equiv4\lfloor\nu/4\rfloor+1\pmod7\), the same residue as the
encoder's raw condition \(r\equiv b\pmod{14}\).

## Examples and reproducible check

| Program | \(\nu\) | \(\mu_0\) | \(S\) | \(k\) | Selected \(\mu\) | Raw `long_distance` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| \((Y^6)\) | 516 | 580 | 9989 | 0 | 580 | 1161 |
| \((Y^6,\epsilon,\epsilon)\) | 602 | 664 | 18053 | 0 | 664 | 1329 |
| \((Y^6,N^6,Y^6,N^6)\) | 2112 | 2176 | 369677 | 14 | 2274 | 4549 |
| \((Y^6,Y^6,N^6,N^6)\) | 2112 | 2176 | 371693 | 16 | 2288 | 4577 |

The last two programs have identical weighted counts but different selected
gaps: the program order matters. A counts-only formula would not describe
the current encoder exactly.

From the project root, run:

```sh
python supplementary/ossifier_gap.py
python supplementary/ossifier_gap.py --appendants YYYYYY empty empty
```

The default check uses the existing 119-program corpus plus the two order
examples above. It independently enumerates the candidate maximum and
calculates the selected gap in fitted-piece units, then compares it with
the encoder. It also checks the residue, the clearance bound, \(\mu>\nu\),
and that the previous allowed gap fails the certificate whenever it is
above the inherited baseline. All 121 programs pass. The source geometry
and its calibration are shared with the runtime; this is an arithmetic
agreement check, not an independent rederivation of the local collisions.

Full per-program inputs and results are written to
`supplementary/results/ossifier-gap/report.json`. To refresh the versioned
[receipt](ossifier-gap-summary.json), run with `--record`. No encoder,
ready-language, or decoder behavior is changed by this check. For the
broader scope of the conditional soundness evidence, see
[ENCODER.md](ENCODER.md).
