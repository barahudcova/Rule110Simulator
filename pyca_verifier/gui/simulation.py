"""Binary simulation and phase-aligned reservoir extension, independent of UI."""
from collections import deque
import re
from time import perf_counter
from ..automaton import BitRow, step
from ..encoder import Initialization, make_encoder
from ..patterns import ETHER, GLIDERS, word


class Simulation:
    ticks_per_row = 4
    rows_per_batch = 210
    padding_tiles = 840

    def __init__(self, initialization=Initialization(), width=4500, height=3000):
        if width < 400 or height < 1:
            raise ValueError("World width must be at least 400, height positive")
        self.width, self.height = width, height
        self.initialization = initialization
        self.reset()

    def reset(self):
        self.encoder = make_encoder(self.initialization)
        source, self.center = self.encoder.initial(self.width, self.padding_tiles)
        self.initial_word = source
        self.row = BitRow.from_word(source)
        self.history = deque([(0, self.row)], maxlen=self.height)
        self.display_time = 0

    def _step(self):
        """Evolve one native tick; subclasses may request an early yield."""
        self.row = step(self.row)

    def _store_row(self):
        """Retain the current row once in the bounded display history."""
        if self.history[-1][1].time != self.row.time:
            self.display_time += 1
            self.history.append((self.display_time, self.row))

    def advance(self, *, max_rows=None, time_budget=None):
        """Advance towards the next 840-tick reservoir boundary.

        Without limits this runs one legacy-sized batch. Interactive playback
        can yield between visible rows so keyboard and mouse events stay timely.
        Reservoir decisions still occur only at the original batch boundaries.
        """
        if max_rows is not None and max_rows < 1:
            raise ValueError("max_rows must be positive")
        if time_budget is not None and time_budget <= 0:
            raise ValueError("time_budget must be positive")
        deadline = perf_counter()+time_budget if time_budget is not None else None
        advanced = 0
        batch_ticks = self.rows_per_batch*self.ticks_per_row
        end_tick = (self.row.time//batch_ticks+1)*batch_ticks
        while self.row.time < end_tick:
            if self.row.width < 2*self.ticks_per_row+1:
                raise RuntimeError("No known cells remain; reservoir could not be extended")
            for _ in range(min(self.ticks_per_row,end_tick-self.row.time)):
                if self._step():
                    self._store_row()
                    return
            self._store_row()
            advanced += 1
            if self.row.time < end_tick and (
                (max_rows is not None and advanced >= max_rows)
                or (deadline is not None and perf_counter() >= deadline)
            ):
                return
        self.extend()
        # Native closeups reconstruct the next three ticks from this boundary.
        # Save the post-splice checkpoint, including newly inserted reservoirs,
        # so they never evolve an obsolete pre-extension row.
        self.history[-1] = (self.display_time, self.row)

    def extend(self):
        """Retain the original stable-ossifier gate and leader phase bookkeeping.

        Only phase-aligned ether and outgoing E debris are discarded on the left.
        The original continuation rules prepend O and append program components.
        Origin tracks every splice so stored history never shifts when panning.
        """
        text = self.row.word()
        left = text.find(ETHER)
        if left < 0:
            return
        garbage = [word('E', i) + (ETHER if len(p) <= 20 else '')
                   for i, p in enumerate(GLIDERS['E'])]
        while True:
            if text.startswith(ETHER, left):
                left += len(ETHER)
                continue
            length = next((len(p) for p in garbage if text.startswith(p, left)), 0)
            if length:
                left += length
                continue
            break
        oss_phase = next((i for i in range(3) if text.startswith(word('O', i), left)), None)
        if oss_phase is None:
            return  # A collision has not yet settled; retain the known light cone.
        right = text.rfind(ETHER)
        while right > left and text.startswith(ETHER, right-len(ETHER)):
            right -= len(ETHER)
        if right <= left:
            return
        cropped = text[left:right]
        origin = self.row.origin + left
        self.encoder.oss_phase = oss_phase
        leaders = sum(len(re.findall(word('RL', i), text)) for i in range(30))
        if leaders < 2 or origin+len(cropped)-self.center < round(2.5*self.width):
            # Keep the same compiled encoding when replenishing: a ready
            # encoder's appendant-zero spacing marker belongs to every cycle,
            # including cycles appended after the initial viewport is filled.
            cropped += self.encoder.program()
        ossifiers = sum(len(re.findall(word('O', i), cropped)) for i in range(3))
        if ossifiers < 2 or self.center-origin < round(2.5*self.width):
            prefix = self.encoder.ossifiers(2)
            cropped = prefix + cropped
            origin -= len(prefix)
        padding = ETHER*self.padding_tiles
        seed = BitRow.from_word(padding+cropped+padding, origin-len(padding))
        self.row = BitRow(seed.value, seed.width, seed.origin, self.row.time)
