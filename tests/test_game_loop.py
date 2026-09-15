import inspect
import os
import runpy
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame


class FixedClock:
    def tick(self, fps):
        return 16


class GameLoopTests(unittest.TestCase):
    def test_controls_shield_near_miss_pause_defeat_and_restart(self):
        frame = 0
        snapshots = {}

        def events():
            nonlocal frame
            frame += 1
            if frame > 130:
                return [pygame.event.Event(pygame.QUIT)]
            key = {90: pygame.K_p, 95: pygame.K_p, 110: pygame.K_e, 115: pygame.K_r}.get(frame)
            return [] if key is None else [pygame.event.Event(pygame.KEYDOWN, key=key)]

        def keys():
            pressed = defaultdict(bool)
            if frame < 60:
                pressed[pygame.K_w] = True
            elif frame < 80:
                pressed[pygame.K_d] = True
                if frame >= 70:
                    pressed[pygame.K_w] = True
                    pressed[pygame.K_LSHIFT] = True
            return pressed

        def flip():
            # Observe the actual game globals at the point it presents a frame.
            state = inspect.currentframe().f_back.f_globals
            snapshots[frame] = {
                "time": state["current_time"],
                "position": state["player_position"].copy(),
                "velocity": state["player_velocity"].copy(),
                "aim": state["aim_direction"].copy(),
                "health": state["player_health"],
                "energy": state["flow"].energy,
                "boost": state["flight"].boost_energy,
                "shield": state["phoenix_shield_timer"],
                "paused": state["paused"],
                "score": state["score"],
            }
            # Keep random combat out of the controlled scenarios.
            state["enemies"].clear()
            state["last_respawn_time"] = 99999
            if frame == 100:
                state["player_velocity"].update(0, 0)
                state["enemy_bullets"].append({
                    "pos": state["player_position"] + pygame.Vector2(-5, 36),
                    "direction": pygame.Vector2(1, 0),
                    "near_miss_awarded": False,
                })
            if frame == 109:
                state["flow"].reward_maneuver(100)
                state["enemy_bullets"].clear()
                state["enemy_bullets"].append({
                    "pos": state["player_position"].copy(),
                    "direction": pygame.Vector2(1, 0),
                    "near_miss_awarded": False,
                })
            if frame == 110:
                state["phoenix_shield_timer"] = 0
                state["player_health"] = 8
                state["score"] = 300
                state["enemy_bullets"].append({
                    "pos": state["player_position"].copy(),
                    "direction": pygame.Vector2(1, 0),
                    "near_miss_awarded": False,
                })

        main_path = Path(__file__).resolve().parents[1] / "MainContents.py"
        with patch("pygame.time.Clock", FixedClock), patch("pygame.event.get", events), \
                patch("pygame.key.get_pressed", keys), patch("pygame.mouse.get_pos", return_value=(0, 0)), \
                patch("pygame.display.flip", flip):
            runpy.run_path(str(main_path), run_name="__main__")

        self.assertGreater(snapshots[59]["position"].x, snapshots[1]["position"].x)
        self.assertGreater(snapshots[69]["velocity"].y, 0)
        self.assertLess(snapshots[79]["boost"], 100)
        self.assertEqual(snapshots[79]["aim"], pygame.Vector2(1, 0))
        for paused_frame in range(90, 95):
            self.assertTrue(snapshots[paused_frame]["paused"])
            self.assertEqual(snapshots[paused_frame]["time"], snapshots[89]["time"])
            self.assertEqual(snapshots[paused_frame]["position"], snapshots[89]["position"])
        self.assertGreater(snapshots[95]["time"], snapshots[94]["time"])
        self.assertGreater(snapshots[101]["energy"], snapshots[100]["energy"])
        self.assertEqual(snapshots[102]["energy"], snapshots[101]["energy"])
        self.assertEqual(snapshots[110]["health"], 100)
        self.assertGreater(snapshots[110]["shield"], 3.9)
        self.assertEqual(snapshots[110]["energy"], 0)
        self.assertEqual(snapshots[111]["health"], 0)
        self.assertEqual(snapshots[114]["time"], snapshots[111]["time"])
        self.assertEqual(snapshots[115]["health"], 100)
        self.assertEqual(snapshots[115]["score"], 0)
        self.assertEqual(snapshots[115]["boost"], 100)
        self.assertEqual(snapshots[115]["position"], pygame.Vector2(640, 360))
        self.assertAlmostEqual(snapshots[115]["time"], 0.016)


if __name__ == "__main__":
    unittest.main()
