import os
import unittest
from collections import defaultdict
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from MainContents import Game, WORLD_SIZE
from Game.combat import Enemy, Projectile
from Game.renderer import Renderer


def held(*keys):
    return defaultdict(bool, {key: True for key in keys})


def enemy_at(position, health=100, kind="hunter"):
    return Enemy(pygame.Vector2(position), kind, health, health, 0, shot_timer=999)


class GameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1280, 720))
        cls.renderer = Renderer(cls.screen, WORLD_SIZE)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        with patch("MainContents.Renderer", return_value=self.renderer):
            self.game = Game(self.screen, seed=17)
        self.game.audio.muted = True
        self.game.reset()
        self.game.waves.remaining = 1
        self.game.waves.spawn_timer = 999
        self.mouse = self.game.last_mouse.copy()

    def tick(self, keys=None, buttons=(False, False, False), dt=0.016):
        self.game.update(dt, keys if keys is not None else held(), self.mouse, buttons)

    def test_camera_follows_flight_and_stationary_mouse_keeps_heading(self):
        start = self.game.position.copy()
        camera = self.game.camera.copy()
        for _ in range(60):
            self.tick(held(pygame.K_w))
        self.assertGreater(self.game.position.x, start.x)
        self.assertGreater(self.game.camera.x, camera.x)
        self.assertEqual(self.game.heading, pygame.Vector2(1, 0))
        self.tick(held(pygame.K_d))
        self.assertGreater(self.game.velocity.y, 0)
        self.tick(held(pygame.K_w, pygame.K_LSHIFT))
        self.assertLess(self.game.flight.boost_energy, 100)

    def test_cannon_requires_input_or_explicit_assist(self):
        self.tick()
        self.assertEqual(self.game.projectiles, [])
        self.tick(buttons=(True, False, False))
        self.assertEqual(len(self.game.projectiles), 1)
        self.assertGreater(self.game.projectiles[0].velocity.x, 0)
        self.game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f))
        self.game.cannon_cooldown = 0
        self.tick()
        self.assertEqual(len(self.game.projectiles), 2)

    def test_missile_requires_acquisition_and_respects_rearm(self):
        target = enemy_at(self.game.position + pygame.Vector2(400, 0))
        self.game.enemies = [target]
        self.assertFalse(self.game.fire_missile())
        for _ in range(45):
            self.tick()
        self.assertTrue(self.game.lock.ready)
        self.assertTrue(self.game.fire_missile())
        self.assertFalse(self.game.fire_missile())
        self.assertTrue(self.game.projectiles[-1].missile)
        self.assertIs(self.game.projectiles[-1].target, target)

    def test_swept_collision_catches_a_fast_projectile(self):
        target = enemy_at(self.game.position + pygame.Vector2(50, 0), 20)
        self.game.enemies = [target]
        self.game.projectiles = [Projectile(self.game.position.copy(), pygame.Vector2(2000, 0), 22, "player")]
        self.game.update_projectiles(0.05)
        self.game.remove_defeated()
        self.assertEqual(self.game.projectiles, [])
        self.assertEqual(self.game.enemies, [])
        self.assertEqual(self.game.score, 100)

    def test_near_miss_only_rewards_once_after_passing(self):
        self.game.projectiles = [Projectile(self.game.position + pygame.Vector2(-10, 40), pygame.Vector2(400, 0), 8, "enemy")]
        self.game.update_projectiles(0.05)
        self.assertGreater(self.game.flow.energy, 0)
        before = self.game.flow.energy
        self.game.update_projectiles(0.05)
        self.assertEqual(self.game.flow.energy, before)
        self.assertEqual(self.game.health, 100)

    def test_shield_blocks_hits_then_damage_breaks_flow(self):
        self.game.flow.reward_maneuver(100)
        self.game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        self.assertEqual(self.game.flow.energy, 0)
        self.assertEqual(self.game.shield, 4)
        self.game.damage(8)
        self.assertEqual(self.game.health, 100)
        self.game.shield = 0
        self.game.flow.reward_maneuver(12)
        self.game.damage(8)
        self.assertEqual(self.game.health, 92)
        self.assertEqual(self.game.flow.flow, 1)

    def test_pause_freezes_simulation_and_focus_loss_pauses(self):
        self.tick(held(pygame.K_w))
        self.game.missile_cooldown = 2
        self.game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
        before = (self.game.time, self.game.position.copy(), self.game.velocity.copy(), self.game.missile_cooldown)
        for _ in range(20):
            self.tick(held(pygame.K_w))
        self.assertEqual(before, (self.game.time, self.game.position, self.game.velocity, self.game.missile_cooldown))
        self.game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.tick()
        self.assertGreater(self.game.time, before[0])
        self.game.event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.game.state, "paused")

    def test_defeat_and_restart_reset_the_run(self):
        self.game.health = 8
        self.game.score = 300
        self.game.flight.boost_energy = 10
        self.game.projectiles = [Projectile(self.game.position.copy(), pygame.Vector2(1, 0), 8, "enemy")]
        self.tick()
        self.assertEqual(self.game.state, "gameover")
        before = self.game.time
        self.tick()
        self.assertEqual(self.game.time, before)
        self.game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        self.assertEqual(self.game.state, "playing")
        self.assertEqual(self.game.health, 100)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.flight.boost_energy, 100)
        self.assertEqual(self.game.projectiles, [])
        self.assertEqual(self.game.waves.wave, 1)

    def test_wave_clear_repairs_and_delays_the_next_wave(self):
        self.game.health = 70
        self.game.waves.remaining = 0
        self.tick()
        self.assertTrue(self.game.waves.cleared)
        self.assertEqual(self.game.health, 82)
        for _ in range(60):
            self.tick()
        self.assertEqual(self.game.waves.wave, 1)
        for _ in range(170):
            self.tick()
        self.assertEqual(self.game.waves.wave, 2)

    def test_ninth_wave_spawns_exactly_one_boss(self):
        self.game.waves.wave = 8
        self.game.waves.begin()
        self.game.update_waves(0.016)
        self.assertEqual(self.game.enemies[0].kind, "boss")
        for _ in range(4):
            self.game.waves.spawn_timer = 0
            self.game.update_waves(0.016)
        self.assertEqual(sum(enemy.kind == "boss" for enemy in self.game.enemies), 1)

    def test_world_edges_stop_outward_motion_and_clamp_camera(self):
        self.game.position.update(WORLD_SIZE[0] - 41, WORLD_SIZE[1] - 41)
        self.game.velocity.update(420, 420)
        self.tick(held(pygame.K_w), dt=0.05)
        self.assertEqual(self.game.position.x, WORLD_SIZE[0] - 40)
        self.assertEqual(self.game.velocity.x, 0)
        self.assertLessEqual(self.game.camera.x, WORLD_SIZE[0] - self.screen.get_width())

    def test_edge_spawns_keep_their_distance_from_the_player(self):
        for corner in ((40, 40), (WORLD_SIZE[0] - 40, WORLD_SIZE[1] - 40)):
            self.game.position.update(corner)
            for _ in range(20):
                self.game.spawn_enemy()
                enemy = self.game.enemies[-1]
                self.assertGreaterEqual(enemy.position.distance_to(self.game.position), 649)
                self.assertGreaterEqual(enemy.position.x, 90)
                self.assertLessEqual(enemy.position.x, WORLD_SIZE[0] - 90)

    def test_all_screens_render_with_existing_aircraft_assets(self):
        self.game.enemies = [enemy_at(self.game.position + pygame.Vector2(260, 0), kind=kind) for kind in ("hunter", "flanker", "bomber", "boss")]
        self.game.lock.update(self.game.enemies, self.game.position, self.game.heading, 1)
        for state in ("menu", "playing", "paused", "gameover"):
            self.game.state = state
            self.renderer.draw(self.game)
        self.assertGreater(len(self.renderer.rotation_cache), 0)


if __name__ == "__main__":
    unittest.main()
