# Collision database

The collision database records complete native-time evolutions of isolated
Rule 110 particles, glider clusters, and finite collision experiments. Its
purpose is to make intermediate collision patterns inspectable and searchable,
including patterns that disappear between the simulator's displayed rows.
Each binary word retains separate witnesses describing where and when it
occurred. This report describes the existing database; the ready-pattern
search is reported separately in [READY_DATABASE.md](READY_DATABASE.md).

The database is an **experimental collision corpus**. It has neither a proof
of coverage of all valid encoded computations nor a global reachability
certificate for every selected collision input. These limits matter when
using a search result to support a universal claim.

## Recorded data

The inventory below was checked directly against the SQLite database opened
read-only. [database-inventory.json](database-inventory.json) records its
identity, counts, and the hashes of the original construction/audit receipts.

| Quantity | Value |
| --- | ---: |
| Indexed candidate experiments | 13,060 |
| Selected experiments stored in SQLite | 3,646 |
| Selected source families | 52 |
| Source/tick frames | 8,447,759 |
| Distinct stored binary words | 165,297 |
| Stored word widths | 4,120–7,600 cells |
| Input-core widths | 4–3,484 cells |
| Recorded experiment horizons | 210–3,840 ticks |
| Ether guard on each side | 2,048 cells |
| SQLite file size | 837,115,904 bytes (about 798 MiB) |

Every source includes ticks `0` through its stated horizon, with stride one.
Deduplication stores identical words once; it retains all their source/tick
records. Thus the number of words is smaller than the number of observations.

The selected experiments comprise:

| Source group | Experiments | Included situations |
| --- | ---: | --- |
| Free particles and clusters | 13 | C₂, Y, N, moving E-bar, A⁴, O, L, R, S, P, standard component, acceptor, rejector |
| Elementary and compound collisions | 640 | C₂/E-bar, A⁴/E-bar, prepared-leader reads, accepted/rejected components, leader successions |
| Raw-leader preparation | 120 | Ordinary and short leaders meeting acceptors or rejectors |
| Additional prepared-leader reads | 28 | Ordinary/short consumption of Y or N in further phases |
| One E-bar passing a whole static symbol | 420 | All recorded partial passages through the four C₂s |
| Packet crossings | 2,100 | Static Y/N with moving Y/N or the three garbage-pair variants |
| Whole ossification | 120 | Complete O converting a moving Y or N packet |
| Garbage/ossifier crossings | 180 | A⁴ or O with garbage from Y, N, or an empty appendant |
| Two garbage pairs/ossifier | 1 | An interacting garbage train |
| Compound ossification | 4 | Garbage followed by productive moving data |
| V4-specific extensions | 20 | Productive prefixes and short-empty garbage trains during conversion |

Here E-bar is Cook's left-moving particle, called `E` in the database.
`ETHER` denotes the periodic background. A⁴ is one bundle of four A gliders;
O is the complete four-bundle ossifier. Historical source names use `RL`,
`SL`, `PC`, and `SC` for R, S, P, and a standard component.

## How the words were obtained

The source manifest contains the complete initial `core_bits`, parameters,
source-file hashes, and claimed participant/output descriptions. Candidate
sources were imported from the existing atomic, packet-crossing, ossification,
and leader experiments. The selected cases had the intended local endpoint
according to those experiments; 9,414 exploratory alternatives remain indexed
in the source manifest but were not evolved into this default database.
Their exclusion does not prove that no valid computation could reach them.

For each selected source, the builder places its binary core between ether
half-lines. Each exterior is periodic with the alignment specified by that
source. It allocates enough initial padding for the backward light cone of
every requested capture. A native Rule 110 update discards one unsupported
boundary cell at each end, so no arbitrary finite boundary value can enter
the captured region within the recorded horizon.

At each tick the builder retains the whole disturbance relative to the two
ether exteriors, with 2,048 ether cells on each side. It does not crop out
separate gliders during a collision. Both exteriors are allowed to have
different ether phases. The frame's `origin` is measured relative to the
leftmost cell of its initial `core_bits`; this differs from some coordinates
in the historical endpoint descriptions, which included that experiment's
initial padding.

The schema separates words from witnesses:

- `patterns`: exact width, content hash, and compressed packed binary cells.
- `sources`: input core, family, horizon, source hashes, parameters, and
  situation/endpoint descriptions in `details_json`.
- `frames`: source identifier, native tick, spatial origin, and pattern identifier.

The `situations` view joins these records. Packed cells use little-endian bit
order: the least significant bit is the leftmost spatial cell. The width is
essential for retaining zero-valued cells at the right. A pattern's SHA-256
covers its width as eight little-endian bytes followed by its packed cells,
before zlib compression. A word can therefore have several witnesses and
interpretations without overwriting earlier metadata.

## What has been independently checked

The saved construction and validation receipts report:

- **Native evolution:** 343,025,078 cells checked against a separate literal
  Rule 110 truth-table implementation at generation checkpoints.
- **Saved-data integrity:** every one of the 165,297 word hashes and both
  ether guards checked, along with all 3,646 complete tick ranges; SQLite's
  `quick_check` returned `ok`.
- **Saved temporal consistency:** 10,938 consecutive-row comparisons,
  covering 50,637,387 cells, checked with the independent literal rule.
- **Generator review:** all 8,184 binary input rows of widths 3–12 checked
  for the step operation; 200 reproducibly seeded random cases additionally
  checked 7,673 captured frames, their coordinates, exact ether exteriors,
  and packing round trips. All non-ether fourteen-cell windows were retained
  in these cases.

All recorded checks passed. The report hashes in the inventory identify these
receipts; this is a summary of those saved validations, rather than a claim
that the ready-pattern scanner repeats every construction check.

The 13 isolated free-particle experiments additionally have exact translating
orbit checks over the common 210-tick clock. C₂, Y and N return with displacement
zero; left-moving clusters return shifted by −56 cells; A⁴, O, acceptor and
rejector return shifted by +140 cells. The comparison includes the complete
disturbance and compatible ether exteriors. It therefore certifies each
isolated orbit for arbitrary time, including all its temporal phases. It does
not certify closure of a network of interacting packets.

## Interpretation and coverage limits

Of the stored sources, 3,633 are labelled `local_contract_only`; the remaining
13 are `catalogue_particle_only`. There are no source records carrying a
protected full encoded-computation reachability witness. The database builder
recomputes each input's binary evolution independently of readiness and decoder
matching, but it does not independently reclassify the historical endpoint
claims. Those labels remain witness metadata, not semantic conclusions derived
from a binary substring.

Some leader/program joins come from an earlier encoder and explicitly require
a V4 embedding check. The 20 V4 extensions use geometry derived from V4 joins,
but are still local collision experiments. In particular, an isolated E-bar
can be moving data or garbage according to its surrounding packet and history;
its binary core alone does not fix that role.

A ready-word match consequently establishes an occurrence in the identified
local experiment. Establishing that it is a consuming frontier, or a false
ready signal in an admissible computation, additionally requires the relevant
participant/context evidence. Absence of a ready word from the corpus would
establish only absence from these stored experiments.

To upgrade the corpus to all-time coverage, one needs a finite description
of permitted complete rows that includes every encoded initial configuration
and is preserved by Rule 110. That description must include legal phases,
gap classes and lower bounds, modified S/S′ interfaces, and permitted
simultaneous interactions. Extracting all fixed-width factors from such a
closed description would then cover every reachable observation by induction.
The current records preserve intermediate ticks and large ether guards, but
do not supply that closure certificate. Nor do they enumerate all windows
formed by joining different experiments.

## Using the database with this release

The approximately 798 MiB SQLite file is optional external research data; it
is not copied into this minimal simulator/verifier repository. To search a
copy, run from the repository root:

```sh
python soundness/ready_database.py --database /path/to/collisions.sqlite3
```

The reference database is identified by SHA-256:

```text
74f6f7f4961c1603edf498f1e3306604fdefc251d3e091a1428329b6d10b32cd
```

The original database project also provides a self-contained compressed source
manifest and builder. Rebuilding SQLite from that manifest needs only Python's
standard library; regenerating the manifest itself additionally needs the
historical experiment archives. The source-manifest and frozen-builder hashes
are recorded in [database-inventory.json](database-inventory.json).

## References

- Matthew Cook, [*Universality in Elementary Cellular Automata*](https://content.wolfram.com/sites/13/2023/02/15-1-1.pdf),
  *Complex Systems* **15** (2004), 1–40, §§3.2–4.4: phases, up/over distances,
  crossings, and component collisions.
- Matthew Cook, [*A Concrete View of Rule 110 Computation*](https://arxiv.org/pdf/0906.3248),
  *EPTCS* **1** (2009), 31–55, §2, especially pp. 40–41 and Figs. 5–11:
  propagation of spacing constraints around ether regions and intended local
  reactions. Page references are printed page numbers.

The [encoder verification report](README.md) checks the shipped encoder's
finite source-alignment conditions. That result and the experimental database's
coverage are separate claims.
