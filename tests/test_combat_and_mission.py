import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from Game.audio import Audio
from Game.combat import Enemy, Projectile, MissileLock, guide_missile, hit_fraction, in_cone
from Game.mission import WaveDirector


class CombatTests(unittest.TestCase):
    def setUp(self):
        self.origin = pygame.Vector2()
        self.forward = pygame.Vector2(1, 0)
        self.enemy = Enemy(pygame.Vector2(400, 0), "hunter", 100, 100, 0)

    def test_cannon_cone_is_narrower_than_missile_cone(self):
        self.enemy.position = pygame.Vector2(400, 0).rotate(25)
        self.assertFalse(in_cone(self.enemy, self.origin, self.forward, 620, 12))
        self.assertTrue(in_cone(self.enemy, self.origin, self.forward, 850, 32))

    def test_lock_resets_after_heading_or_target_changes(self):
        lock = MissileLock()
        lock.update([self.enemy], self.origin, self.forward, 0.8)
        self.assertTrue(lock.ready)
        lock.update([self.enemy], self.origin, -self.forward, 0.1)
        self.assertIsNone(lock.target)
        self.assertEqual(lock.progress, 0)
        other = Enemy(pygame.Vector2(400, 0), "hunter", 100, 100, 0)
        lock.update([other], self.origin, self.forward, 0.1)
        self.assertFalse(lock.ready)
        self.assertIs(lock.target, other)

    def test_missile_takes_short_turn_across_angle_wrap(self):
        self.enemy.position = pygame.Vector2(400, 0).rotate(-179)
        shot = Projectile(self.origin.copy(), self.forward.rotate(179) * 480, 85, "player", target=self.enemy, missile=True)
        guide_missile(shot, 0.05)
        self.assertAlmostEqual(shot.velocity.angle_to(self.enemy.position), 0, delta=0.01)
        self.assertAlmostEqual(shot.velocity.length(), 480)

    def test_lost_missile_target_keeps_velocity_without_crashing(self):
        self.enemy.health = 0
        shot = Projectile(self.origin.copy(), self.forward * 480, 85, "player", target=self.enemy, missile=True)
        guide_missile(shot, 0.05)
        self.assertIsNone(shot.target)
        self.assertEqual(shot.velocity, self.forward * 480)

    def test_collision_entry_accounts_for_hitbox_radius(self):
        start = pygame.Vector2()
        end = pygame.Vector2(150, 0)
        small = hit_fraction(pygame.Vector2(85, 0), start, end, 23)
        large = hit_fraction(pygame.Vector2(100, 0), start, end, 46)
        self.assertLess(large, small)
        self.assertIsNone(hit_fraction(pygame.Vector2(85, 50), start, end, 23))
        self.assertEqual(hit_fraction(start, start, start, 24), 0)


class MissionTests(unittest.TestCase):
    def test_spawns_are_spaced_and_live_population_is_bounded(self):
        waves = WaveDirector()
        waves.begin()
        self.assertEqual(waves.update(0.016, 0), "spawn")
        self.assertIsNone(waves.update(0.016, 1))
        remaining = waves.remaining
        waves.spawn_timer = 0
        self.assertIsNone(waves.update(0.016, 4))
        self.assertEqual(waves.remaining, remaining)

    def test_wave_only_clears_when_pending_and_live_enemies_are_zero(self):
        waves = WaveDirector()
        waves.begin()
        waves.remaining = 0
        self.assertIsNone(waves.update(0.016, 1))
        self.assertEqual(waves.update(0.016, 0), "clear")
        self.assertIsNone(waves.update(1, 0))
        self.assertEqual(waves.update(5, 0), "next")


class AudioTests(unittest.TestCase):
    def test_unavailable_audio_device_is_optional(self):
        with patch("pygame.mixer.get_init", return_value=None), patch("pygame.mixer.init", side_effect=pygame.error("no device")):
            audio = Audio()
            audio.toggle()
            audio.play("cannon")
            self.assertEqual(audio.sounds, {})

    def test_audio_constructor_never_opens_a_device(self):
        with patch("pygame.mixer.init") as initialize:
            audio = Audio()
            self.assertTrue(audio.muted)
            self.assertEqual(audio.sounds, {})
            initialize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
