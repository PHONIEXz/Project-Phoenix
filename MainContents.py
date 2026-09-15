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
        self.jet = JET_BY_INDEX[self.progress.selected]
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
        self.enemies = []
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
            self.jet = jet
            self.apply_jet()
            # Switching aircraft preserves damage instead of providing free heals.
            self.health = self.jet.hull * ratio
            self.shop_message = f"{jet.name} equipped."
        else:
            self.shop_message = self.progress.error

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
        boss = self.waves.wave % 9 == 0 and self.waves.remaining == self.waves.total - 1
        kinds = ["hunter"] if self.waves.wave == 1 else ["hunter", "flanker", "bomber"]
        kind = "boss" if boss else self.rng.choice(kinds)
        # Reject out-of-map spawns instead of clamping them onto a nearby jet.
        corners = [pygame.Vector2(x, y) for x in (90, WORLD_SIZE[0] - 90) for y in (90, WORLD_SIZE[1] - 90)]
        position = max(corners, key=lambda point: point.distance_squared_to(self.position))
        for _ in range(32):
            angle = self.rng.uniform(0, math.tau)
            candidate = self.position + pygame.Vector2(math.cos(angle), math.sin(angle)) * self.rng.uniform(650, 900)
            if 90 <= candidate.x <= WORLD_SIZE[0] - 90 and 90 <= candidate.y <= WORLD_SIZE[1] - 90:
                position = candidate
                break
        health = (650 + self.waves.wave * 20) if boss else {"hunter": 55, "flanker": 50, "bomber": 100}[kind] + min(60, self.waves.wave * 2.5)
        speed = {"hunter": 125, "flanker": 160, "bomber": 85, "boss": 80}[kind] + min(45, self.waves.wave * 2.5)
        self.enemies.append(Enemy(position, kind, health, health, speed, phase=self.rng.uniform(0, math.tau), shot_timer=self.rng.uniform(1, 2)))

    def update(self, dt, keys, mouse_position, buttons):
        self.mouse = pygame.Vector2(mouse_position)
        if self.state != "playing":
            return
        dt = max(0, min(dt, 0.05))
        self.time += dt
        for attr in ("hit_cooldown", "cannon_cooldown", "missile_cooldown", "banner_timer"):
            setattr(self, attr, max(0, getattr(self, attr) - dt))
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
            if enemy.kind == "flanker":
                movement = toward * (1 if distance > 330 else -0.3) + side * 0.9
            elif enemy.kind in ("bomber", "boss"):
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
                angles = (-14, 0, 14) if enemy.kind in ("bomber", "boss") else (0,)
                for angle in angles:
                    self.projectiles.append(Projectile(enemy.position + toward * 26, direction.rotate(angle) * 370, 8, "enemy", lifetime=2.7))
                enemy.shot_timer = self.rng.uniform(1.7, 2.5) / (1 + min(0.25, self.waves.wave * 0.015))
            if distance < enemy.radius + PLAYER_RADIUS:
                self.damage(12)
                enemy.position -= toward * 70

    def fire_cannon(self):
        if self.cannon_cooldown > 0:
            return
        target = select_target(self.enemies, self.position, self.heading, 620, 12)
        direction = (target.position - self.position).normalize() if target else self.heading.copy()
        self.projectiles.append(Projectile(self.position + self.heading * 34, direction * 1000 + self.velocity * 0.25, self.jet.damage, "player", lifetime=0.8))
        self.cannon_cooldown = self.jet.interval
        self.burst(self.position + self.heading * 34, (255, 215, 120), 2, 3)
        self.audio.play("cannon")

    def fire_missile(self):
        if self.missile_cooldown > 0 or not self.lock.ready:
            return False
        self.projectiles.append(Projectile(self.position + self.heading * 35, self.heading * 480, 85, "player", radius=7, lifetime=5, target=self.lock.target, missile=True))
        self.missile_cooldown = 2.4
        self.audio.play("missile")
        return True

    def damage(self, amount):
        if self.phoenix.guarding or self.hit_cooldown > 0:
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
            self.banner = "SECTOR CLEAR / +22 HULL / COINS AWARDED"
            self.banner_timer = 3
            self.audio.play("ready")
        elif action == "next":
            self.waves.begin()
            reinforce_drones(self)
            self.banner = f"WAVE {self.waves.wave:02d} / {'BOSS INBOUND' if self.waves.wave % 9 == 0 else 'NEW CONTACTS'}"
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
