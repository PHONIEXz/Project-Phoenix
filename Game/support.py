"""Free support drones and the 50-second Phoenix ally."""

import math
from dataclasses import dataclass, field

import pygame

from Game.combat import Projectile

PHOENIX_DURATION = 50.0
GUARD_RADIUS = 185.0


@dataclass
class Drone:
    position: pygame.Vector2 = field(default_factory=pygame.Vector2)
    cooldown: float = 0.3
    # Each slot has a readable battlefield job.  ``role`` and ``level`` are
    # appended after the original fields so old saves/tests can still create
    # Drone(position, cooldown) safely.
    role: str = "gunner"
    level: int = 1


class Phoenix:
    def __init__(self):
        self.remaining = 0.0
        self.mode = "attack"
        self.position = pygame.Vector2()
        self.heading = pygame.Vector2(1, 0)
        self.cooldown = 0.0

    @property
    def active(self):
        return self.remaining > 0

    @property
    def guarding(self):
        return self.active and self.mode == "guard"

    def activate(self, position):
        if self.active:
            return False
        self.remaining = PHOENIX_DURATION
        self.position = position.copy()
        self.cooldown = 0
        return True

    def toggle(self):
        self.mode = "guard" if self.mode == "attack" else "attack"

    def update(self, game, dt):
        if not self.active:
            return
        self.remaining = max(0, self.remaining - dt)
        if self.remaining < 0.000001:
            self.remaining = 0.0
        if not self.active:
            return
        self.cooldown = max(0, self.cooldown - dt)
        candidates = [enemy for enemy in game.enemies if enemy.health > 0 and enemy.position.distance_to(game.position) <= 850]
        target = min(candidates, key=lambda enemy: enemy.position.distance_squared_to(self.position), default=None)
        orbit = game.position + pygame.Vector2(math.cos(game.time * 2.4), math.sin(game.time * 2.4)) * (135 if self.mode == "guard" else 105)
        desired = target.position if target is not None and self.mode == "attack" else orbit
        delta = desired - self.position
        if delta.length_squared():
            self.heading = delta.normalize()
            self.position += self.heading * min(delta.length(), 920 * dt)
        if self.guarding:
            for enemy in game.enemies:
                offset = enemy.position - game.position
                if enemy.health > 0 and offset.length() < GUARD_RADIUS + enemy.radius:
                    direction = offset.normalize() if offset.length_squared() else pygame.Vector2(1, 0)
                    position = game.position + direction * (GUARD_RADIUS + enemy.radius + 2)
                    if not (60 <= position.x <= game.world_size[0] - 60 and 60 <= position.y <= game.world_size[1] - 60):
                        toward_center = pygame.Vector2(game.world_size) / 2 - game.position
                        direction = toward_center.normalize()
                        position = game.position + direction * (GUARD_RADIUS + enemy.radius + 2)
                    enemy.position = position
                    enemy.health -= 100 * dt
                    enemy.flash = 0.1
        if target is not None and self.cooldown <= 0:
            offset = target.position - self.position
            if offset.length_squared():
                damage = 185 if self.mode == "attack" else 65
                game.projectiles.append(Projectile(self.position.copy(), offset.normalize() * 850, damage, "phoenix", radius=9, lifetime=2.6, target=target, missile=True))
                self.cooldown = 0.55 if self.mode == "attack" else 1.05
        life = 0.35
        game.particles.append([self.position - self.heading * 25, -self.heading * 80, life, life, (255, 146, 48), 7])


def reinforce_drones(game):
    """One free drone plus purchased slots; reinforcements arrive each wave."""
    roles = ("gunner", "interceptor", "guardian")
    level = max(1, int(getattr(game.progress, "drone_level", 1)))
    game.drones = [
        Drone(game.position.copy(), 0.3 + i * 0.18, roles[i], level)
        for i in range(min(3, 1 + game.progress.drone_slots))
    ]


def update_drones(game, dt):
    if not game.drones:
        return
    for index, drone in enumerate(game.drones):
        role = getattr(drone, "role", "gunner")
        level = max(1, int(getattr(drone, "level", getattr(game.progress, "drone_level", 1))))
        orbit_radius = {"gunner": 80, "interceptor": 94, "guardian": 72}.get(role, 80)
        orbit_speed = {"gunner": 1.1, "interceptor": 1.45, "guardian": 0.82}.get(role, 1.1)
        angle = game.time * orbit_speed + index * math.tau / len(game.drones)
        drone.position = game.position + pygame.Vector2(math.cos(angle), math.sin(angle)) * orbit_radius
        drone.cooldown = max(0, drone.cooldown - dt)
        target_range = {"gunner": 520, "interceptor": 700, "guardian": 580}.get(role, 520)
        target = min(
            (enemy for enemy in game.enemies if enemy.health > 0 and enemy.position.distance_to(drone.position) <= target_range),
            key=lambda enemy: enemy.position.distance_squared_to(drone.position),
            default=None,
        )
        if target is not None and drone.cooldown <= 0:
            offset = target.position - drone.position
            if offset.length_squared():
                wave = getattr(getattr(game, "waves", None), "wave", 1)
                base_damage = {"gunner": 14, "interceptor": 20, "guardian": 11}.get(role, 14)
                damage = base_damage + min(12, wave * 0.8) + (level - 1) * 5
                projectile_speed = {"gunner": 800, "interceptor": 930, "guardian": 730}.get(role, 800)
                radius = 5 if role == "guardian" else 4
                lifetime = 1.1 if role == "interceptor" else 0.95
                game.projectiles.append(Projectile(drone.position.copy(), offset.normalize() * projectile_speed, damage, "drone", radius=radius, lifetime=lifetime))
                base_cooldown = {"gunner": 0.8, "interceptor": 0.58, "guardian": 0.98}.get(role, 0.8)
                drone.cooldown = max(0.26, base_cooldown - (level - 1) * 0.065)
