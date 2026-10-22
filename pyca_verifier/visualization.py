"""Ready-time and collision diagnostics using the bundled visualization kit.

Graphics are optional: headless verification never imports this module. The
viewer shares the verifier's frozen encoder and binary backend, and owns its
renderer, camera, widgets, examples and assets within this package.
"""
import argparse
from collections import deque
from pathlib import Path

import numpy as np
import pygame

from .gui.app import Application, EXAMPLES, read_examples
from .encoder import Initialization, build_seed, make_encoder
from .gui.simulation import Simulation
from .gui.view import Rule110View, ASSETS

from .collision_monitor import CollisionMonitor
from .ready import ReadyDetector, ReadyTrace


class VerificationSimulation(Simulation):
    """Observe every native row, preserving the clean simulation's dynamics."""

    def __init__(self, initialization=Initialization(), width=4500, height=3000,
                 *, multisteps=None):
        self.ready_detector = ReadyDetector()
        if multisteps is not None and (type(multisteps) is not int or multisteps < 1):
            raise ValueError('multisteps must be a positive integer')
        self.multisteps = multisteps
        super().__init__(initialization, width, height)

    def reset(self):
        self.background = None
        self.resource_plan = None
        self.encoded_seed = None
        if self.multisteps is None:
            super().reset()
        else:
            # The viewport does not participate in this seed or its evolution.
            # Use the exact finite reservoirs and ether continuation of runner.
            from .background import EtherBackground
            from .runner import plan_multisteps
            self.resource_plan = plan_multisteps(
                self.initialization, self.multisteps)
            self.encoded_seed = build_seed(self.initialization,
                program_cycles=self.resource_plan['program_cycles'],
                extra_ossifiers=self.resource_plan['extra_ossifiers'],
                padding_cells=2048)
            self.encoder = make_encoder(self.initialization)
            self.initial_word = self.encoded_seed.row.word()
            self.center = self.encoded_seed.center
            self.background = EtherBackground(self.encoded_seed.row, guard_cells=2048)
            self.row = self.background.row
            self.history = deque([(0, self.row)], maxlen=self.height)
            self.display_time = 0
        self.ready_rows = {}
        self.ready_trace = ReadyTrace()
        self.completion_tick = None
        observation = self._observe_ready()
        if observation.matches:
            self.ready_rows[0] = observation
        self.monitor = CollisionMonitor()
        self.monitor.observe(self.row)
        self.pause_requested = bool(self.monitor.events)

    def _observe_ready(self):
        observation = self.ready_detector.observe(self.row)
        self.ready_trace.observe(observation)
        return observation

    def _store_row(self):
        super()._store_row()
        oldest = self.history[0][0]
        while self.ready_rows and next(iter(self.ready_rows)) < oldest:
            del self.ready_rows[next(iter(self.ready_rows))]

    def _step(self):
        if self.background is None:
            super()._step()
        else:
            self.row = self.background.step()
        events = self.monitor.observe(self.row)
        ready = self._observe_ready()
        if ready.matches:
            self._store_row()
            self.ready_rows[self.display_time] = ready
        goal_reached = (self.multisteps is not None and self.completion_tick is None
                        and ready.is_ready
                        and len(self.ready_trace.events) >= self.multisteps+1)
        if goal_reached:
            self.completion_tick = self.row.time
        if events or goal_reached:
            self._store_row()
            self.pause_requested = True
            return True
        return False

    def extend(self):
        if self.background is not None:
            return  # Padding is evolved ether; particles are never inserted.
        before = self.row
        super().extend()
        if self.row is not before:
            self.monitor.on_splice(before, self.row)


class VerificationView(Rule110View):
    """Add markers to a separate surface, preserving all particle pixels."""

    ready_color = (190, 235, 245)
    ambiguous_ready_color = (255, 210, 210)
    ready_band_radius = 2

    def __init__(self, simulation):
        super().__init__(simulation)
        self.show_ready = True
        self._overlay_key = None
        self._verification_surface = None

    def process_event(self, event, camera):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_v:
            self.show_ready = not self.show_ready
            return True
        return super().process_event(event, camera)

    def _ready_colors(self):
        colors = {}
        if not self.show_ready:
            return colors
        visible = {index for index, _ in self.simulation.history}
        for index, observation in self.simulation.ready_rows.items():
            color = self.ready_color if observation.is_ready else self.ambiguous_ready_color
            for neighbor in range(index-self.ready_band_radius,
                                  index+self.ready_band_radius+1):
                if neighbor in visible and colors.get(neighbor) != self.ambiguous_ready_color:
                    colors[neighbor] = color
        return colors

    def native_ready_colors(self):
        if not self.show_ready:
            return {}
        return {observation.tick: (self.ready_color if observation.is_ready
                                  else self.ambiguous_ready_color)
                for observation in self.simulation.ready_rows.values()}

    def render(self):
        surface = super().render()
        colors = self._ready_colors()
        key = (self.revision, self.show_ready, tuple(sorted(colors.items())))
        if key == self._overlay_key:
            return self._verification_surface
        self._verification_surface = surface.copy()
        first = max(0, self.simulation.display_time-self.h+1)
        pixels = pygame.surfarray.pixels3d(self._verification_surface)
        try:
            for index, color in colors.items():
                y = index-first
                if 0 <= y < self.h:
                    # A saved row view would keep the surface locked even
                    # after deleting pixels. Retain only the copied mask.
                    white = np.all(pixels[:, y] == 255, axis=1)
                    pixels[white, y] = color
        finally:
            del pixels
        # UI arrows keep their own pixels, including their white backgrounds.
        for name, rect in [('left', self.left_rect), ('right', self.right_rect)]:
            if name in self.targets:
                self._verification_surface.blit(self.arrows[f'{name}_arrow'], rect)
        self.revision += 1
        self._overlay_key = (self.revision, self.show_ready, tuple(sorted(colors.items())))
        return self._verification_surface


class VerificationApplication(Application):
    def __init__(self, *args, multisteps=None, **kwargs):
        self.multisteps = multisteps
        super().__init__(*args, **kwargs)

    def load(self):
        self.simulation = VerificationSimulation(self.examples[self.selected],
                                                 self.width, self.height,
                                                 multisteps=self.multisteps)
        self.view = VerificationView(self.simulation)
        self.paused = True
        self.reset_camera()
        self._camera_frame_key = None

    def draw(self):
        if self.simulation.pause_requested:
            self.paused = True
            self.simulation.pause_requested = False
        super().draw()
        if self.help_visible:
            self.draw_ready_status()
        if self.simulation.monitor.events:
            self.draw_collision_message()
        elif self.paused and self.simulation.completion_tick == self.simulation.row.time:
            self.draw_completion_message()

    def draw_completion_message(self):
        """Explain the requested ready-return pause even with help hidden.

        This is an observation limit. The viewer does not run the tape decoder
        and must not present this message as a successful verification result.
        """
        tick = self.simulation.completion_tick
        lines = [f'Reached {self.multisteps} ready returns',
                 f'CA tick {tick}. Playback paused at the requested limit.',
                 'SPACE continues; N restarts.']
        font = pygame.font.Font(str(ASSETS/'AldotheApache.ttf'),
                                max(12, self.screen.get_height()//42))
        surfaces = [font.render(line, True, (110, 200, 215)) for line in lines]
        width = max(surface.get_width() for surface in surfaces)+24
        height = font.get_linesize()*len(lines)+24
        rect = pygame.Rect((self.screen.get_width()-width)//2,
                          max(15, self.screen.get_height()-height-15), width, height)
        pygame.draw.rect(self.screen, (0, 0, 0), rect)
        pygame.draw.rect(self.screen, (110, 200, 215), rect, 2)
        for index, surface in enumerate(surfaces):
            self.screen.blit(surface, (rect.x+12, rect.y+12+index*font.get_linesize()))

    def draw_ready_status(self):
        """Keep the new status below the original dimension/FPS fields."""
        trace = self.simulation.ready_trace
        if trace is None:
            lines = ['Ready detector unavailable']
        else:
            last = trace.events[-1]['tick'] if trace.events else 'none'
            lines = [f'Ready events: {len(trace.events)}', f'Last ready tick: {last}',
                     'V -> toggle ready-row highlights']
            if self.multisteps is not None:
                lines.append(f'Fixed reservoirs: {self.multisteps} transitions')
            if trace.ambiguous:
                lines.append(f'Ambiguous ticks: {len(trace.ambiguous)} (red)')
        if not self.view.show_ready:
            lines.append('Highlights hidden (V)')
        surfaces = [self.font.render(line, True, (110,200,215)) for line in lines]
        width = max(surface.get_width() for surface in surfaces)
        x = max(10, self.screen.get_width()-width-10)
        y = max(field.rect.bottom for field in self.fields)+12
        pygame.draw.rect(self.screen, (0,0,0),
                         (x-5, y-5, width+10, self.font.get_linesize()*len(lines)+10))
        for index, surface in enumerate(surfaces):
            self.screen.blit(surface, (x, y+index*self.font.get_linesize()))

    def draw_collision_message(self):
        event = self.simulation.monitor.events[0]
        if event.kind == 'ossifier_static_tape':
            heading = 'Ossifier struck stationary tape'
            detail = 'An approaching A4/C2 pair collided and lost its free-glider core patterns.'
        else:
            heading = 'F-producing collision signature detected'
            detail = 'Cook\'s '+('spatial' if event.kind == 'F_spatial_signature' else 'temporal')+' signature appeared.'
        lines = [heading, f'CA tick {event.tick}, cell {event.x}. Simulation paused when first detected.',
            detail, 'The periodic ossifier supply may have exhausted the accepted moving data.',
            'This can indicate an inadmissible initial configuration or intended halting;',
            'it does not establish an implementation error. SPACE continues; N restarts.']
        font = pygame.font.Font(str(ASSETS/'AldotheApache.ttf'),max(12,self.screen.get_height()//42))
        sw,sh = self.screen.get_size()
        # Wrap long explanatory lines and keep the notice independent of H/help.
        wrapped = []
        for line in lines:
            current = ''
            for token in line.split():
                candidate = (current+' '+token).strip()
                if font.size(candidate)[0] > sw-60 and current:
                    wrapped.append(current)
                    current = token
                else:
                    current = candidate
            wrapped.append(current)
        height = font.get_linesize()*len(wrapped)+24
        rect = pygame.Rect(15,max(15,(sh-height)//2),sw-30,height)
        pygame.draw.rect(self.screen,(0,0,0),rect)
        pygame.draw.rect(self.screen,(230,89,89),rect,2)
        for index,line in enumerate(wrapped):
            color = (230,89,89) if index == 0 else (230,230,230)
            self.screen.blit(font.render(line,True,color),(rect.x+12,rect.y+12+index*font.get_linesize()))


def main():
    parser = argparse.ArgumentParser(description='Rule 110 ready-time and collision viewer')
    parser.add_argument('--examples', type=Path, default=EXAMPLES)
    parser.add_argument('--case', default='Original')
    parser.add_argument('--tape')
    parser.add_argument('--appendants', nargs='+', help='YN words; use empty for an empty appendant')
    parser.add_argument('-s', '--screen', nargs=2, type=int, default=(1280, 720))
    parser.add_argument('-w', '--world', nargs=2, type=int, default=(4500, 3000))
    parser.add_argument('--no-help', action='store_true')
    parser.add_argument('--frames', type=int)
    parser.add_argument('--ticks', type=int, default=0,
                        help='Advance before opening, rounded up to 840-tick batches')
    parser.add_argument('--multisteps', type=int,
                        help='Use the verifier\'s exact fixed seed for N transitions, '
                             'independent of panning; pause at the Nth ready return')
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    try:
        examples = read_examples(args.examples)
        if args.case not in examples:
            parser.error(f'Unknown case {args.case!r}; choose from {list(examples)}')
        selected = args.case
        if args.tape is not None or args.appendants is not None:
            base = examples[selected]
            rules = tuple('' if a == 'empty' else a for a in args.appendants) \
                if args.appendants else base.appendants
            examples['Custom'] = Initialization(args.tape if args.tape is not None else base.tape, rules)
            selected = 'Custom'
        app = VerificationApplication(examples, selected, tuple(args.screen),
                                      tuple(args.world), not args.no_help,
                                      multisteps=args.multisteps)
        for _ in range((args.ticks+839)//840):
            app.simulation.advance()
            if app.simulation.pause_requested:
                break
        app.run(args.frames)
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(app.screen, args.screenshot)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
