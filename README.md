# Don't Blame the Chat, Blame the Game

A 2D pixel-art horror puzzle. A streamer is trapped in a dark 3x3 maze and must find three digits to work out the exit code, while Twitch chat plays the enemy: viewers lock rooms, shuffle the maze and cut the lights.

## Run
```
pip install -r requirements.txt
python main.py --sim-chat            # no Twitch needed: fake chat sends random commands
python main.py --channel yourchannel # read a real Twitch chat
```
- Control panel: http://127.0.0.1:8000/ (live state, cooldowns, event log, and buttons to trigger events by hand).
- Reading Twitch chat needs the environment variable `TWITCH_TOKEN=oauth:xxxx` (a token for your account or a bot account). Without it the game and panel still work. Never commit the token to the repository.
- Options: `--host --port --seed --db`.

## Controls
WASD to move, mouse to aim the flashlight (about 60 degrees), E to pick up a digit or enter the code at the exit, R to restart, Esc to quit.

## Rules
- Three Angels hunt you in the dark along the shortest path through the room graph. They freeze while your flashlight beam hits them with a clear line of sight.
- Digits are hidden in the corners of different rooms; press E next to one to pick it up. The exit code is the digits sorted by the room number where each was picked up (lowest first); digits from the same room keep their pickup order. Example: a 2 picked up in room 8, then a 5 and a 9 in room 4, gives 592.
- Once all three digits are found, the Angels move 30% faster and the beam narrows. Press E at the exit to enter the code. A correct code starts the final blackout: the flashlight is off, the Angels move freely, and you must reach the exit before they catch you.
- Chat commands (cooldowns are shared by all viewers):

| Command | Effect | Cooldown |
|---|---|---|
| `!lock` / `!lock 4` | Seal a room for 2 seconds | 10 s |
| `!shuffle` | Shuffle the rooms (objects and Angels move with their room) | 20 s |
| `!blackout` | Flashlight off for 3 seconds | 5 s |
| `!chaos` | Blackout plus shuffle | 30 s |
| `!speed` | Angels 30% faster for 8 seconds | 20 s |

Each viewer also has a personal 3-second cooldown to stop spam. All numbers live in `data/config.json`, and the room layout in `data/layout.json`.

Where the design document is silent, these choices were made (change them in the code or config): shuffling never moves the player's own room; `!lock` never locks the player's room or a doorway right next to the player; blackout lasts 3 seconds; `!speed` lasts 8 seconds; during the final blackout chat can still use lock, shuffle and speed.

## Project structure
| File | Contents |
|---|---|
| `game/world.py` | Game rules (player, flashlight, digits, code, win/lose); no graphics or network code |
| `game/angel.py` | Angel state machine: HUNT / FROZEN / BLOCKED |
| `game/pathfinding.py` | Breadth-first shortest path over the room graph |
| `game/events.py` | Chat events, cooldowns and durations |
| `game/render.py` | Pygame rendering and HUD |
| `game/db.py` | SQLite: one record per round, plus an event log |
| `chat/` | Command parsing, TwitchIO bot, fake chat |
| `server/` | FastAPI control panel (WebSockets) and the bridge to the game loop |
| `data/` | `config.json`, `layout.json`, and `sessions.db` (created at run time) |
| `main.py` | Starts the game, the panel and the bot |

## Tests
```
python -m pytest
```
25 tests cover geometry and pathfinding; Angel freezing, hunting, doorway crossing and locked rooms; code ordering; digit pickup and code entry; win and lose; every event and its cooldown; the database; chat parsing; the panel API and WebSocket; and drawing every game phase.

## Known limitations
- The TwitchIO bot has not been tested against a live channel. Only bot construction and command handling are tested, so try it on your own channel first.
- The bot only reads chat and never replies; results appear on the game screen and the control panel.
- Graphics are simple shapes drawn in code, with no art assets.
