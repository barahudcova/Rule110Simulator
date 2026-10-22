"""Small pygame controls drawn in memory, with no bitmap assets."""
import pygame


def arrow_surface(size, direction):
    """Reproduce the original red, pixel-shaped navigation arrows."""
    surface = pygame.Surface((8, 8), pygame.SRCALPHA)
    for y, (left, width) in enumerate(((3, 1), (2, 2), (1, 7), (0, 8),
                                      (0, 8), (1, 7), (2, 2), (3, 1))):
        surface.fill((221, 88, 88), (left, y, width, 1))
    if direction == 'right':
        surface = pygame.transform.flip(surface, True, False)
    return pygame.transform.scale(surface, (size, size))


def window_icon(size=32):
    """A compact black-and-white Rule 110 spacetime glyph."""
    surface = pygame.Surface((16, 16))
    surface.fill((255, 255, 255))
    row = [0]*8+[1]+[0]*7
    for y in range(16):
        for x, cell in enumerate(row):
            if cell:
                surface.set_at((x, y), (0, 0, 0))
        padded = [0]+row+[0]
        row = [(110 >> ((padded[x] << 2) | (padded[x+1] << 1)
                        | padded[x+2])) & 1 for x in range(16)]
    return pygame.transform.scale(surface, (size, size))
