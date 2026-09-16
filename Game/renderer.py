"""Cached procedural scenery and the flight deck HUD. No downloaded assets."""

import math
import random
from pathlib import Path

import pygame
from Game.progression import JETS, DRONE_PRICES
from Game.support import GUARD_RADIUS

INK = (10, 19, 29)
PANEL = (13, 27, 39)
WHITE = (226, 238, 240)
MUTED = (131, 164, 176)
TEAL = (79, 222, 202)
GOLD = (255, 194, 94)
RED = (255, 106, 102)


class Renderer:
    def __init__(self, screen, world_size, status=None):
        report = status or (lambda message: None)
        self.screen = screen
        self.width, self.height = screen.get_size()
        report("Loading fonts and aircraft")
        self.fonts = {size: pygame.font.Font(None, size) for size in (18, 21, 24, 28, 34, 48, 80, 116)}
        ships = Path(__file__).resolve().parents[1] / "Assets" / "Jets" / "Ships"
        raw_ships = {jet.index: pygame.image.load(str(ships / f"ship_{jet.index:04d}.png")).convert_alpha() for jet in JETS}
        self.sprites = {
            "player": pygame.transform.scale(raw_ships[11], (72, 72)),
            "hunter": pygame.transform.scale(raw_ships[0], (64, 64)),
            "flanker": pygame.transform.scale(raw_ships[4], (64, 64)),
            "bomber": pygame.transform.scale(raw_ships[7], (78, 78)),
            "boss": pygame.transform.scale(raw_ships[2], (136, 136)),
        }
        self.rotation_cache = {}
        self.jet_sprites = {index: pygame.transform.scale(image, (72, 72)) for index, image in raw_ships.items()}
        self.player_index = 11
        self.world_size = world_size
        report("Preparing the battlefield")
        self.terrain = self.make_terrain(world_size)
        self.cloud = pygame.Surface((280, 160), pygame.SRCALPHA)
        for layer in range(6):
            pygame.draw.ellipse(self.cloud, (172, 207, 212, 4 + layer * 2), (layer * 10, layer * 6, 280 - layer * 20, 160 - layer * 12))
        report("Aircraft and battlefield ready")

    def make_terrain(self, size):
        rng = random.Random(48)
        # A new surface already uses the display format; avoid a second map copy.
        surface = pygame.Surface(size, depth=self.screen.get_bitsize())
        surface.fill((19, 54, 66))
        for _ in range(2600):
            x, y = rng.randrange(size[0]), rng.randrange(size[1])
            pygame.draw.line(surface, (26, 65, 76), (x, y), (x + rng.randrange(8, 42), y), 1)
        islands = [(1380, 1570, 460, 330), (2560, 720, 380, 280), (530, 500, 430, 340), (3030, 2110, 380, 260)]
        for cx, cy, rx, ry in islands:
            shape = [(math.cos(i * math.tau / 36) * rng.uniform(0.82, 1.1), math.sin(i * math.tau / 36) * rng.uniform(0.85, 1.1)) for i in range(36)]
            for scale, color in ((1.15, (28, 77, 79)), (1.08, (59, 98, 88)), (1.0, (130, 131, 98)), (0.97, (53, 86, 70))):
                pygame.draw.polygon(surface, color, [(cx + x * rx * scale, cy + y * ry * scale) for x, y in shape])
            for _ in range(95):
                x, y = rng.gauss(cx, rx * 0.27), rng.gauss(cy, ry * 0.27)
                pygame.draw.circle(surface, (39, 72, 62), (round(x + 4), round(y + 5)), rng.randrange(8, 20))
                pygame.draw.circle(surface, (65, 99, 74), (round(x), round(y)), rng.randrange(6, 14))
        runway = pygame.Rect(1050, 1510, 660, 82)
        pygame.draw.rect(surface, (34, 45, 48), runway.inflate(20, 20), border_radius=8)
        pygame.draw.rect(surface, (58, 67, 66), runway)
        pygame.draw.rect(surface, (148, 159, 139), runway.inflate(-16, -12), 2)
        for x in range(runway.left + 40, runway.right - 20, 62):
            pygame.draw.line(surface, (194, 195, 158), (x, runway.centery), (x + 28, runway.centery), 3)
            pygame.draw.circle(surface, (111, 218, 198), (x, runway.top - 6), 3)
            pygame.draw.circle(surface, (111, 218, 198), (x, runway.bottom + 6), 3)
        for i in range(7):
            building = pygame.Rect(1120 + i * 74, 1650 + (i % 2) * 40, 50, 34)
            pygame.draw.rect(surface, (25, 49, 47), building.move(6, 8))
            pygame.draw.rect(surface, (91, 111, 95), building)
            pygame.draw.rect(surface, (116, 135, 111), building.inflate(-10, -10), 1)
        pygame.draw.rect(surface, (39, 112, 125), surface.get_rect().inflate(-4, -4), 3)
        return surface

    def text(self, label, position, size=24, color=WHITE, center=False):
        image = self.fonts[size].render(str(label), True, color)
        rect = image.get_rect(center=position) if center else image.get_rect(topleft=position)
        self.screen.blit(image, rect)
        return rect

    def panel(self, rect):
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=12)
        pygame.draw.rect(self.screen, (40, 68, 79), rect, 1, border_radius=12)

    def meter(self, x, y, label, value, ratio, color, width=230):
        self.text(label, (x, y), 18, MUTED)
        self.text(value, (x + width - 55, y), 18, color)
        pygame.draw.rect(self.screen, (33, 54, 64), (x, y + 21, width, 7), border_radius=3)
        fill = round(width * max(0, min(1, ratio)))
        if fill:
            pygame.draw.rect(self.screen, color, (x, y + 21, fill, 7), border_radius=3)

    def aircraft(self, kind, position, heading, flash=0):
        angle = round((-math.degrees(math.atan2(heading.y, heading.x)) - 90) / 3) * 3
        key = kind, angle
        if key not in self.rotation_cache:
            sprite = pygame.transform.rotate(self.sprites[kind], angle)
            shadow = sprite.copy()
            shadow.fill((0, 0, 0, 95), special_flags=pygame.BLEND_RGBA_MULT)
            self.rotation_cache[key] = sprite, shadow
        sprite, shadow = self.rotation_cache[key]
        self.screen.blit(shadow, shadow.get_rect(center=position + pygame.Vector2(16, 23)))
        self.screen.blit(sprite, sprite.get_rect(center=position))
        if flash > 0:
            pygame.draw.circle(self.screen, GOLD, position, 24, 2)

    def draw(self, game):
        if self.player_index != game.jet.index:
            self.player_index = game.jet.index
            self.sprites["player"] = self.jet_sprites[game.jet.index]
            self.rotation_cache = {key: value for key, value in self.rotation_cache.items() if key[0] != "player"}
        offset = game.camera.copy()
        if game.state == "playing" and game.shake > 0:
            offset += pygame.Vector2(game.visual_rng.uniform(-game.shake, game.shake), game.visual_rng.uniform(-game.shake, game.shake))
        # The camera always stays inside the cached map, including shake.
        offset.x = max(0, min(self.world_size[0] - self.width, offset.x))
        offset.y = max(0, min(self.world_size[1] - self.height, offset.y))
        self.screen.blit(self.terrain, (0, 0), pygame.Rect(round(offset.x), round(offset.y), self.width, self.height))
        for i in range(9):
            cloud_pos = pygame.Vector2((i * 367 + 100) % (self.width + 350) - 200, (i * 197) % (self.height + 240) - 160)
            cloud_pos -= pygame.Vector2(offset.x * 0.17 % 120, offset.y * 0.17 % 90)
            self.screen.blit(self.cloud, cloud_pos)
        if game.state == "hangar":
            self.hangar(game)
            return

        if game.phoenix.guarding:
            aura = pygame.Surface((int(GUARD_RADIUS * 2 + 12), int(GUARD_RADIUS * 2 + 12)), pygame.SRCALPHA)
            center = aura.get_width() // 2
            pygame.draw.circle(aura, (255, 177, 60, 22), (center, center), int(GUARD_RADIUS))
            pygame.draw.circle(aura, (255, 192, 78, 145), (center, center), int(GUARD_RADIUS), 2)
            self.screen.blit(aura, aura.get_rect(center=game.position - offset))

        for particle in game.particles:
            pos, _, life, total, color, size = particle
            radius = max(1, round(size * life / total))
            pygame.draw.circle(self.screen, color, pos - offset, radius)
        for pos, age in game.rings:
            pygame.draw.circle(self.screen, GOLD if age < 0.2 else (164, 117, 76), pos - offset, round(18 + age * 115), 2)

        for enemy in game.enemies:
            pos = enemy.position - offset
            if -120 < pos.x < self.width + 120 and -120 < pos.y < self.height + 120:
                self.aircraft(enemy.kind, pos, enemy.heading, enemy.flash)
                bar_width = 90 if enemy.kind == "boss" else 44
                pygame.draw.rect(self.screen, (24, 40, 46), (pos.x - bar_width / 2, pos.y - enemy.radius - 18, bar_width, 4))
                pygame.draw.rect(self.screen, RED, (pos.x - bar_width / 2, pos.y - enemy.radius - 18, bar_width * max(0, enemy.health / enemy.max_health), 4))

        for shot in game.projectiles:
            pos = shot.position - offset
            direction = shot.velocity.normalize() if shot.velocity.length_squared() else pygame.Vector2(1, 0)
            color = RED if shot.owner == "enemy" else TEAL if shot.owner == "drone" else GOLD
            pygame.draw.line(self.screen, color, pos - direction * (24 if shot.missile else 12), pos, 4 if shot.missile else 2)
            pygame.draw.circle(self.screen, RED if shot.owner == "enemy" else WHITE, pos, 3)

        if game.state != "menu":
            for drone in game.drones:
                self.drone(drone.position - offset, game.time)
            if game.phoenix.active:
                self.phoenix_bird(game.phoenix.position - offset, game.phoenix.heading, game.time)

        player = game.position - offset
        if game.state != "menu":
            self.aircraft("player", player, game.heading)
        if game.state == "playing":
            pygame.draw.line(self.screen, (98, 166, 173), player + game.heading * 44, player + game.heading * 67, 1)
            self.target_reticle(game, offset)
            self.cursor(game.mouse)
            self.edge_markers(game, offset)
        if game.state != "menu":
            self.hud(game)
        if game.state == "menu":
            self.menu(game)
        elif game.state in ("paused", "gameover"):
            self.overlay(game)

    def target_reticle(self, game, offset):
        target = game.lock.target
        if target is None:
            return
        pos = target.position - offset
        color = TEAL if game.lock.ready else GOLD
        radius = target.radius + 16
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            corner = pos + pygame.Vector2(sx * radius, sy * radius)
            pygame.draw.line(self.screen, color, corner, corner - pygame.Vector2(sx * 12, 0), 2)
            pygame.draw.line(self.screen, color, corner, corner - pygame.Vector2(0, sy * 12), 2)
        if game.lock.progress > 0:
            pygame.draw.arc(self.screen, color, pygame.Rect(pos.x - radius - 8, pos.y - radius - 8, (radius + 8) * 2, (radius + 8) * 2), -math.pi / 2, -math.pi / 2 + math.tau * game.lock.progress, 2)
        label = "LOCKED" if game.lock.ready else f"ACQUIRING {game.lock.progress:.0%}"
        self.text(label, (pos.x, pos.y + radius + 17), 18, color, True)

    def cursor(self, position):
        pygame.draw.circle(self.screen, WHITE, position, 9, 1)
        for delta in ((-16, 0), (16, 0), (0, -16), (0, 16)):
            end = pygame.Vector2(position) + pygame.Vector2(delta)
            start = pygame.Vector2(position) + pygame.Vector2(delta) * 0.72
            pygame.draw.line(self.screen, TEAL, start, end, 1)

    def edge_markers(self, game, offset):
        center = pygame.Vector2(self.width / 2, self.height / 2)
        for enemy in game.enemies:
            pos = enemy.position - offset
            if 30 < pos.x < self.width - 30 and 90 < pos.y < self.height - 150:
                continue
            direction = pos - center
            if not direction.length_squared():
                continue
            direction.normalize_ip()
            scale = min((self.width / 2 - 34) / max(abs(direction.x), 0.01), (self.height / 2 - 155) / max(abs(direction.y), 0.01))
            mark = center + direction * scale
            side = pygame.Vector2(-direction.y, direction.x)
            pygame.draw.polygon(self.screen, RED, [mark + direction * 8, mark - direction * 5 + side * 5, mark - direction * 5 - side * 5])

    def hud(self, game):
        self.panel(pygame.Rect(20, 18, 255, 61))
        self.text("PROJECT / PHOENIX", (36, 29), 24)
        self.text(f"{game.jet.name.upper()} / {game.progress.coins} COINS", (36, 55), 18, GOLD)
        self.panel(pygame.Rect(self.width / 2 - 163, 18, 326, 61))
        self.text(f"WAVE {game.waves.wave:02d}  /  {game.score:06d} PTS", (self.width / 2, 39), 28, WHITE, True)
        self.text(f"{len(game.enemies) + game.waves.remaining} CONTACTS REMAINING", (self.width / 2, 63), 18, MUTED, True)
        self.panel(pygame.Rect(self.width - 217, 18, 197, 164))
        self.text("SECTOR RADAR", (self.width - 201, 30), 18, TEAL)
        radar = pygame.Rect(self.width - 202, 58, 167, 107)
        pygame.draw.rect(self.screen, (21, 48, 59), radar)
        for i in range(1, 4):
            pygame.draw.line(self.screen, (36, 67, 76), (radar.x + radar.w * i / 4, radar.y), (radar.x + radar.w * i / 4, radar.bottom))
            pygame.draw.line(self.screen, (36, 67, 76), (radar.x, radar.y + radar.h * i / 4), (radar.right, radar.y + radar.h * i / 4))
        def radar_pos(pos):
            return pygame.Vector2(radar.x + pos.x / self.world_size[0] * radar.w, radar.y + pos.y / self.world_size[1] * radar.h)
        for enemy in game.enemies:
            pygame.draw.circle(self.screen, RED, radar_pos(enemy.position), 4 if enemy.kind == "boss" else 2)
        pygame.draw.circle(self.screen, TEAL, radar_pos(game.position), 4)

        self.panel(pygame.Rect(20, self.height - 149, 274, 126))
        self.meter(38, self.height - 135, "HULL", f"{game.health:.0f}/{game.jet.hull}", game.health / game.jet.hull, RED if game.health < game.jet.hull * 0.3 else TEAL)
        self.meter(38, self.height - 97, "AFTERBURNER", f"{game.flight.boost_energy:.0f}%", game.flight.boost_ratio, (100, 191, 255))
        self.meter(38, self.height - 59, f"PHOENIX / FLOW x{game.flow.flow:.1f}", f"{game.flow.energy:.0f}%", game.flow.energy_ratio, GOLD)
        self.panel(pygame.Rect(self.width - 314, self.height - 126, 294, 103))
        self.text("CANNON  /  LEFT MOUSE", (self.width - 298, self.height - 110), 21)
        if game.missile_cooldown > 0:
            status = f"MISSILE REARM {game.missile_cooldown:.1f}s"
        elif game.lock.ready:
            status = "LOCKED / RIGHT MOUSE OR SPACE"
        elif game.lock.target is not None:
            status = "MISSILE ACQUIRING TARGET"
        else:
            status = "MISSILE / AIM TO ACQUIRE"
        self.text(status, (self.width - 298, self.height - 77), 18, TEAL if game.lock.ready else GOLD)
        self.text(f"ASSIST {'ON' if game.assist else 'OFF'} [F]   SOUND {'OFF' if game.audio.muted else 'ON'} [M]", (self.width - 298, self.height - 45), 18, MUTED)
        self.text(f"{game.velocity.length():03.0f}", (self.width / 2, self.height - 88), 48, WHITE, True)
        self.text("FLIGHT SPEED", (self.width / 2, self.height - 54), 18, MUTED, True)
        if game.phoenix.active:
            self.text(f"PHOENIX {game.phoenix.mode.upper()} / {game.phoenix.remaining:.0f}s / B SWITCH", (self.width / 2, self.height - 123), 21, GOLD, True)
        elif game.flow.ready:
            self.text("PHOENIX READY / E SUMMON / B MODE", (self.width / 2, self.height - 123), 21, GOLD, True)
        self.text(f"{len(game.drones)} DRONE{'S' if len(game.drones) != 1 else ''} / H HANGAR", (self.width / 2, self.height - 27), 18, TEAL, True)
        if game.progress.error:
            self.text(game.progress.error, (self.width / 2, 190), 21, RED, True)
        if game.banner_timer > 0 and game.state == "playing":
            self.text(game.banner, (self.width / 2, 116), 34, GOLD, True)
        if game.waves.cleared and game.state == "playing":
            self.text(f"NEXT WAVE {game.waves.intermission:.1f}s / H HANGAR", (self.width / 2, 149), 21, TEAL, True)

    def dim(self):
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        surface.fill((5, 14, 24, 200))
        self.screen.blit(surface, (0, 0))

    def menu(self, game):
        self.dim()
        self.text("AERIAL SURVIVAL  /  SECTOR 07", (80, 111), 21, TEAL)
        self.text("PROJECT", (75, 155), 80)
        self.text("PHOENIX", (75, 218), 116, GOLD)
        self.text("Fly with momentum. Hold your line. Earn the lock.", (82, 337), 28, MUTED)
        button = pygame.Rect(82, 398, 304, 54)
        pygame.draw.rect(self.screen, TEAL if button.collidepoint(game.mouse) else GOLD, button, border_radius=8)
        self.text("LAUNCH SORTIE   /   ENTER", button.center, 24, INK, True)
        self.text("W thrust   S brake   A/D bank   Shift boost", (82, 488), 24)
        self.text("Mouse aim   Left fire   Right/Space missile", (82, 520), 24)
        self.text("E Phoenix   B mode   H hangar   P/Esc pause", (82, 552), 24)
        self.text(f"{game.progress.coins} COINS / {len(game.progress.owned)} AIRCRAFT / H OPEN HANGAR", (82, self.height - 65), 21, GOLD)
        if game.progress.error:
            self.text(game.progress.error, (82, self.height - 32), 18, RED)
        preview = pygame.transform.scale(self.sprites["player"], (200, 200))
        self.screen.blit(preview, preview.get_rect(center=(self.width - 270, self.height / 2)))
        pygame.draw.circle(self.screen, (57, 91, 106), (self.width - 270, self.height // 2), 119, 1)
        pygame.draw.circle(self.screen, (57, 91, 106), (self.width - 270, self.height // 2), 145, 1)
        self.text(f"{game.jet.name.upper()} / {game.jet.index:04d}", (self.width - 270, self.height / 2 + 180), 21, GOLD, True)

    def overlay(self, game):
        self.dim()
        center = self.width / 2
        self.text("FLIGHT PAUSED" if game.state == "paused" else "SORTIE COMPLETE", (center, self.height / 2 - 65), 48, GOLD, True)
        self.text(f"WAVE {game.waves.wave:02d}  /  SCORE {game.score:06d}", (center, self.height / 2), 28, WHITE, True)
        label = "P / ESC RESUME  /  H HANGAR" if game.state == "paused" else "R FLY AGAIN  /  H HANGAR  /  Q MENU"
        self.text(label, (center, self.height / 2 + 57), 24, TEAL, True)

    def drone(self, position, time):
        for delta in ((-11, -8), (11, -8), (-11, 8), (11, 8)):
            pos = position + pygame.Vector2(delta)
            pygame.draw.line(self.screen, (102, 182, 193), position, pos, 2)
            pygame.draw.circle(self.screen, (22, 63, 77), pos, 6)
            pygame.draw.line(self.screen, TEAL, pos - pygame.Vector2(5, math.sin(time * 30) * 3), pos + pygame.Vector2(5, math.sin(time * 30) * 3), 1)
        pygame.draw.polygon(self.screen, TEAL, [position + pygame.Vector2(0, -9), position + pygame.Vector2(7, 0), position + pygame.Vector2(0, 9), position + pygame.Vector2(-7, 0)])
        pygame.draw.circle(self.screen, WHITE, position, 2)

    def phoenix_bird(self, position, heading, time):
        angle = math.degrees(math.atan2(heading.y, heading.x))
        flap = math.sin(time * 9) * 13
        def shape(points, color):
            pygame.draw.polygon(self.screen, color, [position + pygame.Vector2(point).rotate(angle) for point in points])
        shape([(-12, -5), (-23, -24 - flap), (-48, -47 - flap), (-31, -16), (-22, -7)], (255, 120, 38))
        shape([(-12, 5), (-23, 24 + flap), (-48, 47 + flap), (-31, 16), (-22, 7)], (255, 120, 38))
        shape([(-9, -5), (-17, -24 - flap * 0.7), (-36, -35 - flap * 0.7), (-21, -10)], GOLD)
        shape([(-9, 5), (-17, 24 + flap * 0.7), (-36, 35 + flap * 0.7), (-21, 10)], GOLD)
        shape([(-11, -7), (-60, -15), (-36, 0), (-60, 15), (-11, 7)], (230, 85, 33))
        shape([(-20, -7), (14, -10), (26, -5), (39, 1), (26, 7), (8, 9), (-20, 7)], (255, 220, 109))
        shape([(23, -5), (45, 1), (26, 5)], (255, 150, 43))
        eye = position + pygame.Vector2(22, -3).rotate(angle)
        pygame.draw.circle(self.screen, INK, eye, 2)

    def hangar_card(self, index):
        return pygame.Rect(28 + index % 4 * 210, 112 + index // 4 * 136, 194, 120)

    def hangar_buy_button(self):
        return pygame.Rect(self.width - 390, 467, 350, 49)

    def hangar_upgrade_button(self):
        return pygame.Rect(self.width - 390, 522, 350, 38)

    def drone_buy_button(self):
        return pygame.Rect(567, self.height - 146, 255, 47)

    def hangar_back_button(self):
        return pygame.Rect(self.width - 238, 30, 198, 42)

    def hangar(self, game):
        self.dim()
        self.text("PHOENIX / AIRCRAFT HANGAR", (28, 30), 34, WHITE)
        self.text(f"{game.progress.coins} COINS / EARNED IN COMBAT / SAVED AFTER DEFEAT", (30, 73), 21, GOLD)
        back = self.hangar_back_button()
        self.panel(back)
        self.text("BACK / ESC", back.center, 21, TEAL, True)
        for index, jet in enumerate(JETS):
            card = self.hangar_card(index)
            self.panel(card)
            selected = index == game.hangar_selection
            if selected:
                pygame.draw.rect(self.screen, GOLD, card, 2, border_radius=12)
            sprite = self.jet_sprites[jet.index]
            self.screen.blit(sprite, sprite.get_rect(center=(card.x + 44, card.y + 48)))
            self.text(jet.name, (card.x + 85, card.y + 20), 21)
            self.text(jet.role, (card.x + 85, card.y + 46), 18, MUTED)
            state = "EQUIPPED" if jet.index == game.progress.selected else "OWNED" if jet.index in game.progress.owned else f"{jet.price} COINS"
            self.text(state, (card.x + 15, card.y + 94), 18, TEAL if jet.index in game.progress.owned else GOLD)
        base_jet = JETS[game.hangar_selection]
        jet = game.progress.effective_jet(base_jet.index)
        detail = pygame.Rect(self.width - 410, 112, 390, 420)
        self.panel(detail)
        self.text(jet.name.upper(), (detail.centerx, 149), 34, GOLD, True)
        preview = pygame.transform.scale(self.jet_sprites[jet.index], (132, 132))
        self.screen.blit(preview, preview.get_rect(center=(detail.centerx, 235)))
        level = game.progress.level(jet.index)
        self.text(f"{jet.role.upper()} / LEVEL {level} / SHIP {jet.index:04d}", (detail.centerx, 313), 20, TEAL, True)
        self.text(f"HULL {jet.hull}   /   SPEED {jet.speed}", (detail.x + 25, 350), 22)
        self.text(f"{jet.weapon.upper()} / {jet.damage} DAMAGE", (detail.x + 25, 383), 20)
        self.text(f"{jet.shot_count} SHOT{'S' if jet.shot_count != 1 else ''} / {1 / jet.interval:.1f} PER SEC", (detail.x + 25, 414), 20, MUTED)
        self.text("Each level improves hull, speed, damage and reload.", (detail.x + 25, 445), 17, MUTED)
        buy = self.hangar_buy_button()
        pygame.draw.rect(self.screen, TEAL if base_jet.index in game.progress.owned else GOLD, buy, border_radius=8)
        label = "EQUIP / ENTER" if base_jet.index in game.progress.owned else f"BUY & EQUIP / {base_jet.price} COINS"
        self.text(label, buy.center, 21, INK, True)
        upgrade = self.hangar_upgrade_button()
        pygame.draw.rect(self.screen, GOLD if level < 5 and base_jet.index in game.progress.owned else (52, 105, 118), upgrade, border_radius=7)
        upgrade_label = "MAX WEAPON LEVEL" if level >= 5 else f"UPGRADE WEAPON / {160 + level * 140} COINS / I"
        self.text(upgrade_label, upgrade.center, 16, INK if level < 5 and base_jet.index in game.progress.owned else MUTED, True)
        panel = pygame.Rect(28, self.height - 164, 814, 87)
        self.panel(panel)
        self.text(f"DRONE SUPPORT / {1 + game.progress.drone_slots} OF 3", (46, panel.y + 15), 24, TEAL)
        self.text("One free escort. Purchased drones stay unlocked.", (46, panel.y + 49), 21, MUTED)
        button = self.drone_buy_button()
        pygame.draw.rect(self.screen, GOLD, button, border_radius=8)
        label = "ALL DRONES UNLOCKED" if game.progress.drone_slots == 2 else f"BUY DRONE / {DRONE_PRICES[game.progress.drone_slots]} / U"
        self.text(label, button.center, 18, INK, True)
        message = game.progress.error or game.shop_message or "A/D select / Enter buy or equip / I upgrade weapon / U buy drone / Esc return"
        self.text(message, (30, self.height - 48), 18, RED if game.progress.error else WHITE)
