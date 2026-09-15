# Project Phoenix

An arcade jet survival game built with Pygame. The Flight Operations update adds a scrolling 3600 x 2600 battlefield, larger aircraft, islands and an airstrip, camera follow, shadows, clouds, tracer fire, missile trails, explosions, radar, and synthesized sound effects.

## Run on Kali Linux

From the project folder, use Kali's packaged Pygame:

```bash
sudo apt update
sudo apt install python3-pygame python3-venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python MainContents.py
```

If you already created this environment, activate it and run the game; installation is only needed once.

## Other Python environments

Use Python 3.10 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python MainContents.py
```

On Windows, activate with `.venv\Scripts\activate`.

## Controls

| Input | Action |
| --- | --- |
| Enter / Launch button | Start a sortie |
| Move mouse | Aim the nose; a stationary mouse preserves heading |
| W / Up | Forward thrust with momentum |
| S / Down | Brake without reversing |
| A / Left, D / Right | Accelerate sideways relative to the nose |
| Shift + thrust | Afterburner; release Shift after depletion to use it again |
| Left mouse | Hold to fire the cannon |
| Right mouse / Space | Launch a missile after acquiring a target lock |
| F | Toggle automatic weapon assist |
| E | Spend full Phoenix energy on a four-second shield |
| M | Mute or unmute effects |
| P / Esc | Pause or resume |
| R after defeat | Restart |
| Q after defeat | Return to the menu |

The cannon assists within a narrow 12-degree half-angle and 620-pixel targeting range. Missiles acquire within a wider 32-degree half-angle and 850-pixel range; hold the target for 0.7 seconds. Rearming takes 2.4 seconds. A missile that loses its target continues forward until its lifetime ends.

## Missions and Phoenix Flow

Clear all incoming aircraft to finish a wave. A 3.5-second repair break restores up to 12 hull points, then the next wave begins. Waves grow to at most 24 total enemies, with no more than eight active at once. Every ninth wave starts with a boss. Hunters weave, flankers circle, and bombers fire spread shots.

Fast flying slowly builds Phoenix energy. Close evades and defeated aircraft build energy and a Flow multiplier up to x3. Damage breaks Flow. Full energy powers a temporary shield against hostile shots and contact damage. Defeated aircraft award 100 score; a boss awards 1,000.

The radar maps the whole sector and red edge arrows point toward offscreen aircraft. Losing window focus pauses play automatically. Banking currently changes lateral acceleration without tilting the sprite.

## Checks

```bash
python -m unittest discover -s tests -v
```

The suite covers flight, boost, energy, cone targeting, missile lock and guidance, swept collisions, wave pacing, bosses, shield protection, pause, defeat, restart, optional audio, and all display states. SDL's dummy display runs these checks without opening a window.

Scenery and effects are generated in code. Aircraft use the existing Kenney ship assets. No extra images, sounds, network services, or paid dependencies are required. Local playtesting is still needed to assess flight feel and difficulty on your device.
