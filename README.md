# Project Phoenix

A Pygame arcade jet game with mouse aiming, momentum, assisted weapons, and enemy fire.

## Run

Use Python 3.10 or newer. From the project folder:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python MainContents.py
```

On Windows, activate with `.venv\Scripts\activate` instead.

## Controls

| Input | Action |
| --- | --- |
| Move mouse | Change nose direction; a stationary mouse keeps the heading |
| W / Up | Thrust along the nose direction |
| S / Down | Brake without reversing |
| A / Left, D / Right | Bank sideways relative to the nose |
| Shift + thrust | Afterburner; release Shift after depletion to use it again |
| E | Spend full Phoenix energy on a four-second projectile shield |
| P / Esc | Pause or resume |
| R after defeat | Restart |

Cannon and homing missiles fire automatically at targets in the existing forward targeting cone. Banking currently changes lateral acceleration; it does not tilt the sprite.

The boost meter recharges after a short delay. Fast flight slowly builds Phoenix energy. Close enemy-shot evades build energy and a Flow multiplier up to x3; taking damage breaks Flow. Defeated enemies award 100 score.

## Checks

```bash
python -m unittest discover -s tests -v
```

Tests use SDL's dummy display to exercise controls, energy, pause, defeat, and restart without opening a window. Gameplay feel still needs a local play session.
