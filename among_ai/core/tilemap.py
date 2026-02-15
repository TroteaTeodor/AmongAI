"""Tiled map loading and camera system. Adapted from original tilemap.py."""

import pygame as pg
import pytmx
from among_ai.constants import WIDTH, HEIGHT


class TiledMap:
    """Loads a TMX tiled map and renders it to a surface."""

    def __init__(self, filename):
        tm = pytmx.load_pygame(filename, pixelalpha=True)
        self.width = tm.width * tm.tilewidth
        self.height = tm.height * tm.tileheight
        self.tmdata = tm

    def render(self, surface):
        ti = self.tmdata.get_tile_image_by_gid
        for layer in self.tmdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = ti(gid)
                    if tile:
                        surface.blit(tile, (x * self.tmdata.tilewidth, y * self.tmdata.tileheight))

    def make_map(self):
        temp = pg.Surface((self.width, self.height))
        self.render(temp)
        return temp

    def get_collision_objects(self) -> list:
        """Extract all collision rectangles from object layers."""
        objects = []
        for obj in self.tmdata.objects:
            objects.append({
                'name': obj.name,
                'x': obj.x,
                'y': obj.y,
                'width': obj.width,
                'height': obj.height,
            })
        return objects


class Camera:
    """Camera that follows a target sprite with map boundaries."""

    def __init__(self, width, height):
        self.camera = pg.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def apply_rect(self, rect):
        return rect.move(self.camera.topleft)

    def apply_pos(self, pos):
        """Apply camera offset to a raw (x, y) position."""
        return (pos[0] + self.camera.x, pos[1] + self.camera.y)

    def update(self, target):
        x = -target.rect.x + int(WIDTH / 2)
        y = -target.rect.y + int(HEIGHT / 2)
        # Clamp to map boundaries
        x = min(0, x)
        y = min(0, y)
        x = max(-(self.width - WIDTH), x)
        y = max(-(self.height - HEIGHT), y)
        self.camera = pg.Rect(x, y, self.width, self.height)

    def set_position(self, x, y):
        """Directly set camera position (for spectator mode)."""
        x = min(0, x)
        y = min(0, y)
        x = max(-(self.width - WIDTH), x)
        y = max(-(self.height - HEIGHT), y)
        self.camera = pg.Rect(x, y, self.width, self.height)
