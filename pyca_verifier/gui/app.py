"""Small PyCA loop using the original menu, text, font and camera widgets."""
import json
from pathlib import Path
import random
import pygame
from ..encoder import Initialization
from .simulation import Simulation
from .view import Rule110View, ASSETS
from .interface.camera import Camera
from .interface.graphics import window_icon
from .interface.widgets import DropdownMenu, InputField, TextBlock, render_text_blocks

EXAMPLES = Path(__file__).parents[1]/'data'/'initializations.json'


def read_examples(path):
    entries = json.loads(Path(path).read_text())
    return {name: Initialization(entry['tape'], tuple(entry['appendants']))
            for name, entry in entries.items()}


def random_initialization():
    tape = ''.join(random.choice('YN') for _ in range(random.randint(1,5)))
    if 'Y' not in tape:
        tape = 'Y'+tape[1:]
    rules = [''.join(random.choice('YN') for _ in range(6)) for _ in range(random.randint(1,4))]
    others = rules[1:]+['']*random.randint(0,2)
    random.shuffle(others)
    return Initialization(tape, tuple(rules[:1]+others))


class Application:
    def __init__(self, examples, selected, screen=(1280,720), world=(4500,3000), help_visible=True):
        pygame.init()
        self.screen = pygame.display.set_mode(screen, pygame.RESIZABLE)
        pygame.display.set_caption('PyCA Verifier')
        pygame.display.set_icon(window_icon())
        self.examples, self.selected = examples, selected
        self.width, self.height = world
        self.fps = 60
        self.paused = True
        self.help_visible = help_visible
        self.running = True
        self.clock = pygame.time.Clock()
        self.load()
        self.layout()

    def load(self):
        self.simulation = Simulation(self.examples[self.selected], self.width, self.height)
        self.view = Rule110View(self.simulation)
        self.paused = True
        self.reset_camera()
        self._camera_frame_key = None

    def reset_camera(self):
        self.camera = Camera(self.width,self.height)
        self.camera.resize(*self.screen.get_size())
        self.camera.zoom = min(self.screen.get_width()/self.width, self.screen.get_height()/self.height)
        self.camera.updateFov()
        self.view.native.reset_camera()

    def layout(self):
        sw, sh = self.screen.get_size()
        self.font = pygame.font.Font(str(ASSETS/'AldotheApache.ttf'), max(10,sh//45))
        self.title_font = pygame.font.Font(str(ASSETS/'AldotheApache.ttf'), max(12,int(sh/45*1.3)))
        self.dropdown = DropdownMenu(self.screen, int(sw*.15),int(sh*.05),self.font,
                                     self.examples,self.selected,int(sh*.02))
        self.dropdown.label = 'Select Initialization'
        self.fields = [InputField(self.screen,int(sw*.05),int(sh*.05),self.font,
                       label, value, int(sh*.02), index) for index,(label,value) in
                       enumerate([('Width',self.width),('Height',self.height),('FPS',self.fps)])]

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            self.camera.resize(*event.size)
            self.layout()
            return
        # Menus and numeric fields own their clicks and keyboard input.
        menu_click = event.type == pygame.MOUSEBUTTONDOWN and (
            self.dropdown.rect.collidepoint(event.pos) or self.dropdown.active)
        if self.dropdown.handle_event(event):
            self.selected = self.dropdown.current_option
            self.load()
            return
        if menu_click:
            return
        active_field = any(field.active for field in self.fields)
        if self.help_visible:
            for index, field in enumerate(self.fields):
                if field.handle_event(event):
                    value = field.get_value()
                    if index == 0:
                        self.width = max(400,value)
                        field.text = str(self.width)
                    elif index == 1:
                        self.height = value
                    else:
                        self.fps = value
                    if index < 2:
                        self.load()
        if active_field or any(field.active for field in self.fields):
            return
        self.camera.handle_event(event)
        anchor = (getattr(event, 'pos', None) or pygame.mouse.get_pos())
        self.view.native.sync_camera(self.camera, anchor)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_q,pygame.K_ESCAPE):
                self.running = False
            elif event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key == pygame.K_s and self.paused:
                self.simulation.advance()
            elif event.key == pygame.K_h:
                self.help_visible = not self.help_visible
            elif event.key == pygame.K_c:
                self.reset_camera()
            elif event.key == pygame.K_n:
                self.load()
            elif event.key == pygame.K_r:
                self.examples['Random'] = random_initialization()
                self.selected = 'Random'
                self.load()
                self.layout()
            elif event.key == pygame.K_p:
                destination = Path('artifacts')
                destination.mkdir(exist_ok=True)
                surface = (self.view.native.render(self.camera, include_arrows=False)
                           if self.view.native.active
                           else self.view.render())
                pygame.image.save(surface,destination/f'tick-{self.simulation.row.time}.png')
        self.view.process_event(event,self.camera)

    def draw(self):
        self.screen.fill((0,0,0))
        self.view.native.sync_camera(self.camera)
        if self.view.native.active:
            frame = self.view.native.render(self.camera)
        else:
            surface = self.view.render()
            frame_key = (self.view.revision, tuple(self.camera.fov),
                         self.camera.zoom, self.camera.size.size)
            if frame_key != self._camera_frame_key:
                self._camera_frame = self.camera.apply(surface, border=True)
                self._camera_frame_key = frame_key
            frame = self._camera_frame
        self.screen.blit(frame,(0,0))
        if self.help_visible:
            dim, accent, title = (230,230,230),(230,89,89),(74,101,176)
            ini = self.simulation.initialization
            blocks = [TextBlock('Universality in rule 110.', 'up_sx', title, self.title_font),
                TextBlock('\n','up_sx',dim,self.font),
                TextBlock('Interface controls','up_sx',accent,self.font),
                TextBlock('SPACE -> start/stop the simulation\nS -> one simulation batch\n'
                          'H -> show/hide this help\nP -> screenshot\nQ -> quit', 'up_sx',dim,self.font),
                TextBlock('\nCamera controls','up_sx',accent,self.font),
                TextBlock('CTRL + MOUSE WHEEL -> zoom (close-up shows native cells)\nCTRL + MOUSE DRAG -> move camera\n'
                          'C -> reset camera', 'up_sx',dim,self.font),
                TextBlock('Automaton controls','below_sx',accent,self.font),
                TextBlock('LEFT / RIGHT -> move along configuration\nA / D -> jump to next offscreen tape symbol\n'
                          'N -> restart this initialization\nR -> new random initialization\nB -> toggle raw ether',
                          'below_sx',dim,self.font),
                TextBlock(f'Tape: {ini.tape or "empty"}\nAppendants: '+repr(list(ini.appendants)),
                          'below_sx',dim,self.font),
                TextBlock(f'FPS: {int(self.clock.get_fps())}\nTick: {self.simulation.row.time}\n'
                          f'View: {"native cells" if self.view.native.active else "overview"}',
                          'up_dx',accent,self.font)]
            render_text_blocks(self.screen,blocks)
            for field in self.fields:
                field.draw()
        self.dropdown.draw(self.screen,display_text=self.help_visible)

    def run(self, frames=None):
        count = 0
        while self.running and (frames is None or count < frames):
            for event in pygame.event.get():
                self.handle_event(event)
            if not self.paused:
                self.simulation.advance(time_budget=.012)
            self.draw()
            pygame.display.flip()
            self.clock.tick(self.fps)
            count += 1
