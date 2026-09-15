import pygame
import math
import random
from pathlib import Path

from GameSettings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE
from Game.flight_system import FlightController
from Game.phoenix_flow import PhoenixFlow


# PROJECT PATH

BASE_DIR = Path(__file__).resolve().parent

PLAYER_IMAGE_PATH = (
    BASE_DIR
    / "Assets"
    / "Jets"
    / "Ships"
    / "ship_0011.png"
)


# PYGAME SETUP

pygame.init()

screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT)
)

pygame.display.set_caption(GAME_TITLE)

clock = pygame.time.Clock()


# PLAYER

player_image = pygame.image.load(
    str(PLAYER_IMAGE_PATH)
).convert_alpha()

player_position = pygame.Vector2(
    SCREEN_WIDTH // 2,
    SCREEN_HEIGHT // 2
)

player_velocity = pygame.Vector2(0, 0)

player_rect = player_image.get_rect(
    center=player_position
)

flight = FlightController()
flow = PhoenixFlow()
hud_font = pygame.font.Font(None, 23)
title_font = pygame.font.Font(None, 48)
PHOENIX_SHIELD_DURATION = 4.0
phoenix_shield_timer = 0.0
engine_trails = []
paused = False
score = 0
current_time = 0.0

PLAYER_MAX_HEALTH = 100
player_health = PLAYER_MAX_HEALTH


# PHOENIX ENERGY / NEAR MISS SYSTEM

PHOENIX_NEAR_MISS_GAIN = 12

# How close a hostile shot must pass to count as a near miss.
NEAR_MISS_RADIUS = 48

near_miss_flash_timer = 0
NEAR_MISS_FLASH_TIME = 0.22


# PLAYER AIMING

last_mouse_position = pygame.Vector2(
    pygame.mouse.get_pos()
)

aim_direction = pygame.Vector2(1, 0)

MOUSE_AIM_THRESHOLD = 2


# PLAYER COMBAT SETTINGS

CANNON_RANGE = 260
MISSILE_RANGE = 340

FIRE_HALF_ANGLE = 45

BULLET_SPEED = 700
BULLET_DAMAGE = 20
BULLET_COOLDOWN = 0.22

MISSILE_SPEED = 320
MISSILE_DAMAGE = 60
MISSILE_COOLDOWN = 1.8

last_bullet_time = 0
last_missile_time = 0


# ENEMY SETTINGS

MAX_ENEMIES = 4
ENEMY_HEALTH = 100

ENEMY_STOP_DISTANCE = 170

RESPAWN_DELAY = 1.4
last_respawn_time = 0

ENEMY_SHOOT_RANGE = 300
ENEMY_BULLET_SPEED = 360
ENEMY_BULLET_DAMAGE = 8

ENEMY_BULLET_COOLDOWN_MIN = 1.0
ENEMY_BULLET_COOLDOWN_MAX = 1.8


# GAME OBJECTS

enemies = []
bullets = []
missiles = []
enemy_bullets = []


def spawn_enemy():

    side = random.choice(
        ["top", "bottom", "left", "right"]
    )

    margin = 50

    if side == "top":

        position = (
            random.randint(
                margin,
                SCREEN_WIDTH - margin
            ),
            -40
        )

    elif side == "bottom":

        position = (
            random.randint(
                margin,
                SCREEN_WIDTH - margin
            ),
            SCREEN_HEIGHT + 40
        )

    elif side == "left":

        position = (
            -40,
            random.randint(
                margin,
                SCREEN_HEIGHT - margin
            )
        )

    else:

        position = (
            SCREEN_WIDTH + 40,
            random.randint(
                margin,
                SCREEN_HEIGHT - margin
            )
        )

    enemy = {
        "pos": pygame.Vector2(position),

        "rect": pygame.Rect(
            0,
            0,
            55,
            55
        ),

        "speed": random.randint(
            75,
            115
        ),

        "health": ENEMY_HEALTH,

        "last_shot": 0,

        "shoot_cooldown": random.uniform(
            ENEMY_BULLET_COOLDOWN_MIN,
            ENEMY_BULLET_COOLDOWN_MAX
        ),
    }

    enemy["rect"].center = position

    enemies.append(enemy)


# INITIAL ENEMIES

for _ in range(MAX_ENEMIES):
    spawn_enemy()


# MAIN GAME LOOP

screen.fill((10, 15, 25))
frozen_frame = screen.copy()

running = True

while running:

    # TIME

    dt = min(clock.tick(FPS) / 1000, 0.05)

    # EVENTS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p) and player_health > 0:
                paused = not paused
                last_mouse_position = pygame.Vector2(pygame.mouse.get_pos())
            elif event.key == pygame.K_e and not paused and player_health > 0:
                if flow.consume():
                    phoenix_shield_timer = PHOENIX_SHIELD_DURATION
            elif event.key == pygame.K_r and player_health <= 0:
                player_position.update(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                player_velocity.update(0, 0)
                player_rect.center = player_position
                aim_direction.update(1, 0)
                last_mouse_position = pygame.Vector2(pygame.mouse.get_pos())
                player_health = PLAYER_MAX_HEALTH
                flight = FlightController()
                flow = PhoenixFlow()
                phoenix_shield_timer = 0.0
                near_miss_flash_timer = 0.0
                score = 0
                current_time = 0.0
                last_bullet_time = last_missile_time = last_respawn_time = 0.0
                enemies.clear()
                bullets.clear()
                missiles.clear()
                enemy_bullets.clear()
                engine_trails.clear()
                for _ in range(MAX_ENEMIES):
                    spawn_enemy()
                paused = False

    if not running:
        break

    # Freeze the simulation clock while paused or after defeat.
    if paused or player_health <= 0:
        screen.blit(frozen_frame, (0, 0))
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((5, 10, 20, 190))
        screen.blit(shade, (0, 0))
        message = "PAUSED" if paused else "FLIGHT ENDED"
        hint = "P / Esc to resume" if paused else "R to restart"
        title = title_font.render(message, True, (255, 220, 120))
        text = hud_font.render(hint, True, (230, 235, 245))
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))
        screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 25)))
        pygame.display.flip()
        continue

    current_time += dt
    near_miss_flash_timer = max(0.0, near_miss_flash_timer - dt)
    phoenix_shield_timer = max(0.0, phoenix_shield_timer - dt)

    # MOUSE AIMING

    current_mouse_position = pygame.Vector2(
        pygame.mouse.get_pos()
    )

    mouse_movement = (
        current_mouse_position
        - last_mouse_position
    )

    if (
        mouse_movement.length()
        >= MOUSE_AIM_THRESHOLD
    ):

        new_aim_direction = (
            current_mouse_position
            - player_position
        )

        if new_aim_direction.length() != 0:

            aim_direction = (
                new_aim_direction.normalize()
            )

        last_mouse_position = (
            current_mouse_position
        )


    # FLIGHT MODEL V2: thrust, braking, lateral banking and afterburner.
    keys = pygame.key.get_pressed()
    player_velocity = flight.update(player_velocity, aim_direction, keys, dt)

    # MOVE PLAYER

    player_position += (
        player_velocity
        * dt
    )


    # SCREEN BOUNDARIES

    half_width = player_rect.width / 2
    half_height = player_rect.height / 2

    if player_position.x < half_width:

        player_position.x = half_width
        player_velocity.x = max(
            0,
            player_velocity.x
        )

    if (
        player_position.x
        > SCREEN_WIDTH - half_width
    ):

        player_position.x = (
            SCREEN_WIDTH - half_width
        )

        player_velocity.x = min(
            0,
            player_velocity.x
        )

    if player_position.y < half_height:

        player_position.y = half_height
        player_velocity.y = max(
            0,
            player_velocity.y
        )

    if (
        player_position.y
        > SCREEN_HEIGHT - half_height
    ):

        player_position.y = (
            SCREEN_HEIGHT - half_height
        )

        player_velocity.y = min(
            0,
            player_velocity.y
        )


    # ROTATE PLAYER

    angle = math.degrees(
        math.atan2(
            -aim_direction.y,
            aim_direction.x
        )
    )

    rotated_player = (
        pygame.transform.rotate(
            player_image,
            angle - 90  # Kenney ship artwork points up by default.
        )
    )

    rotated_rect = (
        rotated_player.get_rect(
            center=(
                round(player_position.x),
                round(player_position.y)
            )
        )
    )

    player_rect.center = (
        round(player_position.x),
        round(player_position.y)
    )


    flow.update(dt, player_velocity.length(), flight.max_speed, flight.is_boosting)

    # Short engine trails show momentum and make boost easy to read.
    engine_trails = [(pos, life - dt, boosted) for pos, life, boosted in engine_trails if life > dt]
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        engine_trails.append((player_position - aim_direction * 14, 0.3, flight.is_boosting))

    # ENEMY MOVEMENT

    for enemy in enemies:

        to_player = (
            player_position
            - enemy["pos"]
        )

        distance_to_player = (
            to_player.length()
        )

        if (
            distance_to_player
            > ENEMY_STOP_DISTANCE
            and distance_to_player != 0
        ):

            enemy_direction = (
                to_player.normalize()
            )

            enemy["pos"] += (
                enemy_direction
                * enemy["speed"]
                * dt
            )

        enemy["rect"].center = (
            round(enemy["pos"].x),
            round(enemy["pos"].y)
        )


    # ENEMY SHOOTING

    for enemy in enemies:

        to_player = (
            player_position
            - enemy["pos"]
        )

        distance_to_player = (
            to_player.length()
        )

        if (
            distance_to_player
            <= ENEMY_SHOOT_RANGE
            and distance_to_player != 0
        ):

            if (
                current_time
                - enemy["last_shot"]
                >= enemy["shoot_cooldown"]
            ):

                shot_direction = (
                    to_player.normalize()
                )

                enemy_bullets.append(
                    {
                        "pos": pygame.Vector2(
                            enemy["pos"]
                        ),

                        "direction": shot_direction,

                        # Prevents one projectile from
                        # rewarding repeated near misses.
                        "near_miss_awarded": False,
                    }
                )

                enemy["last_shot"] = (
                    current_time
                )

                enemy["shoot_cooldown"] = (
                    random.uniform(
                        ENEMY_BULLET_COOLDOWN_MIN,
                        ENEMY_BULLET_COOLDOWN_MAX
                    )
                )


    # FIND TARGETS IN FRONT

    cannon_target = None
    cannon_target_distance = CANNON_RANGE

    missile_target = None
    missile_target_distance = MISSILE_RANGE

    for enemy in enemies:

        to_enemy = (
            enemy["pos"]
            - player_position
        )

        distance = to_enemy.length()

        if distance == 0:
            continue

        enemy_direction = (
            to_enemy.normalize()
        )

        dot = max(
            -1,
            min(
                1,
                aim_direction.dot(
                    enemy_direction
                )
            )
        )

        angle_to_enemy = (
            math.degrees(
                math.acos(dot)
            )
        )

        if (
            distance < cannon_target_distance
            and angle_to_enemy
            <= FIRE_HALF_ANGLE
        ):

            cannon_target_distance = distance
            cannon_target = enemy

        if (
            distance < missile_target_distance
            and angle_to_enemy
            <= FIRE_HALF_ANGLE
        ):

            missile_target_distance = distance
            missile_target = enemy


    # AUTOMATIC CANNON

    if cannon_target is not None:

        if (
            current_time
            - last_bullet_time
            >= BULLET_COOLDOWN
        ):

            bullet_position = (
                pygame.Vector2(
                    player_position
                )
            )

            bullet_direction = (
                cannon_target["pos"]
                - bullet_position
            )

            if bullet_direction.length() != 0:

                bullet_direction = (
                    bullet_direction.normalize()
                )

                bullets.append(
                    {
                        "pos": bullet_position,
                        "direction": bullet_direction,
                    }
                )

                last_bullet_time = current_time


    # HOMING MISSILE

    if missile_target is not None:

        if (
            current_time
            - last_missile_time
            >= MISSILE_COOLDOWN
        ):

            missiles.append(
                {
                    "pos": pygame.Vector2(
                        player_position
                    ),

                    "target": missile_target,
                }
            )

            last_missile_time = current_time


    # PLAYER BULLETS

    for bullet in bullets[:]:

        bullet["pos"] += (
            bullet["direction"]
            * BULLET_SPEED
            * dt
        )

        bullet_rect = pygame.Rect(
            round(bullet["pos"].x) - 4,
            round(bullet["pos"].y) - 4,
            8,
            8
        )

        hit_enemy = None

        for enemy in enemies:

            if bullet_rect.colliderect(
                enemy["rect"]
            ):

                hit_enemy = enemy
                break

        if hit_enemy is not None:

            hit_enemy["health"] -= (
                BULLET_DAMAGE
            )

            bullets.remove(bullet)

        elif not screen.get_rect().colliderect(
            bullet_rect
        ):

            bullets.remove(bullet)


    # MISSILES

    for missile in missiles[:]:

        target = missile["target"]

        if target not in enemies:

            missiles.remove(missile)
            continue

        missile_direction = (
            target["pos"]
            - missile["pos"]
        )

        if missile_direction.length() != 0:

            missile_direction = (
                missile_direction.normalize()
            )

            missile["pos"] += (
                missile_direction
                * MISSILE_SPEED
                * dt
            )

        missile_rect = pygame.Rect(
            round(missile["pos"].x) - 7,
            round(missile["pos"].y) - 7,
            14,
            14
        )

        if missile_rect.colliderect(
            target["rect"]
        ):

            target["health"] -= (
                MISSILE_DAMAGE
            )

            missiles.remove(missile)


    # ENEMY BULLETS + NEAR MISS DETECTION

    for enemy_bullet in enemy_bullets[:]:

        enemy_bullet["pos"] += (
            enemy_bullet["direction"]
            * ENEMY_BULLET_SPEED
            * dt
        )

        enemy_bullet_rect = pygame.Rect(
            round(
                enemy_bullet["pos"].x
            ) - 5,

            round(
                enemy_bullet["pos"].y
            ) - 5,

            10,
            10
        )


        # DIRECT HIT

        if enemy_bullet_rect.colliderect(
            player_rect
        ):

            if phoenix_shield_timer <= 0:
                player_health -= ENEMY_BULLET_DAMAGE
                flow.break_flow()

            player_health = max(
                0,
                player_health
            )

            enemy_bullets.remove(
                enemy_bullet
            )

            continue


        # NEAR MISS

        distance_from_player = (
            enemy_bullet["pos"]
            .distance_to(
                player_position
            )
        )

        if (
            distance_from_player
            <= NEAR_MISS_RADIUS
            and (enemy_bullet["pos"] - player_position).dot(enemy_bullet["direction"]) > 0
            and not enemy_bullet[
                "near_miss_awarded"
            ]
        ):

            flow.reward_maneuver(PHOENIX_NEAR_MISS_GAIN)

            enemy_bullet[
                "near_miss_awarded"
            ] = True

            near_miss_flash_timer = (
                NEAR_MISS_FLASH_TIME
            )


        # REMOVE OFFSCREEN BULLETS

        if not screen.get_rect().colliderect(
            enemy_bullet_rect
        ):

            enemy_bullets.remove(
                enemy_bullet
            )


    # REMOVE DEFEATED ENEMIES

    for enemy in enemies[:]:

        if enemy["health"] <= 0:

            enemies.remove(enemy)
            score += 100


    # RESPAWN ENEMIES

    if (
        len(enemies) < MAX_ENEMIES
        and current_time
        - last_respawn_time
        >= RESPAWN_DELAY
    ):

        spawn_enemy()

        last_respawn_time = (
            current_time
        )


    # DRAW

    screen.fill(
        (10, 15, 25)
    )


    for trail_pos, life, boosted in engine_trails:
        color = (255, 160, 50) if boosted else (80, 160, 220)
        color = tuple(round(channel * life / 0.3) for channel in color)
        pygame.draw.circle(screen, color, trail_pos, max(1, round(life * (20 if boosted else 12))))

    # CANNON RANGE

    pygame.draw.circle(
        screen,
        (40, 70, 90),
        (
            round(player_position.x),
            round(player_position.y)
        ),
        CANNON_RANGE,
        1
    )


    # NEAR MISS RING
    # Visible only briefly when a near miss succeeds.

    if near_miss_flash_timer > 0:

        pygame.draw.circle(
            screen,
            (255, 150, 40),
            (
                round(player_position.x),
                round(player_position.y)
            ),
            NEAR_MISS_RADIUS,
            2
        )


    # ENEMIES

    for enemy in enemies:

        pygame.draw.rect(
            screen,
            (200, 50, 50),
            enemy["rect"]
        )

        health_width = int(
            55
            * max(
                enemy["health"],
                0
            )
            / ENEMY_HEALTH
        )

        pygame.draw.rect(
            screen,
            (60, 60, 60),
            (
                enemy["rect"].x,
                enemy["rect"].y - 10,
                55,
                5
            )
        )

        pygame.draw.rect(
            screen,
            (50, 200, 80),
            (
                enemy["rect"].x,
                enemy["rect"].y - 10,
                health_width,
                5
            )
        )


    # TARGET LOCK

    active_target = (
        cannon_target
        or missile_target
    )

    if active_target is not None:

        lock_rect = (
            active_target["rect"]
            .inflate(
                18,
                18
            )
        )

        pygame.draw.rect(
            screen,
            (255, 220, 80),
            lock_rect,
            2
        )


    # PLAYER BULLETS

    for bullet in bullets:

        pygame.draw.circle(
            screen,
            (240, 240, 120),
            (
                round(
                    bullet["pos"].x
                ),

                round(
                    bullet["pos"].y
                )
            ),
            4
        )


    # MISSILES

    for missile in missiles:

        pygame.draw.circle(
            screen,
            (255, 120, 40),
            (
                round(
                    missile["pos"].x
                ),

                round(
                    missile["pos"].y
                )
            ),
            7
        )


    # ENEMY BULLETS

    for enemy_bullet in enemy_bullets:

        pygame.draw.circle(
            screen,
            (255, 80, 80),
            (
                round(
                    enemy_bullet["pos"].x
                ),

                round(
                    enemy_bullet["pos"].y
                )
            ),
            5
        )


    # PLAYER

    screen.blit(
        rotated_player,
        rotated_rect
    )


    if phoenix_shield_timer > 0:
        pygame.draw.circle(screen, (255, 190, 70), player_rect.center, 30, 3)

    # PLAYER HEALTH BAR

    health_bar_width = 220

    health_ratio = (
        player_health
        / PLAYER_MAX_HEALTH
    )

    pygame.draw.rect(
        screen,
        (55, 55, 55),
        (
            20,
            20,
            health_bar_width,
            18
        )
    )

    pygame.draw.rect(
        screen,
        (60, 210, 90),
        (
            20,
            20,
            int(
                health_bar_width
                * health_ratio
            ),
            18
        )
    )


    # PHOENIX ENERGY BAR

    energy_bar_width = 220

    energy_ratio = (
        flow.energy_ratio
    )

    pygame.draw.rect(
        screen,
        (55, 55, 55),
        (
            20,
            50,
            energy_bar_width,
            14
        )
    )

    pygame.draw.rect(
        screen,
        (255, 140, 40),
        (
            20,
            50,
            int(
                energy_bar_width
                * energy_ratio
            ),
            14
        )
    )


    # FLIGHT HUD
    hud_lines = [
        ("HULL", (250, 250, 250), (250, 20)),
        (f"{flow.state_name}  |  Flow x{flow.flow:.1f}", (255, 180, 70), (250, 48)),
        (f"BOOST {flight.boost_energy:.0f}%", (100, 200, 255), (250, 77)),
        (f"SPEED {player_velocity.length():.0f}   SCORE {score}", (220, 230, 240), (20, 106)),
        ("Mouse aim | W/Up thrust | S/Down brake | A/D bank | Shift + thrust boost", (170, 190, 210), (20, SCREEN_HEIGHT - 47)),
        ("E Phoenix shield (full energy) | P/Esc pause", (170, 190, 210), (20, SCREEN_HEIGHT - 25)),
    ]
    if phoenix_shield_timer > 0:
        hud_lines.append((f"PHOENIX SHIELD {phoenix_shield_timer:.1f}s", (255, 210, 80), (20, 135)))
    elif flow.ready:
        hud_lines.append(("PRESS E: PHOENIX SHIELD", (255, 210, 80), (20, 135)))
    pygame.draw.rect(screen, (45, 55, 65), (20, 80, 220, 14))
    pygame.draw.rect(screen, (80, 180, 245), (20, 80, round(220 * flight.boost_ratio), 14))
    for label, color, position in hud_lines:
        screen.blit(hud_font.render(label, True, color), position)

    frozen_frame = screen.copy()
    pygame.display.flip()


# QUIT

pygame.quit()
