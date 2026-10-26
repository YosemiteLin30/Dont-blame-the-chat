"""The 3x3 maze geometry: rooms are numbered 1..9 (left to right, top to bottom)."""


class Layout:
    def __init__(self, data):
        self.n = data["grid"]
        self.rw, self.rh = data["room_w"], data["room_h"]
        self.wall = data["wall"]
        self.door_w = data["door_w"]
        self.hud_h = data["hud_h"]
        self.start_room = data["start_room"]
        self.exit_room = data["exit_room"]
        self.angel_spawn_rooms = data["angel_spawn_rooms"]
        self.digit_rooms = data["digit_rooms"]
        self.digit_spawns = data["digit_spawns"]
        self.width, self.height = self.n * self.rw, self.n * self.rh
        self.rooms = list(range(1, self.n * self.n + 1))
        self._walls = self._build_walls()

    # -- rooms ------------------------------------------------------------
    def room_of(self, x, y):
        col = min(max(int(x // self.rw), 0), self.n - 1)
        row = min(max(int(y // self.rh), 0), self.n - 1)
        return row * self.n + col + 1

    def origin(self, room):
        i = room - 1
        return (i % self.n) * self.rw, (i // self.n) * self.rh

    def center(self, room):
        ox, oy = self.origin(room)
        return ox + self.rw / 2, oy + self.rh / 2

    def neighbors(self, room):
        i = room - 1
        col, row = i % self.n, i // self.n
        out = []
        if col > 0:
            out.append(room - 1)
        if col < self.n - 1:
            out.append(room + 1)
        if row > 0:
            out.append(room - self.n)
        if row < self.n - 1:
            out.append(room + self.n)
        return out

    def door_center(self, a, b):
        """Midpoint of the doorway between adjacent rooms a and b."""
        (ax, ay), (bx, by) = self.center(a), self.center(b)
        return (ax + bx) / 2, (ay + by) / 2

    def exit_point(self):
        return self.width - 4, self.center(self.exit_room)[1]

    # -- walls --------------------------------------------------------------
    def _build_walls(self):
        t, n, rw, rh, g = self.wall / 2, self.n, self.rw, self.rh, self.door_w / 2
        walls = []
        for c in range(1, n):                       # vertical walls with a doorway per row
            x = c * rw
            for r in range(n):
                cy = r * rh + rh / 2
                walls.append((x - t, r * rh, x + t, cy - g))
                walls.append((x - t, cy + g, x + t, (r + 1) * rh))
        for r in range(1, n):                       # horizontal walls with a doorway per column
            y = r * rh
            for c in range(n):
                cx = c * rw + rw / 2
                walls.append((c * rw, y - t, cx - g, y + t))
                walls.append((cx + g, y - t, (c + 1) * rw, y + t))
        w, h = self.width, self.height              # outer border
        walls += [(-t * 2, -t, w + t * 2, t), (-t * 2, h - t, w + t * 2, h + t),
                  (-t, 0, t, h), (w - t, 0, w + t, h)]
        return walls

    def static_walls(self):
        return list(self._walls)

    def door_rect(self, a, b):
        """Rectangle that seals the doorway between a and b."""
        x, y = self.door_center(a, b)
        g, t = self.door_w / 2, self.wall / 2
        if abs(self.center(a)[0] - self.center(b)[0]) > 1:     # vertical wall
            return (x - t, y - g, x + t, y + g)
        return (x - g, y - t, x + g, y + t)
