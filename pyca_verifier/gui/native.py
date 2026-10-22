"""Native spacetime closeups reconstructed from the retained display rows.

The overview stores one row every four ticks (and extra diagnostic rows).
Only the narrow, known light cone between adjacent checkpoints is evolved;
this never advances the simulation or supplies guessed boundary cells.
"""
from bisect import bisect_right
import numpy as np
import pygame

from ..automaton import BitRow, step


def native_rows(history, left, right, first_tick, last_tick, *, max_gap=4):
    """Yield exact cropped rows, including the ticks between checkpoints.

    The interval is inclusive in time and half-open in space. Missing older
    history and cells outside a checkpoint's known light cone stay unavailable.
    A gap larger than the display cadence is never silently extrapolated.
    """
    checkpoints = [row for _, row in history]
    times = [row.time for row in checkpoints]
    first = max(0, bisect_right(times, first_tick)-1)
    for index in range(first, len(checkpoints)):
        source = checkpoints[index]
        if source.time > last_tick:
            break
        end = min(last_tick, source.time)
        if index+1 < len(checkpoints):
            gap = checkpoints[index+1].time-source.time
            if 0 < gap <= max_gap:
                end = min(last_tick, checkpoints[index+1].time-1)
        if end < first_tick:
            continue
        reach = end-source.time
        lo = max(source.origin, left-reach)
        hi = min(source.origin+source.width, right+reach)
        if hi <= lo:
            continue
        value = (source.value >> (lo-source.origin)) & ((1 << (hi-lo))-1)
        row = BitRow(value, hi-lo, lo, source.time)
        while row.time <= end:
            if row.time >= first_tick:
                yield row
            if row.time == end or row.width < 3:
                break
            row = step(row)


class NativeCloseup:
    """Viewport-only renderer; idle frames reuse the already scaled surface."""

    threshold = 2.0  # Screen pixels per native cell, horizontally and vertically.

    def __init__(self, view):
        self.view = view
        self.active = False
        self.raw = True
        self.fov = None
        self._key = None
        self._frame = None
        self.arrow_rects = {}
        self.arrows = {name: pygame.transform.scale(icon, (32, 32))
                       for name, icon in view.arrows.items()}

    @property
    def height(self):
        return self.view.h*getattr(self.view.simulation, 'ticks_per_row', 4)

    def _timeline(self):
        sim = self.view.simulation
        first_index = max(0, sim.display_time-self.view.h+1)
        return [(index-first_index, row.time) for index, row in sim.history]

    def overview_to_tick(self, y):
        timeline = self._timeline()
        if len(timeline) == 1 and self.view.simulation.display_time == 0 and 0 <= y < 32:
            # The overview repeats its seed stripe for visibility. Every point
            # on that preview denotes tick zero, not a not-yet-simulated tick.
            return timeline[0][1]
        index = max(0, min(len(timeline)-2,
                          bisect_right([item[0] for item in timeline], y)-1))
        start, tick = timeline[index]
        cadence = getattr(self.view.simulation, 'ticks_per_row', 4)
        if index+1 < len(timeline):
            following, next_tick = timeline[index+1]
            cadence = (next_tick-tick)/(following-start)
        return tick+(y-start)*cadence

    def tick_to_overview(self, tick):
        timeline = self._timeline()
        index = max(0, min(len(timeline)-2,
                          bisect_right([item[1] for item in timeline], tick)-1))
        start, first_tick = timeline[index]
        cadence = getattr(self.view.simulation, 'ticks_per_row', 4)
        if index+1 < len(timeline):
            following, next_tick = timeline[index+1]
            cadence = (next_tick-first_tick)/(following-start)
        return start+(tick-first_tick)/cadence

    def sync_camera(self, camera, anchor=None):
        active = camera.zoom >= self.threshold
        if active != self.active:
            anchor = anchor or (camera.size.w/2, camera.size.h/2)
            y = camera.position.y+(anchor[1]-camera.size.h/2)/camera.zoom
            first_tick = self.view.simulation.history[0][1].time
            replacement = (self.overview_to_tick(y)-first_tick if active
                           else self.tick_to_overview(y+first_tick))
            camera.position.y += replacement-y
            self.active = active
            camera.height = self.height if active else self.view.h
            camera.updateFov()
            self.view.dirty = True
            self._key = None
        self.fov = camera.fov.copy() if self.active else None

    def reset_camera(self):
        self.active = False
        self.fov = None
        self._key = None
        self.view.dirty = True

    def render(self, camera, *, include_arrows=True):
        view, sim = self.view, self.view.simulation
        self.fov = camera.fov.copy()
        colors = view.native_ready_colors()
        key = (sim.display_time, id(sim.history[-1][1]), sim.center, self.raw,
               tuple(self.fov), camera.size.size, tuple(sorted(colors.items())),
               include_arrows)
        if key == self._key:
            return self._frame
        fov = self.fov
        pixels = np.zeros((fov.height, fov.width, 3), dtype=np.uint8)
        visible = fov.clip(pygame.Rect(0, 0, view.w, self.height))
        if visible:
            pixels[visible.top-fov.top:visible.bottom-fov.top,
                   visible.left-fov.left:visible.right-fov.left] = 255
            first_tick = sim.history[0][1].time
            first = first_tick+visible.top
            last = min(first_tick+visible.bottom-1, sim.history[-1][1].time)
            start = sim.center-view.w//2
            left, right = start+visible.left, start+visible.right
            context = 0 if self.raw else view.match_context
            for row in native_rows(sim.history, left-context, right+context,
                                   first, last,
                                   max_gap=getattr(sim, 'ticks_per_row', 4)):
                lo, hi = max(left, row.origin), min(right, row.origin+row.width)
                if hi <= lo:
                    continue
                states = view._states_for(row.value, row.width, self.raw)
                line = view.palette[states[lo-row.origin:hi-row.origin]].copy()
                if row.time in colors:
                    line[np.all(line == 255, axis=1)] = colors[row.time]
                pixels[row.time-first_tick-fov.top,
                       lo-start-fov.left:hi-start-fov.left] = line
        small = pygame.surfarray.make_surface(pixels.swapaxes(0, 1))
        self._frame = pygame.transform.scale(small, camera.size.size)
        view.update_targets()
        self.arrow_rects = {
            'left': pygame.Rect(camera.size.w-88, 16, 32, 32),
            'right': pygame.Rect(camera.size.w-48, 16, 32, 32),
        }
        for name, rect in self.arrow_rects.items():
            if include_arrows and name in view.targets:
                self._frame.blit(self.arrows[f'{name}_arrow'], rect)
        self._key = key
        return self._frame
