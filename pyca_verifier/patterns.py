"""Fixed glider words and phase tables, read without mutation.

The program tables implement the encoder's uniform geometric joins; repaired
short-leader joins retain the S/S-prime distinction for empty appendants.
"""
import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data"


def load(name):
    return json.loads((DATA / f"{name}.json").read_text())


GLIDERS = load("gliders")
TABLES = {name: load(f"dict_{name}") for name in
          ("yn", "rl", "sl", "sc_sl", "sl_rl", "sl_sl")}
ETHER = "".join(map(str, GLIDERS["ether"]))


@lru_cache(maxsize=None)
def word(family, phase=0):
    cells = GLIDERS[family] if family == "ether" else GLIDERS[family][phase]
    return "".join(map(str, cells))
