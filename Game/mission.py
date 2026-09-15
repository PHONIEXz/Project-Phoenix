"""Finite waves with a quiet repair interval and a boss every ninth wave."""

class WaveDirector:
    def __init__(self):
        self.wave = 0
        self.remaining = 0
        self.total = 0
        self.spawn_timer = 0.0
        self.intermission = 0.0
        self.cleared = False

    def begin(self):
        self.wave += 1
        self.total = min(20, 3 + self.wave)
        self.remaining = self.total
        self.spawn_timer = 0.0
        self.intermission = 0.0
        self.cleared = False

    def update(self, dt, alive):
        """Return 'spawn', 'clear', 'next', or None for this frame."""
        if self.cleared:
            self.intermission = max(0.0, self.intermission - dt)
            return "next" if self.intermission <= 0 else None
        if self.remaining == 0 and alive == 0:
            self.cleared = True
            self.intermission = 6.0
            return "clear"
        self.spawn_timer -= dt
        if self.remaining > 0 and self.spawn_timer <= 0 and alive < min(6, 2 + (self.wave + 1) // 2):
            self.remaining -= 1
            self.spawn_timer = max(0.75, 1.35 - self.wave * 0.025)
            # Spawns are spaced even when there is capacity for multiple jets.
            return "spawn"
        return None
