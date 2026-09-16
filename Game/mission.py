"""Ten-wave sectors, formation patterns, and a boss at each sector end."""


SECTORS = (
    "OCEAN REACH",
    "EMBER ISLANDS",
    "STORM FRONT",
    "NIGHTFALL ZONE",
    "PHOENIX RIFT",
)
FORMATIONS = (
    "VANGUARD SWEEP",
    "PINCER RUN",
    "CROSSWIND COLUMN",
    "RINGBREAK",
    "ESCORT SCREEN",
)
BOSS_NAMES = (
    "TIDAL TITAN",
    "EMBER COLOSSUS",
    "STORM CARRIER",
    "NIGHTFALL DREADNOUGHT",
    "RIFT SOVEREIGN",
)

class WaveDirector:
    def __init__(self):
        self.wave = 0
        self.remaining = 0
        self.total = 0
        self.spawn_timer = 0.0
        self.intermission = 0.0
        self.cleared = False
        self.sector_name = SECTORS[0]
        self.formation = FORMATIONS[0]
        self.boss_name = BOSS_NAMES[0]

    def begin(self):
        self.wave += 1
        sector_index = (self.wave - 1) // 10
        self.sector_name = SECTORS[sector_index % len(SECTORS)]
        self.formation = FORMATIONS[(self.wave - 1) % len(FORMATIONS)]
        self.boss_name = BOSS_NAMES[sector_index % len(BOSS_NAMES)]
        self.total = min(20, 3 + self.wave)
        self.remaining = self.total
        self.spawn_timer = 0.0
        self.intermission = 0.0
        self.cleared = False

    @property
    def sector(self):
        return (self.wave - 1) // 10 + 1

    @property
    def wave_in_sector(self):
        return (self.wave - 1) % 10 + 1

    @property
    def boss_wave(self):
        return self.wave > 0 and self.wave % 10 == 0

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
