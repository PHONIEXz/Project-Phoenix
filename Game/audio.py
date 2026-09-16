"""Small original synthesized effects; gracefully optional on silent systems."""

import math
from array import array

import pygame


class Audio:
    def __init__(self):
        # Launch never opens an audio device. M opts into sound after the menu.
        self.muted = True
        self.sounds = {}
        self.error = ""

    def toggle(self):
        if not self.muted:
            self.muted = True
            if pygame.mixer.get_init():
                pygame.mixer.stop()
            return
        if self.sounds:
            self.muted = False
            return
        print("[audio] Opening sound device...", flush=True)
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            rate, _, channels = pygame.mixer.get_init()
            for name, frequency, duration in (("cannon", 190, 0.07), ("missile", 420, 0.22), ("hit", 90, 0.12), ("explode", 55, 0.35), ("ready", 850, 0.18)):
                samples = array("h")
                count = int(rate * duration)
                for i in range(count):
                    fade = (1 - i / count) ** 2
                    phase = 2 * math.pi * frequency * (i / rate) * (1 - 0.3 * i / count)
                    value = round(7000 * fade * (math.sin(phase) + 0.25 * math.sin(phase * 2)))
                    samples.extend([value] * channels)
                self.sounds[name] = pygame.mixer.Sound(buffer=samples)
            self.muted = False
            self.error = ""
        except pygame.error:
            self.sounds.clear()
            self.error = "Sound unavailable. You can keep playing without it."

    def play(self, name):
        if not self.muted and name in self.sounds:
            self.sounds[name].play()
