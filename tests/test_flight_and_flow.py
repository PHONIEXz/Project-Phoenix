import os
import unittest
from collections import defaultdict

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from Game.flight_system import FlightController
from Game.phoenix_flow import PhoenixFlow


def held(*keys):
    return defaultdict(bool, {key: True for key in keys})


class FlightTests(unittest.TestCase):
    def test_braking_stops_without_reversing(self):
        flight = FlightController()
        velocity = pygame.Vector2(2, 0)
        for _ in range(10):
            velocity = flight.update(velocity, pygame.Vector2(1, 0), held(pygame.K_s), 1 / 60)
        self.assertEqual(velocity, pygame.Vector2())

    def test_banking_follows_nose_and_opposite_inputs_cancel(self):
        flight = FlightController()
        right = flight.update(pygame.Vector2(), pygame.Vector2(0, -1), held(pygame.K_d), 1 / 60)
        self.assertGreater(right.x, 0)
        self.assertEqual(right.y, 0)
        canceled = flight.update(pygame.Vector2(), pygame.Vector2(1, 0), held(pygame.K_a, pygame.K_d), 1 / 60)
        self.assertEqual(canceled, pygame.Vector2())

    def test_boost_drains_recharges_and_needs_release_after_depletion(self):
        flight = FlightController()
        velocity = pygame.Vector2()
        for _ in range(240):
            velocity = flight.update(velocity, pygame.Vector2(1, 0), held(pygame.K_w, pygame.K_LSHIFT), 1 / 60)
        self.assertFalse(flight.is_boosting)
        self.assertTrue(flight.boost_exhausted)
        self.assertGreater(flight.boost_energy, 0)
        flight.update(velocity, pygame.Vector2(1, 0), held(), 1 / 60)
        flight.update(velocity, pygame.Vector2(1, 0), held(pygame.K_w, pygame.K_LSHIFT), 1 / 60)
        self.assertTrue(flight.is_boosting)

    def test_releasing_boost_keeps_momentum(self):
        flight = FlightController()
        velocity = flight.update(pygame.Vector2(600, 0), pygame.Vector2(1, 0), held(), 1 / 60)
        self.assertGreater(velocity.length(), flight.max_speed)
        self.assertLess(velocity.length(), 600)

    def test_movement_is_consistent_across_frame_rates(self):
        speeds = []
        for fps in (30, 60, 120):
            flight = FlightController()
            velocity = pygame.Vector2()
            for _ in range(fps):
                velocity = flight.update(velocity, pygame.Vector2(1, 0), held(pygame.K_w), 1 / fps)
            speeds.append(velocity.length())
        self.assertLess(max(speeds) - min(speeds), 6)


class FlowTests(unittest.TestCase):
    def test_rewards_cap_and_full_energy_can_only_be_spent_once(self):
        flow = PhoenixFlow()
        self.assertFalse(flow.consume())
        for _ in range(20):
            flow.reward_maneuver()
        self.assertEqual(flow.flow, 3)
        self.assertEqual(flow.energy, 100)
        self.assertTrue(flow.consume())
        self.assertFalse(flow.consume())
        self.assertEqual(flow.energy, 0)

    def test_fast_flight_rewards_and_damage_breaks_flow(self):
        flow = PhoenixFlow()
        flow.update(0.05, 420, 420, True)
        self.assertGreater(flow.energy, 0)
        flow.reward_maneuver()
        before = flow.energy
        flow.break_flow()
        self.assertEqual(flow.flow, 1)
        self.assertLess(flow.energy, before)

    def test_inactivity_decays_multiplier(self):
        flow = PhoenixFlow()
        flow.reward_maneuver()
        for _ in range(100):
            flow.update(0.05, 0, 420)
        self.assertEqual(flow.flow, 1)


if __name__ == "__main__":
    unittest.main()
