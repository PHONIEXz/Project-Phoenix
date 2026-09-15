import pygame


class FlightController:
    """Frame-rate independent arcade flight movement for Project Phoenix."""

    def __init__(self):
        self.acceleration = 520.0
        self.max_speed = 420.0
        self.brake_acceleration = 620.0
        self.strafe_acceleration = 360.0
        self.drag = 0.985

        self.boost_acceleration = 820.0
        self.boost_max_speed = 620.0
        self.boost_capacity = 100.0
        self.boost_energy = self.boost_capacity
        self.boost_drain_per_second = 34.0
        self.boost_recharge_per_second = 20.0
        self.boost_recharge_delay = 0.75
        self.time_since_boost = 999.0
        self.is_boosting = False
        self.boost_exhausted = False

    @staticmethod
    def _safe_normalize(vector):
        if vector.length_squared() == 0:
            return pygame.Vector2()
        return vector.normalize()

    def update(self, velocity, aim_direction, keys, dt):
        """Return the updated velocity for one frame."""
        dt = max(0.0, min(dt, 0.05))
        forward = self._safe_normalize(aim_direction)
        right = pygame.Vector2(-forward.y, forward.x)

        thrusting = keys[pygame.K_w] or keys[pygame.K_UP]
        braking = keys[pygame.K_s] or keys[pygame.K_DOWN]
        strafe_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        strafe_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        wants_boost = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if not wants_boost:
            self.boost_exhausted = False

        self.is_boosting = bool(
            wants_boost
            and thrusting
            and self.boost_energy > 0
            and not self.boost_exhausted
            and forward.length_squared() > 0
        )

        if thrusting:
            acceleration = self.boost_acceleration if self.is_boosting else self.acceleration
            velocity += forward * acceleration * dt

        if braking and velocity.length_squared() > 0:
            speed = velocity.length()
            speed_reduction = self.brake_acceleration * dt
            if speed_reduction >= speed:
                velocity.update(0, 0)
            else:
                velocity -= velocity.normalize() * speed_reduction

        strafe_axis = float(strafe_right) - float(strafe_left)
        if strafe_axis:
            velocity += right * self.strafe_acceleration * strafe_axis * dt

        if self.is_boosting:
            self.boost_energy = max(
                0.0,
                self.boost_energy - self.boost_drain_per_second * dt,
            )
            self.time_since_boost = 0.0
            if self.boost_energy == 0:
                self.boost_exhausted = True
        else:
            self.time_since_boost += dt
            if self.time_since_boost >= self.boost_recharge_delay:
                self.boost_energy = min(
                    self.boost_capacity,
                    self.boost_energy + self.boost_recharge_per_second * dt,
                )

        speed_limit = self.boost_max_speed if self.is_boosting else self.max_speed
        speed = velocity.length()
        if speed > speed_limit:
            # Releasing boost sheds extra speed gradually instead of snapping.
            speed_limit = max(speed_limit, speed - self.brake_acceleration * dt)
            velocity.scale_to_length(speed_limit)

        velocity *= self.drag ** (dt * 60.0)
        return velocity

    @property
    def boost_ratio(self):
        return self.boost_energy / self.boost_capacity
