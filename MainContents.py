import pygame
import math
import random
from pathlib import Path

from GameSettings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE


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

PLAYER_ACCELERATION = 520
PLAYER_MAX_SPEED = 420
PLAYER_BRAKE_ACCELERATION = 620
PLAYER_DRAG = 0.985

PLAYER_MAX_HEALTH = 100
player_health = PLAYER_MAX_HEALTH


# PHOENIX ENERGY / NEAR MISS SYSTEM

PHOENIX_MAX_ENERGY = 100
PHOENIX_NEAR_MISS_GAIN = 12

# How close a hostile shot must pass to count as a near miss.
NEAR_MISS_RADIUS = 48

phoenix_energy = 0

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

running = True

while running:

    # TIME

    dt = clock.tick(FPS) / 1000

    current_time = (
        pygame.time.get_ticks()
        / 1000
    )

    if near_miss_flash_timer > 0:

        near_miss_flash_timer -= dt


    # EVENTS

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False


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


    # FLIGHT MODEL V2 - STAGE 1

    keys = pygame.key.get_pressed()

    if (
        keys[pygame.K_w]
        or keys[pygame.K_UP]
    ):

        player_velocity += (
            aim_direction
            * PLAYER_ACCELERATION
            * dt
        )

    if (
        keys[pygame.K_s]
        or keys[pygame.K_DOWN]
    ):

        if player_velocity.length() > 0:

            brake_direction = (
                -player_velocity.normalize()
            )

            player_velocity += (
                brake_direction
                * PLAYER_BRAKE_ACCELERATION
                * dt
            )

            if player_velocity.length() < 15:

                player_velocity.update(
                    0,
                    0
                )


    # LIMIT SPEED

    if (
        player_velocity.length()
        > PLAYER_MAX_SPEED
    ):

        player_velocity.scale_to_length(
            PLAYER_MAX_SPEED
        )


    # DRAG

    player_velocity *= (
        PLAYER_DRAG ** (dt * FPS)
    )


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
            angle
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

            player_health -= (
                ENEMY_BULLET_DAMAGE
            )

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
            and not enemy_bullet[
                "near_miss_awarded"
            ]
        ):

            phoenix_energy += (
                PHOENIX_NEAR_MISS_GAIN
            )

            phoenix_energy = min(
                PHOENIX_MAX_ENERGY,
                phoenix_energy
            )

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
        phoenix_energy
        / PHOENIX_MAX_ENERGY
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


    pygame.display.flip()


# QUIT

pygame.quit()
