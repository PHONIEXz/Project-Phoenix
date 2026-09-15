import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import MainContents


class StartupTests(unittest.TestCase):
    def test_loading_screen_precedes_setup_and_launch_never_opens_audio(self):
        original_game = MainContents.Game
        created = False
        gameplay_frames = 0
        first_frame_before_setup = None

        def factory(screen, status=None):
            nonlocal created
            game = original_game(screen, save_path=save_path, status=status)
            created = True
            return game

        def events():
            nonlocal gameplay_frames
            if not created:
                return []
            gameplay_frames += 1
            return [pygame.event.Event(pygame.QUIT)] if gameplay_frames > 1 else []

        def flip():
            nonlocal first_frame_before_setup
            if first_frame_before_setup is None:
                first_frame_before_setup = not created

        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "progress.json"
            output = io.StringIO()
            with patch("pygame.init", side_effect=AssertionError("full init opens audio")), \
                    patch("pygame.mixer.init", side_effect=AssertionError("launch opened audio")), \
                    patch("pygame.event.get", events), patch("pygame.display.flip", flip), \
                    patch("MainContents.Game", factory), contextlib.redirect_stdout(output):
                MainContents.main()
            self.assertTrue(first_frame_before_setup)
            self.assertTrue(created)
            self.assertIn("[startup] Menu ready", output.getvalue())
            self.assertTrue(save_path.exists())
            self.assertFalse(pygame.display.get_init())

    def test_closing_loading_window_cancels_setup_and_cleans_up(self):
        with patch("pygame.event.get", return_value=[pygame.event.Event(pygame.QUIT)]), \
                patch("MainContents.Game") as constructor, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                MainContents.main()
        self.assertEqual(stopped.exception.code, 0)
        constructor.assert_not_called()
        self.assertFalse(pygame.display.get_init())
        self.assertFalse(pygame.font.get_init())


if __name__ == "__main__":
    unittest.main()
