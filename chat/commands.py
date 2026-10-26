"""Parse Twitch chat lines into game commands."""
from game.events import COMMANDS


def parse_chat(text):
    """Return (command, arg) for '!lock', '!lock 4', '!shuffle' ..., else None."""
    parts = str(text).strip().split()
    if not parts or not parts[0].startswith("!"):
        return None
    name = parts[0][1:].lower()
    if name not in COMMANDS:
        return None
    arg = None
    if name == "lock" and len(parts) > 1 and parts[1].isdigit():
        arg = int(parts[1])
    return name, arg
