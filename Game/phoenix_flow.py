class PhoenixFlow:
    """Rewards smooth, high-skill flying and converts it into Phoenix energy."""

    def __init__(self):
        self.max_energy = 100.0
        self.energy = 0.0
        self.flow = 1.0
        self.max_flow = 3.0
        self.flow_timeout = 2.8
        self.time_since_action = 999.0
        self.ready = False

    def update(self, dt, speed, max_speed, boosting=False):
        dt = min(dt, 0.05)
        self.time_since_action += dt

        speed_ratio = 0.0 if max_speed <= 0 else min(1.0, speed / max_speed)

        # Sustained fast flying slowly rewards the player without making
        # ordinary cruising the fastest way to fill the meter.
        if speed_ratio >= 0.82:
            gain = 1.2 * speed_ratio * dt
            if boosting:
                gain *= 1.35
            self.energy = min(self.max_energy, self.energy + gain * self.flow)

        if self.time_since_action >= self.flow_timeout:
            self.flow = max(1.0, self.flow - 0.45 * dt)

        self.ready = self.energy >= self.max_energy

    def reward_maneuver(self, base_energy=8.0, flow_gain=0.2):
        """Call after a skillful flight event such as a close evade or speed gate."""
        self.time_since_action = 0.0
        self.flow = min(self.max_flow, self.flow + flow_gain)
        self.energy = min(self.max_energy, self.energy + base_energy * self.flow)
        self.ready = self.energy >= self.max_energy

    def break_flow(self, energy_penalty=8.0):
        """Reset the multiplier after a major flying mistake."""
        self.flow = 1.0
        self.time_since_action = 0.0
        self.energy = max(0.0, self.energy - energy_penalty)
        self.ready = self.energy >= self.max_energy

    def consume(self):
        """Spend a full meter. Returns True only when Phoenix was ready."""
        if not self.ready:
            return False
        self.energy = 0.0
        self.flow = 1.0
        self.ready = False
        return True

    @property
    def energy_ratio(self):
        return self.energy / self.max_energy

    @property
    def state_name(self):
        if self.ready:
            return "PHOENIX READY"
        if self.flow >= 2.5:
            return "IGNITED"
        if self.flow >= 1.75:
            return "HEATED"
        return "NORMAL"
