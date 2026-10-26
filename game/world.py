"""Game rules (no graphics, no network): player, flashlight, angels, digits, code and win/lose."""
import math
import random
from enum import Enum

from .angel import Angel
from .events import EventSystem
from .geometry import angle_diff, circle_hits_rect, segment_blocked
from .layout import Layout


class Phase(Enum):
    PLAYING = "playing"
    FINAL = "final"        # code entered: no flashlight, run to the exit
    WON = "won"
    LOST = "lost"


class Player:
    def __init__(self, x, y):
        self.x, self.y, self.facing = x, y, 0.0


class Digit:
    def __init__(self, value, room, x, y):
        self.value, self.room, self.x, self.y = value, room, x, y
        self.taken = False


class Game:
    def __init__(self, cfg, layout_data, seed=None):
        self.cfg = cfg
        self.layout = Layout(layout_data)
        self.rng = random.Random(seed)
        self.reset()

    def reset(self):
        L, cfg = self.layout, self.cfg
        self.events = EventSystem(self)
        self.phase = Phase.PLAYING
        self.elapsed = 0.0
        cx, cy = L.center(L.start_room)
        self.player = Player(cx, cy)
        spawns = self.rng.sample(L.angel_spawn_rooms, cfg["angels"]["count"])
        self.angels = []
        for i, room in enumerate(spawns):
            ox, oy = L.origin(room)
            fx, fy = self.rng.choice(L.digit_spawns)
            self.angels.append(Angel(i + 1, ox + fx * L.rw, oy + fy * L.rh))
        rooms = self.rng.sample(L.digit_rooms, cfg["digits"]["count"])
        values = self.rng.sample(range(10), cfg["digits"]["count"])
        self.digits = []
        for room, value in zip(rooms, values):
            ox, oy = L.origin(room)
            fx, fy = self.rng.choice(L.digit_spawns)
            self.digits.append(Digit(value, room, ox + fx * L.rw, oy + fy * L.rh))
        self.collected = []         # (value, room, order)
        self.code_entry = False
        self.code_buffer = ""
        self.message = ""
        self.message_left = 0.0

    # -- queries ----------------------------------------------------------------
    def running(self):
        return self.phase in (Phase.PLAYING, Phase.FINAL)

    def player_room(self):
        return self.layout.room_of(self.player.x, self.player.y)

    def all_digits(self):
        return len(self.collected) >= self.cfg["digits"]["count"]

    def walls(self):
        L = self.layout
        walls = L.static_walls()
        for room in self.events.locked:
            walls += [L.door_rect(room, n) for n in L.neighbors(room)]
        return walls

    def light_possible(self):
        return self.phase is Phase.PLAYING and self.events.blackout_left <= 0

    def beam_angle(self):
        f = self.cfg["flashlight"]
        return math.radians(f["narrow_angle_deg"] if self.all_digits() else f["angle_deg"])

    def is_lit(self, x, y):
        """True when the flashlight beam reaches (x, y) with a clear line of sight."""
        if not self.light_possible():
            return False
        p = self.player
        dx, dy = x - p.x, y - p.y
        if math.hypot(dx, dy) > self.cfg["flashlight"]["range"]:
            return False
        if angle_diff(math.atan2(dy, dx), p.facing) > self.beam_angle() / 2:
            return False
        return not segment_blocked((p.x, p.y), (x, y), self.walls())

    def angel_speed(self):
        a = self.cfg["angels"]
        speed = a["speed"]
        if self.all_digits():
            speed *= a["speed_boost"]
        if self.events.speed_left > 0:
            speed *= a["speed_boost"]
        return speed

    def expected_code(self):
        """Digits sorted by room number; ties keep their collection order."""
        ordered = sorted(self.collected, key=lambda c: (c[1], c[2]))
        return "".join(str(c[0]) for c in ordered)

    # -- update -------------------------------------------------------------------
    def say(self, text, seconds=3.0):
        self.message, self.message_left = text, seconds

    def update(self, dt, move=(0.0, 0.0), aim=None):
        if not self.running():
            return
        self.elapsed += dt
        self.message_left = max(0.0, self.message_left - dt)
        self.events.update(dt)
        if aim is not None:
            self.player.facing = aim
        if not self.code_entry:
            self._move_player(dt, move)
        for angel in self.angels:
            angel.update(self, dt)
        radius = self.cfg["angels"]["touch_dist"]
        if any(math.hypot(a.x - self.player.x, a.y - self.player.y) < radius for a in self.angels):
            self.phase = Phase.LOST
            self.code_entry = False
            return
        if self.phase is Phase.FINAL:
            ex, ey = self.layout.exit_point()
            if math.hypot(ex - self.player.x, ey - self.player.y) < self.cfg["exit"]["touch_dist"]:
                self.phase = Phase.WON

    def _move_player(self, dt, move):
        mx, my = move
        norm = math.hypot(mx, my)
        if norm == 0:
            return
        step = self.cfg["player"]["speed"] * dt / norm
        r, p, walls = self.cfg["player"]["radius"], self.player, self.walls()
        nx = p.x + mx * step
        if not any(circle_hits_rect(nx, p.y, r, w) for w in walls):
            p.x = nx
        ny = p.y + my * step
        if not any(circle_hits_rect(p.x, ny, r, w) for w in walls):
            p.y = ny

    # -- interaction ----------------------------------------------------------------
    def interact(self):
        """E key: pick up a nearby digit or start entering the code at the exit."""
        if self.phase is not Phase.PLAYING or self.code_entry:
            return
        p = self.player
        for d in self.digits:
            if not d.taken and math.hypot(d.x - p.x, d.y - p.y) <= self.cfg["digits"]["pickup_dist"]:
                d.taken = True
                self.collected.append((d.value, self.player_room(), len(self.collected)))
                self.say(f"Picked up a {d.value}")
                if self.all_digits():
                    self.say("All digits found! The Angels are faster and your light is narrower.", 4.0)
                return
        ex, ey = self.layout.exit_point()
        if math.hypot(ex - p.x, ey - p.y) <= self.cfg["exit"]["interact_dist"]:
            if self.all_digits():
                self.code_entry, self.code_buffer = True, ""
            else:
                self.say("The door needs a 3-digit code.")

    def type_digit(self, ch):
        if self.code_entry and ch.isdigit() and len(self.code_buffer) < len(self.digits):
            self.code_buffer += ch
            if len(self.code_buffer) == len(self.digits):
                self.submit_code()

    def backspace(self):
        self.code_buffer = self.code_buffer[:-1]

    def cancel_entry(self):
        self.code_entry, self.code_buffer = False, ""

    def submit_code(self):
        if not self.code_entry:
            return False
        ok = self.code_buffer == self.expected_code()
        self.code_buffer = ""
        if ok:
            self.code_entry = False
            self.phase = Phase.FINAL
            self.say("Blackout! The door is open. RUN!", 4.0)
        else:
            self.say("Wrong code.")
        return ok

    # -- shuffle ----------------------------------------------------------------------
    def shuffle_rooms(self):
        """Rearrange the contents of every room except the player's; objects move with their room."""
        L = self.layout
        keep = self.player_room()
        rooms = [r for r in L.rooms if r != keep]
        perm = rooms[:]
        for _ in range(20):
            self.rng.shuffle(perm)
            if perm != rooms:
                break
        mapping = dict(zip(rooms, perm))
        mapping[keep] = keep

        def moved(x, y):
            ox, oy = L.origin(L.room_of(x, y))
            nx, ny = L.origin(mapping[L.room_of(x, y)])
            return nx + (x - ox), ny + (y - oy)

        for a in self.angels:
            a.x, a.y = moved(a.x, a.y)
        for d in self.digits:
            if not d.taken:
                d.x, d.y = moved(d.x, d.y)
                d.room = L.room_of(d.x, d.y)
        return perm != rooms

    # -- panel snapshot -------------------------------------------------------------------
    def snapshot(self):
        return {
            "phase": self.phase.value,
            "elapsed": round(self.elapsed, 1),
            "player_room": self.player_room(),
            "digits_found": len(self.collected),
            "digits_total": self.cfg["digits"]["count"],
            "angels": [{"id": a.id, "room": self.layout.room_of(a.x, a.y), "state": a.state.value}
                       for a in self.angels],
            "cooldowns": {k: round(v, 1) for k, v in self.events.cooldown.items()},
            "effects": [{"name": n, "left": round(t, 1)} for n, t in self.events.active()],
            "locked": sorted(self.events.locked),
        }
