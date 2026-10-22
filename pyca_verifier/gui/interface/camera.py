"""The PyCA camera geometry, with cursor-centred zoom and Ctrl-drag."""
import pygame


class Camera:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.position = pygame.Vector2(width/2,height/2)
        self.zoom = 2.0
        self.drag_start = None
        self.size = pygame.Rect(0,0,width,height)
        self.updateFov()

    def resize(self, width, height):
        self.size = pygame.Rect(0,0,width,height)
        self.updateFov()

    def updateFov(self):
        self.fov = pygame.Rect(0,0,max(1,int(self.size.w/self.zoom)),
                               max(1,int(self.size.h/self.zoom)))
        self.fov.center = self.position

    def zoom_at(self, pos, factor):
        old_zoom = self.zoom
        self.zoom = min(20,max(.02,self.zoom*factor))
        delta = pygame.Vector2(pos)-pygame.Vector2(self.size.size)/2
        self.position += delta*(1/old_zoom-1/self.zoom)
        self.updateFov()

    def handle_event(self, event):
        ctrl = pygame.key.get_mods() & pygame.KMOD_CTRL
        if ctrl and event.type == pygame.MOUSEWHEEL:
            self.zoom_at(pygame.mouse.get_pos(),1.1**event.y)
        elif ctrl and event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (4,5):
                self.zoom_at(event.pos,1.1 if event.button == 4 else 1/1.1)
            elif event.button == 1:
                self.drag_start = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.drag_start = None
        elif event.type == pygame.MOUSEMOTION and self.drag_start is not None:
            self.position += (pygame.Vector2(self.drag_start)-pygame.Vector2(event.pos))/self.zoom
            self.drag_start = event.pos
        self.updateFov()

    def convert_mouse_pos(self, pos):
        return (int(pos[0]/self.zoom+self.fov.left),int(pos[1]/self.zoom+self.fov.top))

    def apply(self, surface, border=False):
        visible = pygame.Surface(self.fov.size)
        visible.blit(surface,(0,0),self.fov)
        scaled = pygame.transform.scale(visible,self.size.size)
        if border:
            pygame.draw.rect(scaled,(125,125,125),
                (-self.fov.left*self.zoom,-self.fov.top*self.zoom,
                 self.width*self.zoom,self.height*self.zoom),3)
        return scaled
