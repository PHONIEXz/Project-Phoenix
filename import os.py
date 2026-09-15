import os
import random
import pygame
import math
from pathlib import Path

from GameSettings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE

pygame.init()

screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT)
)