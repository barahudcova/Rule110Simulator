"""PyCA spacetime flowing top to bottom, with cached rows and fixed arrows."""
from pathlib import Path
from bisect import bisect_left, bisect_right
from functools import lru_cache
import numpy as np
import pygame
from .representation import PyCARepresentation, unpack
from .simulation import Simulation
from .native import NativeCloseup
from .interface.graphics import arrow_surface

ASSETS = Path(__file__).parent / 'interface' / 'assets'


class Rule110View:
    # Ether and zero cells are white. Only Y gets an accent color.
    palette = np.array([(255,255,255), (0,0,0), (255,255,255),
                        (255,255,255), (0,0,0), (204,102,0)], dtype=np.uint8)

    def __init__(self, simulation: Simulation):
        self.simulation = simulation
        self.w, self.h = simulation.width, simulation.height
        self.representation = PyCARepresentation()
        rep = self.representation
        # Context covers both the cells needed to recognize a pattern and its
        # entire colored region (including legacy middle/outer offsets).
        self.match_context = max([100,len(rep.ether)]
            +[max(len(a)+130,115+len(b)) for a,b in rep.n_outer]
            +[len(p)+90 for p in rep.n_middle+rep.y_middle]
            +[len(p) for p in rep.n_symbols+rep.y_symbols])
        self.raw = False
        self.canvas = np.full((self.h, self.w, 3), 255, dtype=np.uint8)
        self.surface = pygame.Surface((self.w, self.h))
        self.revision = 0
        self.dirty = True
        self.last_display = -1
        self._last_start = None
        self._last_raw = self.raw
        self._last_visible_height = 0
        self.el_size = self.w//30
        self.arrow_height = self.h//5
        self.left_rect = pygame.Rect(self.w-4*self.el_size, self.arrow_height,
                                     self.el_size, self.el_size)
        self.right_rect = self.left_rect.move(round(1.5*self.el_size), 0)
        self.arrows = {f'{name}_arrow': arrow_surface(self.el_size, name)
                       for name in ('left', 'right')}
        self.targets = {}
        self._target_row = None
        self._tape_points = []
        # Ether slices repeat between history rows. Keeping their classified
        # states also makes returning to a recently viewed region inexpensive.
        self._states_for = lru_cache(maxsize=512)(self._classify)
        self.native = NativeCloseup(self)
        self.update_targets()

    def _classify(self, value, width, raw):
        return unpack(value,width) if raw else self.representation.color(value,width)

    def update_targets(self):
        if self.simulation.row is not self._target_row:
            self._target_row = self.simulation.row
            self._tape_points = self.representation.tape_positions(self._target_row)
        points = self._tape_points
        center = self.simulation.center
        if self.native.active and self.native.fov is not None:
            fov = self.native.fov
            lo, hi = center-self.w//2+fov.left, center-self.w//2+fov.right
            offset = self.w//2-fov.centerx
        else:
            lo, hi, offset = center-self.w//2, center+self.w//2, self.w//5
        left = bisect_left(points, lo)-1
        right = bisect_right(points, hi)
        self.targets = {}
        if left >= 0:
            self.targets['left'] = points[left]+offset
        if right < len(points):
            self.targets['right'] = points[right]+offset

    def jump(self, direction):
        if direction in self.targets:
            self.simulation.center = self.targets[direction]
            self.dirty = True
            self.update_targets()

    def pan(self, cells):
        self.simulation.center += cells
        self.dirty = True
        self.update_targets()

    def process_event(self, event, camera):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                width = self.native.fov.w if self.native.fov else self.w
                self.pan((-1 if event.key == pygame.K_LEFT else 1)*max(1,width//20))
            elif event.key in (pygame.K_a, pygame.K_d):
                self.jump('left' if event.key == pygame.K_a else 'right')
            elif event.key == pygame.K_b:
                if self.native.active:
                    self.native.raw = not self.native.raw
                else:
                    self.raw = not self.raw
                self.dirty = True
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and not pygame.key.get_mods() & pygame.KMOD_CTRL):
            point = event.pos if self.native.active else camera.convert_mouse_pos(event.pos)
            rects = (self.native.arrow_rects.items() if self.native.active else
                     [('left',self.left_rect), ('right',self.right_rect)])
            for name, rect in rects:
                if rect.collidepoint(point):
                    self.jump(name)
                    return True
        return False

    def native_ready_colors(self):
        """Overridden by the verifier; keys are exact CA ticks."""
        return {}

    def _upload(self, rect, *, display_time=None, visible_height=None):
        """Copy a chronological rectangle from the circular row cache.

        Oldest is at y=0. At most two ascending, contiguous slices cover a
        rectangle, avoiding a whole-canvas rotation or particle reclassification.
        """
        rect = rect.clip(self.surface.get_rect())
        if not rect:
            return
        if display_time is None:
            display_time = self.simulation.display_time
        if visible_height is None:
            visible_height = self.h
        bottom = min(rect.bottom, visible_height)
        if bottom < rect.bottom:
            self.surface.fill((255,255,255),
                              (rect.left,max(rect.top,bottom),rect.width,
                               rect.bottom-max(rect.top,bottom)))
        if bottom <= rect.top:
            return
        first_index = max(0,display_time-self.h+1)
        slot = (first_index+rect.top) % self.h
        count = bottom-rect.top
        first = min(count,self.h-slot)
        pixels = pygame.surfarray.pixels3d(self.surface)
        pixels[rect.left:rect.right,rect.top:rect.top+first] = \
            self.canvas[slot:slot+first,rect.left:rect.right].swapaxes(0,1)
        if first < count:
            rest = count-first
            pixels[rect.left:rect.right,rect.top+first:bottom] = \
                self.canvas[:rest,rect.left:rect.right].swapaxes(0,1)
        del pixels

    def _restore_arrows(self):
        # Remove overlays before moving the image; arrows themselves stay fixed.
        for rect in (self.left_rect,self.right_rect):
            self._upload(rect, display_time=self.last_display,
                         visible_height=self._last_visible_height)

    def render(self):
        sim = self.simulation
        changed = sim.display_time != self.last_display
        if not self.dirty and not changed:
            return self.surface
        start = sim.center-self.w//2
        advance = sim.display_time-self.last_display
        first_index = max(0,sim.display_time-self.h+1)
        scroll = first_index-max(0,self.last_display-self.h+1)
        # The seed preview is not evolved history: clear it as soon as a real
        # displayed row arrives, even when playback advances a partial batch.
        if self.last_display == 0 and sim.display_time > 0:
            self.dirty = True
        if changed and (advance < 0 or advance >= self.h):
            self.dirty = True
        regions = [(0,self.w)]
        context = self.match_context
        delta = start-self._last_start if self._last_start is not None else 0
        partial_pan = (self.dirty and not changed and sim.display_time > 0
                and self.raw == self._last_raw
                and 0 < abs(delta) < self.w-2*context)
        if partial_pan or not self.dirty:
            self._restore_arrows()
        if partial_pan:
            # Retain the common spacetime columns. Recompute both edges because
            # a match crossing the old viewport margin can change at either end.
            if delta > 0:
                self.canvas[:,:self.w-delta] = self.canvas[:,delta:].copy()
                regions = [(0,context),(self.w-delta-context,self.w)]
            else:
                self.canvas[:,-delta:] = self.canvas[:,:self.w+delta].copy()
                regions = [(0,-delta+context),(self.w-context,self.w)]
        elif self.dirty:
            self.canvas.fill(255)
        margin = 100  # Exact original coarse-graining edge margin.
        updated = []
        visible_height = 0
        for index, row in sim.history:
            y = index-first_index
            if not 0 <= y < self.h:
                continue
            visible_height = max(visible_height,y+1)
            if not self.dirty and index <= self.last_display:
                continue
            slot = index % self.h
            updated.append(y)
            lo, hi = max(row.origin, start-margin), min(row.origin+row.width, start+self.w+margin)
            for left,right in regions:
                self.canvas[slot,left:right].fill(255)
                a, b = max(lo,start+left), min(hi,start+right)
                if b <= a:
                    continue
                # A strip uses enough surrounding cells to reproduce exactly
                # the full-window matcher, including its original edge bounds.
                begin, end = max(lo,a-context), min(hi,b+context)
                width = end-begin
                value = (row.value >> (begin-row.origin)) & ((1 << width)-1)
                states = self._states_for(value,width,self.raw)
                self.canvas[slot,a-start:b-start] = self.palette[states[a-begin:b-begin]]
        if sim.display_time == 0:
            # A thin seed stripe remains visible at the original fit-to-window
            # zoom. It is a time-zero preview, not additional evolution rows.
            self.canvas[:min(32,self.h)] = self.canvas[0]
        if sim.display_time == 0:
            pygame.surfarray.blit_array(self.surface, self.canvas.swapaxes(0,1))
        elif self.dirty and not partial_pan:
            self._upload(self.surface.get_rect(), visible_height=visible_height)
        else:
            # Shift the displayed pixels once per frame, regardless of how many
            # native rows arrived. The classified ring cache never moves in y.
            if partial_pan:
                self.surface.scroll(dx=-delta)
                for left,right in regions:
                    self._upload(pygame.Rect(left,0,right-left,self.h),
                                 visible_height=visible_height)
            else:
                # First fill downward. Once full, drop the oldest rows at the
                # top and make room for newer time at the bottom.
                if scroll:
                    self.surface.scroll(dy=-scroll)
                    self.surface.fill((255,255,255),(0,self.h-scroll,self.w,scroll))
                for y in updated:
                    self._upload(pygame.Rect(0,y,self.w,1))
        self.update_targets()
        for name, rect in [('left',self.left_rect), ('right',self.right_rect)]:
            if name in self.targets:
                self.surface.blit(self.arrows[f'{name}_arrow'], rect)
        self.last_display = sim.display_time
        self._last_start = start
        self._last_raw = self.raw
        self._last_visible_height = visible_height
        self.dirty = False
        self.revision += 1
        return self.surface
