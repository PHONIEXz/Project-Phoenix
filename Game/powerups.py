"""Small, readable battlefield pickups with no external art dependency."""

from dataclasses import dataclass

import pygame


POWERUP_INFO = {
    "repair": ("REPAIR", (92, 222, 178)),
    "shield": ("SHIELD", (101, 190, 255)),
    "overdrive": ("OVERDRIVE", (255, 194, 94)),
    "missile": ("MISSILES", (255, 133, 112)),
    "phoenix": ("PHOENIX", (255, 120, 38)),
}


@dataclass
class PowerUp:
    position: pygame.Vector2
    kind: str
    lifetime: float = 16.0
    phase: float = 0.0

    @property
    def label(self):
        return POWERUP_INFO[self.kind][0]

    @property
    def color(self):
        return POWERUP_INFO[self.kind][1]


def random_kind(rng, boss=False):
    if boss:
        return rng.choice(("repair", "shield", "overdrive", "missile", "phoenix"))
    return rng.choice(("repair", "shield", "overdrive", "missile"))
