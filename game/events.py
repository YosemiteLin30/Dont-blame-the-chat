"""Chat events: shared cooldowns, durations and their effects on the game."""
COMMANDS = ("lock", "shuffle", "blackout", "chaos", "speed")


class EventSystem:
    def __init__(self, game):
        self.game = game
        self.cooldown = {name: 0.0 for name in COMMANDS}
        self.locked = {}            # room -> seconds left
        self.blackout_left = 0.0
        self.speed_left = 0.0
        self.shuffle_left = 0.0     # only for the "active effects" display

    def update(self, dt):
        for name in self.cooldown:
            self.cooldown[name] = max(0.0, self.cooldown[name] - dt)
        self.blackout_left = max(0.0, self.blackout_left - dt)
        self.speed_left = max(0.0, self.speed_left - dt)
        self.shuffle_left = max(0.0, self.shuffle_left - dt)
        for room in list(self.locked):
            self.locked[room] -= dt
            if self.locked[room] <= 0:
                del self.locked[room]

    def active(self):
        """Label and seconds left of every running effect (for the HUD and panel)."""
        out = [(f"LOCK ROOM {r}", t) for r, t in self.locked.items()]
        if self.blackout_left > 0:
            out.append(("BLACKOUT", self.blackout_left))
        if self.shuffle_left > 0:
            out.append(("ROOM SHUFFLE", self.shuffle_left))
        if self.speed_left > 0:
            out.append(("ANGELS +30%", self.speed_left))
        return out

    # -- triggering -----------------------------------------------------------
    def trigger(self, name, arg=None):
        """Try to run a chat event. Returns (accepted, message); failures cost no cooldown."""
        g = self.game
        if name not in COMMANDS:
            return False, f"Unknown command: {name}"
        if not g.running():
            return False, "The game is over."
        if self.cooldown[name] > 0:
            return False, f"!{name} is on cooldown ({self.cooldown[name]:.0f}s)"
        cfg = g.cfg["events"][name]
        if name == "lock":
            ok, msg = self._lock(arg, cfg["duration"])
        elif name == "shuffle":
            ok, msg = self._shuffle(cfg["duration"])
        elif name == "blackout":
            ok, msg = self._blackout(cfg["duration"])
        elif name == "chaos":
            ok, msg = self._chaos(cfg["duration"])
        else:
            self.speed_left = cfg["duration"]
            ok, msg = True, f"Angels are faster for {cfg['duration']}s"
        if ok:
            self.cooldown[name] = cfg["cooldown"]
        return ok, msg

    def _lock(self, arg, duration):
        g, L = self.game, self.game.layout
        if arg is not None and arg not in L.rooms:
            return False, "No such room."
        candidates = [arg] if arg is not None else [r for r in L.rooms]
        random_pick = arg is None
        g.rng.shuffle(candidates)
        for room in candidates:
            if room == g.player_room() or room in self.locked:
                continue
            seals = [L.door_rect(room, n) for n in L.neighbors(room)]
            if any(_near(g.player, r, g.cfg["player"]["radius"] + 30) for r in seals):
                continue
            self.locked[room] = duration
            return True, f"Room {room} sealed for {duration}s"
        return False, "Cannot lock that room right now." if not random_pick else "No room can be locked right now."

    def _shuffle(self, duration):
        if not self.game.shuffle_rooms():
            return False, "Nothing to shuffle."
        self.shuffle_left = duration
        return True, "The rooms were shuffled"

    def _blackout(self, duration):
        if not self.game.light_possible():
            return False, "The light is already out."
        self.blackout_left = duration
        return True, f"Flashlight off for {duration}s"

    def _chaos(self, duration):
        if self.game.light_possible():
            self.blackout_left = duration
        self.game.shuffle_rooms()
        self.shuffle_left = duration
        return True, "CHAOS: blackout and room shuffle"


def _near(player, rect, dist):
    from .geometry import circle_hits_rect
    return circle_hits_rect(player.x, player.y, dist, rect)
