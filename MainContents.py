"""Project Phoenix: launch this file for the arcade flight game."""

import math
import random
import time
import pygame

from GameSettings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE
from Game.audio import Audio
from Game.combat import Enemy, Projectile, MissileLock, guide_missile, hit_fraction, segment_distance, select_target
from Game.flight_system import FlightController
from Game.mission import WaveDirector
from Game.powerups import PowerUp, random_kind
from Game.phoenix_flow import PhoenixFlow
from Game.progression import Progress, JETS, JET_BY_INDEX
from Game.renderer import Renderer
from Game.support import Phoenix, GUARD_RADIUS, reinforce_drones, update_drones

WORLD_SIZE = (3600, 2600)
PLAYER_RADIUS = 24


class Game:
    world_size = WORLD_SIZE

    def __init__(self, screen, seed=None, save_path=None, status=None):
        self.screen = screen
        self.rng = random.Random(seed)
        self.visual_rng = random.Random(31)
        self.audio = Audio()
        self.renderer = Renderer(screen, WORLD_SIZE, status=status)
        self.running = True
        self.assist = False
        if status:
            status("Loading saved progress")
        self.progress = Progress(save_path)
        self.hangar_selection = 0
        self.hangar_return = "menu"
        self.shop_message = ""
        self.reset()
        self.state = "menu"

    def reset(self):
        self.position = pygame.Vector2(1700, 1280)
        self.previous_position = self.position.copy()
        self.velocity = pygame.Vector2()
        self.heading = pygame.Vector2(1, 0)
        self.flight = FlightController()
        self.jet = self.progress.effective_jet(self.progress.selected)
        self.apply_jet()
        self.flow = PhoenixFlow()
        self.phoenix = Phoenix()
        self.lock = MissileLock()
        self.waves = WaveDirector()
        self.waves.begin()
        self.health = float(self.jet.hull)
        self.score = 0
        self.time = 0.0
        self.hit_cooldown = 0.0
        self.cannon_cooldown = 0.0
        self.missile_cooldown = 0.0
        self.missile_charges = 0
        self.shield_timer = 0.0
        self.overdrive_timer = 0.0
        self.combo = 0
        self.combo_timer = 0.0
        self.enemies = []
        self.powerups = []
        reinforce_drones(self)
        self.projectiles = []
        self.particles = []
        self.rings = []
        self.shake = 0.0
        self.camera = self.position - pygame.Vector2(self.screen.get_width() / 2, self.screen.get_height() / 2)
        self.banner = "WAVE 01 / CLEAR THE SECTOR"
        self.banner_timer = 2.5
        self.mouse = pygame.Vector2(pygame.mouse.get_pos())
        self.last_mouse = self.mouse.copy()
        self.state = "playing"

    def apply_jet(self):
        self.flight.max_speed = self.jet.speed
        self.flight.acceleration = 520 * self.jet.speed / 420
        self.flight.boost_max_speed = self.jet.speed + 200
        self.flight.boost_acceleration = self.flight.acceleration * 1.58

    def open_hangar(self):
        self.hangar_return = self.state
        self.state = "hangar"
        self.hangar_selection = next(i for i, jet in enumerate(JETS) if jet.index == self.progress.selected)
        self.shop_message = ""

    def close_hangar(self):
        self.state = self.hangar_return
        self.last_mouse = pygame.Vector2(pygame.mouse.get_pos())

    def hangar_purchase(self):
        jet = JETS[self.hangar_selection]
        if jet.index not in self.progress.owned:
            success, self.shop_message = self.progress.purchase(jet.index)
            if not success:
                return
        if self.progress.equip(jet.index):
            ratio = self.health / self.jet.hull
            self.jet = self.progress.effective_jet(jet.index)
            self.apply_jet()
            # Switching aircraft preserves damage instead of providing free heals.
            self.health = self.jet.hull * ratio
            self.shop_message = f"{jet.name} equipped."
        else:
            self.shop_message = self.progress.error

    def hangar_upgrade(self):
        jet = JETS[self.hangar_selection]
        success, self.shop_message = self.progress.upgrade(jet.index)
        if success and jet.index == self.progress.selected:
            ratio = self.health / self.jet.hull
            self.jet = self.progress.effective_jet(jet.index)
            self.apply_jet()
            self.health = min(self.jet.hull, self.jet.hull * ratio)

    def event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.WINDOWFOCUSLOST and self.state == "playing":
            self.state = "paused"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.state == "hangar":
            for index in range(12):
                if self.renderer.hangar_card(index).collidepoint(event.pos):
                    self.hangar_selection = index
                    self.shop_message = ""
                    break
            if self.renderer.hangar_buy_button().collidepoint(event.pos):
                self.hangar_purchase()
            elif self.renderer.hangar_upgrade_button().collidepoint(event.pos):
                self.hangar_upgrade()
            elif self.renderer.drone_buy_button().collidepoint(event.pos):
                success, self.shop_message = self.progress.buy_drone()
                if success:
                    reinforce_drones(self)
            elif self.renderer.hangar_back_button().collidepoint(event.pos):
                self.close_hangar()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.state == "menu":
            if pygame.Rect(82, 398, 304, 54).collidepoint(event.pos):
                self.reset()
        elif event.type == pygame.KEYDOWN:
            if self.state == "hangar":
                if event.key in (pygame.K_ESCAPE, pygame.K_h):
                    self.close_hangar()
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.hangar_selection = (self.hangar_selection - 1) % 12
                    self.shop_message = ""
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.hangar_selection = (self.hangar_selection + 1) % 12
                    self.shop_message = ""
                elif event.key == pygame.K_RETURN:
                    self.hangar_purchase()
                elif event.key == pygame.K_i:
                    self.hangar_upgrade()
                elif event.key == pygame.K_u:
                    success, self.shop_message = self.progress.buy_drone()
                    if success:
                        reinforce_drones(self)
                return
            if event.key == pygame.K_m:
                self.audio.toggle()
            elif event.key == pygame.K_RETURN and self.state == "menu":
                self.reset()
            elif event.key == pygame.K_r and self.state == "gameover":
                self.reset()
            elif event.key == pygame.K_q and self.state == "gameover":
                self.state = "menu"
            elif event.key == pygame.K_h:
                self.open_hangar()
            elif event.key in (pygame.K_p, pygame.K_ESCAPE):
                if self.state in ("playing", "paused"):
                    self.state = "paused" if self.state == "playing" else "playing"
                    self.last_mouse = pygame.Vector2(pygame.mouse.get_pos())
                elif self.state == "menu" and event.key == pygame.K_ESCAPE:
                    self.running = False
            elif event.key == pygame.K_f and self.state == "playing":
                self.assist = not self.assist
            elif event.key == pygame.K_b and self.state == "playing":
                self.phoenix.toggle()
            elif event.key == pygame.K_e and self.state == "playing" and not self.phoenix.active:
                if self.flow.consume():
                    self.phoenix.activate(self.position)
                    self.audio.play("ready")
                    self.burst(self.position, (255, 176, 65), 35)

    def burst(self, position, color, count=12, size=5):
        for _ in range(count):
            velocity = pygame.Vector2(1, 0).rotate(self.visual_rng.uniform(0, 360)) * self.visual_rng.uniform(35, 220)
            life = self.visual_rng.uniform(0.2, 0.65)
            self.particles.append([position.copy(), velocity, life, life, color, size])
        self.particles = self.particles[-450:]

    def spawn_enemy(self):
        boss = self.waves.boss_wave and self.waves.remaining == self.waves.total - 1
        kinds = ["hunter"] if self.waves.wave == 1 else ["hunter", "flanker", "bomber"]
        kind = "boss" if boss else self.rng.choice(kinds)
        position = self.formation_position(self.waves.total - self.waves.remaining, boss)
        health = (650 + self.waves.wave * 20) if boss else {"hunter": 55, "flanker": 50, "bomber": 100}[kind] + min(60, self.waves.wave * 2.5)
        speed = {"hunter": 125, "flanker": 160, "bomber": 85, "boss": 80}[kind] + min(45, self.waves.wave * 2.5)
        self.enemies.append(Enemy(position, kind, health, health, speed, phase=self.rng.uniform(0, math.tau), shot_timer=self.rng.uniform(1, 2), boss_name=self.waves.boss_name if boss else ""))

    def formation_position(self, slot, boss=False):
        """Place contacts in readable formations while retaining safe spawn distance."""
        if boss:
            formation = None
        else:
            direction = self.heading.normalize() if self.heading.length_squared() else pygame.Vector2(1, 0)
            side = pygame.Vector2(-direction.y, direction.x)
            anchor = self.position + direction * 820
            formation = self.waves.formation
            if formation == "VANGUARD SWEEP":
                depth = slot // 3
                lateral = (slot % 3 - 1) * 125
                candidate = anchor + side * lateral - direction * depth * 100
            elif formation == "PINCER RUN":
                lateral = -260 if slot % 2 == 0 else 260
                candidate = anchor + side * lateral + direction * ((slot // 2) % 3 - 1) * 90
            elif formation == "CROSSWIND COLUMN":
                candidate = anchor + side * ((slot % 5) - 2) * 95 - direction * (slot // 5) * 120
            elif formation == "RINGBREAK":
                angle = slot * math.tau / max(1, self.waves.total)
                candidate = self.position + pygame.Vector2(math.cos(angle), math.sin(angle)) * 820
            else:
                candidate = anchor + side * ((slot % 4) - 1.5) * 105
            if 90 <= candidate.x <= WORLD_SIZE[0] - 90 and 90 <= candidate.y <= WORLD_SIZE[1] - 90 and candidate.distance_to(self.position) >= 620:
                return candidate

        # Reject out-of-map spawns instead of clamping them onto a nearby jet.
        corners = [pygame.Vector2(x, y) for x in (90, WORLD_SIZE[0] - 90) for y in (90, WORLD_SIZE[1] - 90)]
        position = max(corners, key=lambda point: point.distance_squared_to(self.position))
        for _ in range(32):
            angle = self.rng.uniform(0, math.tau)
            candidate = self.position + pygame.Vector2(math.cos(angle), math.sin(angle)) * self.rng.uniform(650, 900)
            if 90 <= candidate.x <= WORLD_SIZE[0] - 90 and 90 <= candidate.y <= WORLD_SIZE[1] - 90:
                position = candidate
                break
        return position

    def update(self, dt, keys, mouse_position, buttons):
        self.mouse = pygame.Vector2(mouse_position)
        if self.state != "playing":
            return
        dt = max(0, min(dt, 0.05))
        self.time += dt
        for attr in ("hit_cooldown", "cannon_cooldown", "missile_cooldown", "shield_timer", "overdrive_timer", "combo_timer", "banner_timer"):
            setattr(self, attr, max(0, getattr(self, attr) - dt))
        if self.combo_timer <= 0:
            self.combo = 0
        self.shake = max(0, self.shake - dt * 22)

        # Camera travel and jet movement never rotate a stationary mouse heading.
        if (self.mouse - self.last_mouse).length_squared() >= 4:
            desired = self.mouse + self.camera - self.position
            if desired.length_squared():
                self.heading = desired.normalize()
            self.last_mouse = self.mouse.copy()

        self.previous_position = self.position.copy()
        self.velocity = self.flight.update(self.velocity, self.heading, keys, dt)
        self.position += self.velocity * dt
        for axis, size in (("x", WORLD_SIZE[0]), ("y", WORLD_SIZE[1])):
            value = getattr(self.position, axis)
            clamped = max(40, min(size - 40, value))
            if value != clamped:
                setattr(self.position, axis, clamped)
                setattr(self.velocity, axis, 0)

        desired_camera = self.position + self.velocity * 0.16 - pygame.Vector2(self.screen.get_width() / 2, self.screen.get_height() / 2)
        self.camera += (desired_camera - self.camera) * (1 - math.exp(-7 * dt))
        self.camera.x = max(0, min(WORLD_SIZE[0] - self.screen.get_width(), self.camera.x))
        self.camera.y = max(0, min(WORLD_SIZE[1] - self.screen.get_height(), self.camera.y))
        was_ready = self.flow.ready
        self.flow.update(dt, self.velocity.length(), self.flight.max_speed, self.flight.is_boosting)
        self.update_powerups(dt)

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            life = 0.3 if self.flight.is_boosting else 0.18
            color = (255, 171, 78) if self.flight.is_boosting else (96, 177, 212)
            self.particles.append([self.position - self.heading * 25, -self.heading * 95, life, life, color, 7 if self.flight.is_boosting else 4])

        self.update_enemies(dt)
        update_drones(self, dt)
        self.phoenix.update(self, dt)
        self.lock.update(self.enemies, self.position, self.heading, dt)
        if buttons[0] or self.assist:
            self.fire_cannon()
        if buttons[2] or keys[pygame.K_SPACE] or self.assist:
            self.fire_missile()
        self.update_projectiles(dt)
        self.remove_defeated()
        if self.phoenix.active:
            self.flow.energy = 0
            self.flow.ready = False
        if not was_ready and self.flow.ready:
            self.audio.play("ready")

        if self.health <= 0:
            self.state = "gameover"
            self.burst(self.position, (255, 160, 80), 35, 9)
            self.audio.play("explode")
        else:
            self.update_waves(dt)
        for particle in self.particles:
            particle[0] += particle[1] * dt
            particle[2] -= dt
        self.particles = [particle for particle in self.particles if particle[2] > 0][-450:]
        self.rings = [(pos, age + dt) for pos, age in self.rings if age + dt < 0.65]

    def spawn_powerup(self, position, boss=False):
        chance = 1.0 if boss else 0.24
        if self.rng.random() <= chance:
            self.powerups.append(PowerUp(position.copy(), random_kind(self.rng, boss=boss)))

    def update_powerups(self, dt):
        survivors = []
        for pickup in self.powerups:
            pickup.lifetime -= dt
            pickup.phase += dt
            if pickup.lifetime <= 0:
                continue
            if pickup.position.distance_to(self.position) <= 52:
                self.collect_powerup(pickup)
                continue
            survivors.append(pickup)
        self.powerups = survivors

    def collect_powerup(self, pickup):
        effects = {
            "repair": ("FIELD REPAIR / +30 HULL", (92, 222, 178)),
            "shield": ("SHIELD ONLINE / 8 SECONDS", (101, 190, 255)),
            "overdrive": ("OVERDRIVE / 8 SECONDS", (255, 194, 94)),
            "missile": ("MISSILE CACHE / +2 EMERGENCY SHOTS", (255, 133, 112)),
            "phoenix": ("PHOENIX FLOW RESTORED", (255, 120, 38)),
        }
        message, color = effects[pickup.kind]
        if pickup.kind == "repair":
            self.health = min(self.jet.hull, self.health + 30)
        elif pickup.kind == "shield":
            self.shield_timer = max(self.shield_timer, 8.0)
        elif pickup.kind == "overdrive":
            self.overdrive_timer = max(self.overdrive_timer, 8.0)
        elif pickup.kind == "missile":
            self.missile_charges += 2
        elif pickup.kind == "phoenix":
            if not self.phoenix.active:
                self.flow.energy = self.flow.max_energy
                self.flow.ready = True
            else:
                self.phoenix.remaining = min(50.0, self.phoenix.remaining + 8.0)
        self.banner = message
        self.banner_timer = 2.2
        self.audio.play("ready")
        self.burst(self.position, color, 18, 6)

    def update_enemies(self, dt):
        for enemy in self.enemies:
            enemy.flash = max(0, enemy.flash - dt)
            enemy.phase += dt
            offset = self.position - enemy.position
            distance = offset.length()
            if distance == 0 or enemy.health <= 0:
                continue
            toward = offset / distance
            side = pygame.Vector2(-toward.y, toward.x)
            if enemy.kind == "boss":
                ratio = enemy.health / enemy.max_health
                new_phase = 1 if ratio > 0.66 else 2 if ratio > 0.33 else 3
                if new_phase != enemy.boss_phase:
                    enemy.boss_phase = new_phase
                    self.banner = f"{enemy.boss_name or 'BOSS'} / PHASE {new_phase}"
                    self.banner_timer = 2.2
            if enemy.kind == "flanker":
                movement = toward * (1 if distance > 330 else -0.3) + side * 0.9
            elif enemy.kind == "boss" and enemy.boss_phase == 3:
                movement = toward * (1 if distance > 390 else -0.25) + side * 1.15
            elif enemy.kind == "boss":
                movement = toward * (1 if distance > 450 else -0.35) + side * (0.35 if enemy.boss_phase == 1 else 0.75)
            elif enemy.kind == "bomber":
                movement = toward * (1 if distance > 450 else -0.35) + side * 0.35
            else:
                movement = toward * (1 if distance > 290 else -0.2) + side * math.sin(enemy.phase * 1.6) * 0.45
            if movement.length_squared():
                enemy.position += movement.normalize() * enemy.speed * dt
            enemy.position.x = max(60, min(WORLD_SIZE[0] - 60, enemy.position.x))
            enemy.position.y = max(60, min(WORLD_SIZE[1] - 60, enemy.position.y))
            enemy.heading = toward
            enemy.shot_timer -= dt
            if distance < 650 and enemy.shot_timer <= 0:
                lead = self.position + self.velocity * min(0.4, distance / 700) - enemy.position
                direction = lead.normalize() if lead.length_squared() else toward
                if enemy.kind == "boss" and enemy.boss_phase == 3:
                    shot_directions = [pygame.Vector2(1, 0).rotate(enemy.phase * 20 + index * 45) for index in range(8)]
                    shot_speed = 300
                    shot_damage = 12
                else:
                    angles = (-14, 0, 14) if enemy.kind in ("bomber", "boss") else (0,)
                    shot_directions = [direction.rotate(angle) for angle in angles]
                    shot_speed = 370 if enemy.kind != "boss" else 400 + enemy.boss_phase * 25
                    shot_damage = 8 if enemy.kind != "boss" else 8 + enemy.boss_phase * 2
                for shot_direction in shot_directions:
                    self.projectiles.append(Projectile(enemy.position + toward * 26, shot_direction * shot_speed, shot_damage, "enemy", lifetime=2.7))
                enemy.shot_timer = self.rng.uniform(1.7, 2.5) / (1 + min(0.25, self.waves.wave * 0.015))
            if distance < enemy.radius + PLAYER_RADIUS:
                self.damage(12)
                enemy.position -= toward * 70

    def fire_cannon(self):
        if self.cannon_cooldown > 0:
            return
        target = select_target(self.enemies, self.position, self.heading, 620, 12)
        direction = (target.position - self.position).normalize() if target else self.heading.copy()
        count = self.jet.shot_count
        center = (count - 1) / 2
        damage = self.jet.damage * (1.35 if self.overdrive_timer > 0 else 1.0)
        for index in range(count):
            shot_direction = direction.rotate((index - center) * self.jet.spread)
            self.projectiles.append(Projectile(self.position + self.heading * 34, shot_direction * self.jet.projectile_speed + self.velocity * 0.25, damage, "player", lifetime=0.95))
        self.cannon_cooldown = self.jet.interval * (0.62 if self.overdrive_timer > 0 else 1.0)
        self.burst(self.position + self.heading * 34, (255, 215, 120), 2, 3)
        self.audio.play("cannon")

    def fire_missile(self):
        if self.missile_cooldown > 0:
            return False
        target = self.lock.target if self.lock.ready else select_target(self.enemies, self.position, self.heading, 850, 42)
        emergency = not self.lock.ready
        if target is None or (emergency and self.missile_charges <= 0):
            return False
        self.projectiles.append(Projectile(self.position + self.heading * 35, self.heading * 480, 85, "player", radius=7, lifetime=5, target=target, missile=True))
        if emergency:
            self.missile_charges -= 1
        self.missile_cooldown = 2.4
        self.audio.play("missile")
        return True

    def damage(self, amount):
        if self.phoenix.guarding or self.shield_timer > 0 or self.hit_cooldown > 0:
            return
        self.health = max(0, self.health - amount)
        self.hit_cooldown = 0.25
        self.flow.break_flow()
        self.shake = 7
        self.burst(self.position, (255, 106, 102), 10)
        self.audio.play("hit")

    def update_projectiles(self, dt):
        survivors = []
        for shot in self.projectiles:
            start = shot.position.copy()
            if shot.missile:
                guide_missile(shot, dt)
                self.particles.append([start.copy(), -shot.velocity * 0.12, 0.2, 0.2, (198, 144, 88), 4])
            shot.position += shot.velocity * dt
            shot.lifetime -= dt
            hit = False
            if shot.owner != "enemy":
                candidates = []
                for enemy in self.enemies:
                    fraction = hit_fraction(enemy.position, start, shot.position, enemy.radius + shot.radius)
                    if enemy.health > 0 and fraction is not None:
                        candidates.append((fraction, enemy))
                if candidates:
                    fraction, enemy = min(candidates, key=lambda item: item[0])
                    shot.position = start + (shot.position - start) * fraction
                    enemy.health -= shot.damage
                    enemy.flash = 0.1
                    self.burst(shot.position, (255, 192, 101), 7)
                    hit = True
            else:
                if self.phoenix.guarding and hit_fraction(self.position, start, shot.position, GUARD_RADIUS + shot.radius) is not None:
                    self.burst(shot.position, (255, 185, 80), 3, 3)
                    continue
                # Relative movement catches fast shots even as the jet moves.
                relative_start = start - self.previous_position
                relative_end = shot.position - self.position
                distance = segment_distance(pygame.Vector2(), relative_start, relative_end)
                if distance <= PLAYER_RADIUS + shot.radius:
                    self.damage(shot.damage)
                    hit = True
                elif distance <= 61 and not shot.near_miss_awarded:
                    relative_motion = relative_end - relative_start
                    if relative_end.dot(relative_motion) >= 0 and relative_start.dot(relative_motion) <= 0:
                        self.flow.reward_maneuver(12)
                        shot.near_miss_awarded = True
                        self.burst(self.position, (79, 222, 202), 7, 3)
            if not hit and shot.lifetime > 0 and -80 < shot.position.x < WORLD_SIZE[0] + 80 and -80 < shot.position.y < WORLD_SIZE[1] + 80:
                survivors.append(shot)
        self.projectiles = survivors

    def remove_defeated(self):
        alive = []
        for enemy in self.enemies:
            if enemy.health <= 0:
                self.score += 1000 if enemy.kind == "boss" else 100
                self.progress.earn(150 if enemy.kind == "boss" else 18)
                if self.phoenix.active:
                    self.flow.reward_maneuver(0, 0.05)
                else:
                    self.flow.reward_maneuver(8, 0.05)
                self.spawn_powerup(enemy.position, enemy.kind == "boss")
                self.burst(enemy.position, (255, 169, 83), 32 if enemy.kind == "boss" else 19, 8)
                self.rings.append((enemy.position.copy(), 0))
                self.shake = max(self.shake, 4)
                self.audio.play("explode")
            else:
                alive.append(enemy)
        self.enemies = alive
        if self.lock.target not in alive:
            self.lock.target = None
            self.lock.progress = 0

    def update_waves(self, dt):
        action = self.waves.update(dt, len(self.enemies))
        if action == "spawn":
            self.spawn_enemy()
        elif action == "clear":
            self.health = min(self.jet.hull, self.health + 22)
            self.progress.earn(25 + self.waves.wave * 5)
            self.projectiles = [shot for shot in self.projectiles if shot.owner != "enemy"]
            reinforce_drones(self)
            if self.waves.boss_wave:
                self.progress.earn(250)
                self.banner = f"SECTOR {self.waves.sector:02d} CLEARED / BOSS BONUS +250 / +22 HULL"
            else:
                self.banner = "WAVE CLEAR / +22 HULL / COINS AWARDED"
            self.banner_timer = 3
            self.audio.play("ready")
        elif action == "next":
            self.waves.begin()
            reinforce_drones(self)
            if self.waves.wave_in_sector == 1:
                self.banner = f"SECTOR {self.waves.sector:02d} / {self.waves.sector_name} / NEW FRONT"
            else:
                self.banner = f"WAVE {self.waves.wave_in_sector:02d} / {'BOSS INBOUND' if self.waves.boss_wave else self.waves.formation}"
            self.banner_timer = 2.5


def loading_screen(screen, message):
    print(f"[startup] {message}", flush=True)
    screen.fill((10, 19, 29))
    title_font = pygame.font.Font(None, 48)
    font = pygame.font.Font(None, 24)
    title = title_font.render("PROJECT PHOENIX", True, (255, 194, 94))
    detail = font.render(message, True, (226, 238, 240))
    center = screen.get_rect().center
    screen.blit(title, title.get_rect(center=(center[0], center[1] - 25)))
    screen.blit(detail, detail.get_rect(center=(center[0], center[1] + 30)))
    pygame.display.flip()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            raise SystemExit(0)


def main():
    started = time.perf_counter()
    game = None
    try:
        print("[startup] Opening game window (audio disabled)", flush=True)
        # Initialise only the modules required to show a screen.
        pygame.display.init()
        pygame.font.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        loading_screen(screen, "Starting flight operations")
        clock = pygame.time.Clock()
        game = Game(screen, status=lambda message: loading_screen(screen, message))
        print(f"[startup] Menu ready in {time.perf_counter() - started:.2f}s. Enter to launch; M enables sound.", flush=True)
        while game.running:
            dt = clock.tick(FPS) / 1000
            for event in pygame.event.get():
                game.event(event)
            if not game.running:
                break
            game.update(dt, pygame.key.get_pressed(), pygame.mouse.get_pos(), pygame.mouse.get_pressed())
            pygame.mouse.set_visible(game.state != "playing")
            game.renderer.draw(game)
            pygame.display.flip()
    finally:
        if game is not None:
            game.progress.save()
        if pygame.display.get_init():
            pygame.mouse.set_visible(True)
        pygame.quit()


if __name__ == "__main__":
    main()
