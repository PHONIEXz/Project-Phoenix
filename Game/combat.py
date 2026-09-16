"""Arcade targeting, missile guidance, and swept projectile collisions."""

import math
from dataclasses import dataclass, field

import pygame


@dataclass(eq=False)
class Enemy:
    position: pygame.Vector2
    kind: str
    health: float
    max_health: float
    speed: float
    heading: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(-1, 0))
    shot_timer: float = 1.5
    phase: float = 0.0
    flash: float = 0.0
    boss_phase: int = 1
    boss_name: str = ""

    @property
    def radius(self):
        return 46 if self.kind == "boss" else 23


@dataclass(eq=False)
class Projectile:
    position: pygame.Vector2
    velocity: pygame.Vector2
    damage: float
    owner: str
    radius: float = 4
    lifetime: float = 2.0
    target: Enemy | None = None
    missile: bool = False
    near_miss_awarded: bool = False


def segment_distance(point, start, end):
    """Distance to an entire movement segment, including its endpoints."""
    segment = end - start
    if segment.length_squared() == 0:
        return point.distance_to(start)
    fraction = max(0.0, min(1.0, (point - start).dot(segment) / segment.length_squared()))
    return point.distance_to(start + segment * fraction)


def hit_fraction(point, start, end, radius):
    """First entry into a circular hitbox, or None when the segment misses."""
    offset = start - point
    if offset.length_squared() <= radius * radius:
        return 0.0
    movement = end - start
    a = movement.length_squared()
    if a == 0:
        return None
    b = 2 * offset.dot(movement)
    c = offset.length_squared() - radius * radius
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return None
    fraction = (-b - math.sqrt(discriminant)) / (2 * a)
    return fraction if 0 <= fraction <= 1 else None


def in_cone(enemy, position, heading, distance_limit, half_angle):
    if enemy.health <= 0 or heading.length_squared() == 0:
        return False
    offset = enemy.position - position
    distance = offset.length()
    if not 0 < distance <= distance_limit:
        return False
    return heading.normalize().dot(offset / distance) >= math.cos(math.radians(half_angle))


def select_target(enemies, position, heading, distance_limit, half_angle):
    candidates = [enemy for enemy in enemies if in_cone(enemy, position, heading, distance_limit, half_angle)]
    return min(candidates, key=lambda enemy: enemy.position.distance_squared_to(position), default=None)


class MissileLock:
    def __init__(self):
        self.target = None
        self.progress = 0.0
        self.acquire_time = 0.7
        self.distance = 850
        self.half_angle = 32

    def update(self, enemies, position, heading, dt):
        # Keep the current candidate while eligible, avoiding flickering locks.
        candidate = self.target
        if candidate not in enemies or not in_cone(candidate, position, heading, self.distance, self.half_angle):
            candidate = select_target(enemies, position, heading, self.distance, self.half_angle)
        if candidate is not self.target:
            self.target = candidate
            self.progress = 0.0
        if candidate is None:
            self.progress = 0.0
        else:
            self.progress = min(1.0, self.progress + max(0.0, dt) / self.acquire_time)

    @property
    def ready(self):
        return self.target is not None and self.target.health > 0 and self.progress >= 1


def guide_missile(projectile, dt):
    """Turn toward a live target at a limited rate; continue if it is lost."""
    if projectile.target is None or projectile.target.health <= 0:
        projectile.target = None
        return
    desired = projectile.target.position - projectile.position
    if desired.length_squared() == 0 or projectile.velocity.length_squared() == 0:
        return
    turn = (projectile.velocity.angle_to(desired) + 180) % 360 - 180
    turn = max(-220 * dt, min(220 * dt, turn))
    projectile.velocity.rotate_ip(turn)
