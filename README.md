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

Launch shows a loading screen and prints `[startup]` stage messages. Audio stays off during startup to avoid waiting on a sound device. Press M after the menu opens to enable effects. If launch stalls, run `python -u MainContents.py` and report the last `[startup]` line. If enabling sound stalls instead, report the `[audio]` line.

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
| E | Spend full Phoenix energy to summon the bird for 50 seconds |
| B | Switch Phoenix between Attack and Guard modes |
| H | Open the hangar; gameplay pauses while shopping |
| M | Mute or unmute effects |
| P / Esc | Pause or resume |
| R after defeat | Restart |
| Q after defeat | Return to the menu |

The cannon assists within a narrow 12-degree half-angle and 620-pixel targeting range. Missiles acquire within a wider 32-degree half-angle and 850-pixel range; hold the target for 0.7 seconds. Rearming takes 2.4 seconds. A missile that loses its target continues forward until its lifetime ends.

## Missions and Phoenix Flow

Clear all incoming aircraft to finish a wave. A six-second repair break restores up to 22 hull points, then the next wave begins. Waves grow to at most 20 total enemies, with no more than six active at once. Every tenth wave starts with a boss. Hunters weave, flankers circle, and bombers fire spread shots.

Fast flying slowly builds Phoenix energy. Close evades and defeated aircraft build energy and a Flow multiplier up to x3. Damage breaks Flow. Full energy summons Phoenix for 50 seconds of simulation time. Attack mode hunts aircraft with powerful homing fire. Guard mode creates a 185-pixel no-go area, repels enemies, intercepts hostile shots, and protects against contact damage. Press B to switch modes before or during activation. The timer freezes while paused or in the hangar; Phoenix energy cannot rebuild while the bird is active. Defeated aircraft award 100 score; a boss awards 1,000.

The radar maps the whole sector and red edge arrows point toward offscreen aircraft. Losing window focus pauses play automatically. Banking currently changes lateral acceleration without tilting the sprite.

## Coins, aircraft, and drone support

Coins are earned through play, without real-money purchases. A regular aircraft awards 18 coins, a boss awards 150, and a cleared wave awards 25 + 5 x wave number. Coins, owned aircraft, the equipped jet, purchased weapon levels, and purchased drone slots survive defeat and new sorties.

Aircraft are not cosmetic-only. Each jet has a distinct weapon system: repeaters fire twin bolts, spread systems fire multiple angled shots, and siege or lance systems trade rate of fire for heavier hits. In the hangar, select an owned jet and press **I** to buy a weapon upgrade. Up to five levels increase its damage, reload speed, hull, and top speed. The detail panel shows the weapon name, shot count, level, and live stats.

Press H for the hangar. Click a jet card or use A/D to select it, then click Buy/Equip or press Enter. Jet roles trade hull, speed, and cannon strength. Equipping during a sortie preserves the percentage of hull remaining, so changing jets cannot provide free repairs. New sorties start with the equipped jet at full hull.

| Ship | Jet | Role | Coin price |
| --- | --- | --- | --- |
| 0011 | Ember | Balanced | Free |
| 0010 | Swift | Scout | 120 |
| 0009 | Vanguard | Heavy | 180 |
| 0008 | Talon | Striker | 250 |
| 0007 | Bulwark | Guardian | 330 |
| 0006 | Comet | Interceptor | 420 |
| 0005 | Striker | Assault | 520 |
| 0004 | Sentinel | Heavy | 650 |
| 0003 | Wraith | Interceptor | 780 |
| 0002 | Tempest | Striker | 950 |
| 0001 | Aegis | Guardian | 1150 |
| 0000 | Sunflare | Balanced | 1400 |

Every sortie has one free, invulnerable escort drone. It orbits the player and automatically fires at nearby aircraft. Buy two additional permanent drone slots for 350 and 750 coins using U or the hangar button. All unlocked drones arrive again each wave; their firepower grows with the wave number, up to a cap.

Progress is saved atomically after rewards and purchases in `Data/progress.json`, which is excluded from Git. Save errors appear in the HUD or hangar. Purchases roll back if saving fails. An unreadable existing save is preserved; back it up before repairing or moving it to start fresh. Tests use temporary save locations and never spend your actual game coins.

## Checks

```bash
python -m unittest discover -s tests -v
```

The suite covers flight, boost, energy, targeting and missile guidance, swept collisions, wave pacing, bosses, drones, both Phoenix modes, hangar interactions, all aircraft, atomic progress saves, purchase validation, pause, defeat, restart, optional audio, and all display states. SDL's dummy display runs these checks without opening a window.

Scenery and effects are generated in code. Aircraft use the existing Kenney ship assets. No extra images, sounds, network services, or paid dependencies are required. Local playtesting is still needed to assess flight feel and difficulty on your device.
