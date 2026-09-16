import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Game.progression import MAX_WEAPON_LEVEL, Progress, JETS


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "Data" / "progress.json"
        self.progress = Progress(self.path)

    def tearDown(self):
        self.directory.cleanup()

    def test_all_twelve_coloured_jets_are_in_reverse_order(self):
        self.assertEqual([jet.index for jet in JETS], list(range(11, -1, -1)))
        self.assertGreater(len({jet.role for jet in JETS}), 3)
        self.assertEqual(self.progress.owned, {11})

    def test_coins_aircraft_and_drones_survive_reload(self):
        self.progress.earn(1000)
        self.assertTrue(self.progress.purchase(10)[0])
        self.assertTrue(self.progress.equip(10))
        self.assertTrue(self.progress.buy_drone()[0])
        loaded = Progress(self.path)
        self.assertEqual(loaded.coins, 530)
        self.assertEqual(loaded.owned, {11, 10})
        self.assertEqual(loaded.selected, 10)
        self.assertEqual(loaded.drone_slots, 1)
        self.assertFalse(self.path.with_suffix(".json.tmp").exists())

    def test_insufficient_funds_and_duplicate_purchases_do_not_charge(self):
        self.assertFalse(self.progress.purchase(10)[0])
        self.progress.earn(150)
        self.assertTrue(self.progress.purchase(10)[0])
        before = self.progress.coins
        self.assertFalse(self.progress.purchase(10)[0])
        self.assertEqual(self.progress.coins, before)
        self.assertFalse(self.progress.equip(0))

    def test_drone_slots_cap_at_two_paid_plus_one_free(self):
        self.progress.earn(2000)
        self.assertTrue(self.progress.buy_drone()[0])
        self.assertTrue(self.progress.buy_drone()[0])
        self.assertFalse(self.progress.buy_drone()[0])
        self.assertEqual(self.progress.coins, 900)
        self.assertEqual(self.progress.drone_slots, 2)

    def test_failed_save_rolls_back_purchases_and_equipping(self):
        self.progress.earn(1000)
        with patch.object(self.progress, "save", return_value=False):
            self.assertFalse(self.progress.purchase(10)[0])
            self.assertFalse(self.progress.buy_drone()[0])
        self.assertEqual(self.progress.coins, 1000)
        self.assertEqual(self.progress.owned, {11})
        self.assertEqual(self.progress.drone_slots, 0)
        self.progress.purchase(10)
        with patch.object(self.progress, "save", return_value=False):
            self.assertFalse(self.progress.equip(10))
        self.assertEqual(self.progress.selected, 11)

    def test_corrupt_save_is_kept_without_being_overwritten(self):
        self.path.parent.mkdir()
        self.path.write_text("not json")
        loaded = Progress(self.path)
        self.assertTrue(loaded.error)
        loaded.earn(18)
        self.assertEqual(self.path.read_text(), "not json")

    def test_invalid_selected_jet_and_slots_are_sanitized(self):
        self.path.parent.mkdir()
        self.path.write_text(json.dumps({"coins": 50, "owned": [11, 99, "0", True], "selected": 0, "drone_slots": 10}))
        loaded = Progress(self.path)
        self.assertEqual(loaded.owned, {11})
        self.assertEqual(loaded.selected, 11)
        self.assertEqual(loaded.drone_slots, 2)

    def test_weapon_upgrade_changes_stats_and_survives_reload(self):
        self.progress.earn(1000)
        before = self.progress.effective_jet(11)
        success, message = self.progress.upgrade(11)
        self.assertTrue(success, message)
        after = self.progress.effective_jet(11)
        self.assertGreater(after.damage, before.damage)
        self.assertLess(after.interval, before.interval)
        self.assertGreater(after.hull, before.hull)
        loaded = Progress(self.path)
        self.assertEqual(loaded.level(11), 2)
        self.assertEqual(loaded.effective_jet(11).damage, after.damage)

    def test_weapon_levels_stop_at_twelve(self):
        self.progress.earn(50000)
        for _ in range(MAX_WEAPON_LEVEL + 3):
            self.progress.upgrade(11)
        self.assertEqual(self.progress.level(11), MAX_WEAPON_LEVEL)
        self.assertFalse(self.progress.upgrade(11)[0])

    def test_failed_atomic_replace_keeps_the_previous_save(self):
        self.progress.earn(1000)
        before = self.path.read_text()
        with patch("pathlib.Path.replace", side_effect=OSError("disk unavailable")):
            self.assertFalse(self.progress.purchase(10)[0])
        self.assertEqual(self.path.read_text(), before)
        self.assertEqual(self.progress.coins, 1000)
        self.assertNotIn(10, self.progress.owned)
        self.assertTrue(self.progress.error)
        self.assertTrue(self.progress.save())
        self.assertEqual(self.progress.error, "")


if __name__ == "__main__":
    unittest.main()
