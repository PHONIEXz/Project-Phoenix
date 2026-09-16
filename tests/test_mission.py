import unittest

from Game.mission import WaveDirector


class MissionTests(unittest.TestCase):
    def test_sectors_are_ten_waves_with_a_boss_on_the_last_wave(self):
        waves = WaveDirector()
        for expected in range(1, 21):
            waves.begin()
            self.assertEqual(waves.wave, expected)
            self.assertEqual(waves.wave_in_sector, (expected - 1) % 10 + 1)
            self.assertEqual(waves.boss_wave, expected % 10 == 0)
        self.assertEqual(waves.sector, 2)

    def test_formation_and_boss_names_are_readable(self):
        waves = WaveDirector()
        waves.begin()
        self.assertTrue(waves.formation)
        for _ in range(9):
            waves.begin()
        self.assertTrue(waves.boss_name)


if __name__ == "__main__":
    unittest.main()
