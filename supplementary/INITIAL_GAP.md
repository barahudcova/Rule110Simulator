# Initial ossifier gap lookup

For a fixed program `C = (alpha_0, ..., alpha_(z-1))`, let `n` be the initial
tape length and `r` the first index where the tape reads `Y` and the selected
appendant is nonempty. No appending has occurred before this read, so `r` is
found by scanning the initial tape. Admissibility gives `r < z`.

The initial gap in the paper, counted in **28-cell ether pieces**, is exactly

$$
\mu'_c = 57n + T_C(r, n \bmod 5).
$$

There are five columns, indexed by `n mod 5`, and one row for each nonempty
appendant. Rows for empty appendants are unused. The table includes the phase
adjustment and depends only on the program and the fixed encoding geometry.

## Connection to the implementation

The current implementation evaluates the equivalent spacing formula when
initializing a seed; it does not load a stored table:

- [`compact_initial_gap_certificate`](../pyca_verifier/spacing_geometry.py#L202)
  finds `r` and computes the initial gap using the phase tables and collision
  calibration. Its `selected_guard_tiles` field, denoted `d` below, counts
  14-cell ether words before the final shift to a ready configuration.
- [`Encoder.initial`](../pyca_verifier/encoder.py#L168) calls this calculation,
  inserts the resulting ether, and applies that shift.

To convert `d` to the paper's puzzle-piece exponent, use

$$
\mu'_c = \frac{d-25-2h}{2},
\qquad h=\begin{cases}0,&r=0,\\1,&r>0.\end{cases}
$$

Here `r = 0` means a `Y` head; otherwise the head is `N`, since `alpha_0` is
nonempty. The offset accounts for the ready initialization and the boundary
of the transition piece. This is not the gap between repeated ossifier groups.

## Generate the table for a program

Run the following Python code from the repository root. For each entry it chooses
a reference tape with first productive read `r` and length in the required
residue class. Subtracting `57*n` gives the table entry. No Rule 110 or cyclic
tag evolution is performed.

```python
from pyca_verifier.encoder import Initialization
from pyca_verifier.spacing_geometry import compact_initial_gap_certificate

appendants = ("YNYYNY", "", "YNNNNY", "")  # Replace with your program.
table = {}
for r, appendant in enumerate(appendants):
    if not appendant:
        continue
    row = []
    for s in range(5):
        n = r + 1 + (s - r - 1) % 5
        tape = "N" * r + "Y" + "N" * (n - r - 1)
        cert = compact_initial_gap_certificate(Initialization(tape, appendants))
        mu = (cert.selected_guard_tiles - 25 - 2 * int(r > 0)) // 2
        row.append(mu - 57 * n)
    table[r] = tuple(row)
print(table)
```

For this program the complete table is:

| `r` | `n mod 5 = 0` | `1` | `2` | `3` | `4` |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 62 | 64 | 61 | 63 | 65 |
| 2 | 446 | 443 | 445 | 447 | 444 |

For example, `NYY` has `n = 3`, `r = 2`, and therefore
`mu' = 57*3 + 447 = 618`. For any supported program, row zero is the same:
`YY` gives `57*2 + 61 = 175`, and `YYY` gives `57*3 + 63 = 234`.
