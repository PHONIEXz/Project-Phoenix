"""Earned coins, role-based aircraft, and atomic local progress saves."""

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Jet:
    index: int
    name: str
    role: str
    price: int
    hull: int
    speed: int
    damage: int
    interval: float


# Coloured Kenney aircraft, displayed in the requested 0011 -> 0000 order.
JETS = (
    Jet(11, "Ember", "Balanced", 0, 100, 420, 22, 0.13),
    Jet(10, "Swift", "Scout", 120, 85, 510, 18, 0.12),
    Jet(9, "Vanguard", "Heavy", 180, 145, 350, 25, 0.16),
    Jet(8, "Talon", "Striker", 250, 95, 405, 31, 0.15),
    Jet(7, "Bulwark", "Guardian", 330, 160, 330, 24, 0.15),
    Jet(6, "Comet", "Interceptor", 420, 90, 550, 20, 0.11),
    Jet(5, "Striker", "Assault", 520, 115, 410, 35, 0.16),
    Jet(4, "Sentinel", "Heavy", 650, 175, 345, 27, 0.15),
    Jet(3, "Wraith", "Interceptor", 780, 95, 570, 22, 0.11),
    Jet(2, "Tempest", "Striker", 950, 105, 445, 38, 0.15),
    Jet(1, "Aegis", "Guardian", 1150, 190, 340, 29, 0.15),
    Jet(0, "Sunflare", "Balanced", 1400, 120, 480, 30, 0.12),
)
JET_BY_INDEX = {jet.index: jet for jet in JETS}
DRONE_PRICES = (350, 750)


class Progress:
    def __init__(self, path=None):
        default = Path(__file__).resolve().parents[1] / "Data" / "progress.json"
        self.path = Path(path or os.environ.get("PHOENIX_SAVE_PATH", default))
        self.coins = 0
        self.owned = {11}
        self.selected = 11
        self.drone_slots = 0
        self.error = ""
        self.load()

    def load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            if not isinstance(data, dict):
                raise ValueError("invalid progress")
            coins = data.get("coins", 0)
            if type(coins) is not int or coins < 0:
                raise ValueError("invalid coins")
            owned = data.get("owned", [11])
            if not isinstance(owned, list):
                raise ValueError("invalid aircraft list")
            self.owned = {index for index in owned if type(index) is int and index in JET_BY_INDEX} | {11}
            self.coins = coins
            selected = data.get("selected", 11)
            self.selected = selected if type(selected) is int and selected in self.owned else 11
            slots = data.get("drone_slots", 0)
            self.drone_slots = min(2, max(0, slots)) if type(slots) is int else 0
        except (OSError, ValueError, TypeError):
            # Preserve an unreadable file; never silently overwrite its contents.
            self.error = "Progress could not be loaded. Your save was kept."

    def save(self):
        if self.error.startswith("Progress could not be loaded"):
            return False
        temporary = self.path.with_suffix(".json.tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data = {"version": 1, "coins": self.coins, "owned": sorted(self.owned), "selected": self.selected, "drone_slots": self.drone_slots}
            temporary.write_text(json.dumps(data, indent=2) + "\n")
            temporary.replace(self.path)
            self.error = ""
            return True
        except OSError:
            self.error = "Progress could not be saved. Keep the game open and retry."
            return False

    def earn(self, amount):
        self.coins += max(0, int(amount))
        self.save()

    def purchase(self, index):
        jet = JET_BY_INDEX.get(index)
        if jet is None or index in self.owned:
            return False, "Aircraft already owned or unavailable."
        if self.coins < jet.price:
            return False, f"Need {jet.price - self.coins} more coins."
        previous = self.coins
        self.coins -= jet.price
        self.owned.add(index)
        if not self.save():
            self.coins = previous
            self.owned.remove(index)
            return False, self.error
        return True, f"{jet.name} unlocked."

    def equip(self, index):
        if index not in self.owned:
            return False
        previous = self.selected
        self.selected = index
        if not self.save():
            self.selected = previous
            return False
        return True

    def buy_drone(self):
        if self.drone_slots >= 2:
            return False, "All three drone slots are ready."
        price = DRONE_PRICES[self.drone_slots]
        if self.coins < price:
            return False, f"Need {price - self.coins} more coins."
        self.coins -= price
        self.drone_slots += 1
        if not self.save():
            self.coins += price
            self.drone_slots -= 1
            return False, self.error
        return True, "Permanent support drone unlocked."
