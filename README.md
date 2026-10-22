# PyCA Rule 110 Visualizer and Verifier

This simulator provides an interactive view of the Turing universality of the
elementary cellular automaton Rule 110. It visualizes how Rule 110 simulates a
wide range of cyclic tag systems, following
[Cook's construction](https://arxiv.org/abs/0906.3248) with the encoding
modifications described in Appendix D of
[Self-replication and Computational Universality](https://arxiv.org/abs/2510.08342).
Simulating a universal cyclic tag system is the basis of
[Cook's proof of Rule 110's Turing universality](https://www.complex-systems.com/abstracts/v15_i01_a01/).
The verifier also decodes Rule 110 configurations and checks that they match
the simulated cyclic tag system.

## How the simulation works

A **cyclic tag system** consists of a finite tape over the symbols `Y` and `N`,
an ordered list of words called **appendants**, and a position in that list.
At each step, it removes the first tape symbol. If that symbol is `Y`, it
appends the current appendant to the end of the tape; if it is `N`, it adds
nothing. The position then advances to the next appendant, wrapping around at
the end of the list. An empty appendant adds nothing, and the computation
halts when the tape becomes empty. This is the notation used in Appendix D of
[Self-replication and Computational Universality](https://arxiv.org/abs/2510.08342).

The intended Rule 110 simulation uses **admissible** cyclic tag systems and
initial tapes:

- The first appendant is nonempty.
- Every nonempty appendant has a length that is a multiple of six. Other
  appendants may be empty, including consecutive empty appendants.
- The dataword remains nonempty throughout the trajectory.
- During each aligned complete pass through the appendant list, at least one
  nonempty appendant is actually appended to the tape. With `z` appendants,
  these passes comprise steps `kz, ..., (k+1)z-1`, starting at step zero.

The appendant-length and spacing conditions come from Cook's construction.
The last condition depends on both the program and its initial tape: having
a nonempty appendant in the list is insufficient if it is always rejected.

For each program and initial tape, an **encoder** builds the initial Rule 110
configuration. The central region represents the tape from right to left, so
the first logical tape symbol is the rightmost encoded symbol. Each `Y` is
represented by four stationary gliders, shown in orange; each `N` by four
stationary gliders, shown in black. A repeating pattern to the right encodes
the appendant list. To the left, a periodic supply of **ossifiers** converts
incoming moving data into stationary tape symbols. The viewer supplies more
program blocks and ossifiers as needed.

The encoder uses a hand-designed binary glider catalogue and phase tables to
implement Cook's construction. Our encoding distinguishes the short leader
**S**, used for an empty appendant following a nonempty appendant, from
**S′**, used for an empty appendant following another empty appendant.
This distinction resolves the failures observed with consecutive empty
appendants represented by repeated **S** components.

When the cyclic tag tape empties, its computation halts. If a complete pass
through the appendant list adds no nonempty word, the spacing assumption fails
and an ossifier may strike stationary tape data. The viewer can display the
resulting Rule 110 dynamics; collision notices pause playback, which can be
resumed with Space.

Rule 110's computation takes place against a periodic background called the
ether. The overview filters out the ether for visibility; press B to show
the raw binary configuration. In the filtered view, stationary `Y` symbols
are orange (`204, 102, 0`), and other structures are black and white.
The PyCA menu, camera controls, and clickable navigation
arrows make it possible to inspect the configuration. Time flows from top to
bottom; once the history fills the window, older rows scroll off the top.

## Installation

Python 3.10 or newer is required. From this directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[visualization]"
```

For headless verification, install with `python -m pip install -e .` instead;
the verifier requires only the Python standard library. On Windows, activate
the environment with `.venv\Scripts\Activate.ps1`.

## Inputs

Set the initial tape with `--tape` and the cyclic program with `--appendants`.
Use `empty` for an empty appendant. The initial appendant index is zero.
Input validation checks the symbol and appendant-length restrictions;
the trajectory conditions above remain assumptions.

## Verification

```sh
pyca-verify --tape YYY --appendants YYYYYY empty empty --multisteps 6
```

This checks six elementary cyclic tag transitions, requiring seven decoded
ready configurations including tick zero. The verifier selects finite program
and ossifier reservoirs, tests readiness after every Rule 110 update, and compares
each decoded dataword and appendant index with an independent cyclic tag
calculation. An incomplete or failed requested prefix returns a nonzero exit
status. Add `--max-ticks N` to cap the time horizon.

Reports are written to `artifacts/ready-times/`; use `--output PATH` to change
the destination. The output includes `report.json`, `ready-times.csv`, and
`decoded-tapes.csv`, with a compressed binary row saved on a decoding failure.

## Visualization

```sh
pyca-visualize --tape YYY --appendants YYYYYY empty empty --multisteps 6
```

With the same arguments, the viewer starts from the verifier's exact fixed
seed and pauses at the sixth ready return. It displays readiness and collision
diagnostics; tape decoding and comparison are performed by `pyca-verify`.
Omit `--multisteps` for playback without a preset ready-return limit, with
reservoir replenishment. The viewer starts paused; press Space to run.
Collision diagnostics can pause playback automatically; Space resumes it.

The menu selects initializations. Time flows from top to bottom, ether is
filtered in the overview, and stationary `Y` symbols are orange. Zooming in
reveals individual binary cells and every native tick within retained history.

| Control | Action |
| --- | --- |
| Space / S | Pause or resume / advance one batch while paused |
| Left / Right | Move along the configuration |
| A / D or clickable arrows | Jump to an offscreen tape symbol |
| Ctrl + wheel / drag | Zoom / pan |
| B / V | Toggle ether filtering / ready-row highlights |
| C / H | Reset camera / toggle help |
| N / R | Restart / choose a random initialization |
| P / Q | Save a screenshot / quit |

The checkout entry points `python verify.py` and `python visualize.py` accept
the same options. Use `--help` for additional options and fixed-horizon runs.

## Encoding and decoding

The encoder places reversed stationary tape data between a left ossifier
reservoir and a right program reservoir. Distinct short leaders handle an
empty appendant following data and an empty appendant following another empty
appendant. A periodic marker identifies appendant zero, including for lists
containing identical appendants.

A row is ready when it contains exactly one occurrence in total among four
fixed patterns: a
stationary C₂ glider followed by 28 ether cells and the common prepared-leader
head. The decoder reads only the current binary row. It recovers the pointer
by counting leaders modulo the list length, then scans stationary data from
right to left and accepted moving data from left to right. Finite catalogues
and bounded ownership rules handle crossings and partial ossification, so a
converting symbol is emitted once. The reference calculation is used for
resource planning and comparison, and never supplies the decoder's output.

The executable reports unsupported rows explicitly. The implementation has
been tested on finite computations; this is not a completeness proof for all
admissible trajectories or a proof of the global local-simulation identity.
The formal observation wrapper in the paper is not materialized by the viewer:
the executable decoder receives a padded binary window.

## References

- Matthew Cook, [Universality in Elementary Cellular Automata](https://www.complex-systems.com/abstracts/v15_i01_a01/) (2004).
- Matthew Cook, [A Concrete View of Rule 110 Computation](https://arxiv.org/abs/0906.3248) (2009).
- Jordan Cotler, Clément Hongler, and Barbora Hudcová, [Self-replication and Computational Universality](https://arxiv.org/abs/2510.08342).

The viewer derives from Vassilis Papadopoulos's
[PyCA](https://github.com/frotaur/PyCA). See [THIRD_PARTY.md](THIRD_PARTY.md)
for sources and acknowledgments for the code and catalogues.
