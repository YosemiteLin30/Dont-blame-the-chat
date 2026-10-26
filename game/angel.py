"""Angel behaviour as a small state machine.

States:
  FROZEN  - lit by the flashlight, cannot move
  HUNT    - in the dark with a route to the player, moves along the shortest room path
  BLOCKED - in the dark but sealed in a locked room or cut off, waits
"""
import math
from enum import Enum

from .pathfinding import shortest_path


class AngelState(Enum):
    HUNT = "hunt"
    FROZEN = "frozen"
    BLOCKED = "blocked"


class Angel:
    def __init__(self, ident, x, y):
        self.id, self.x, self.y = ident, x, y
        self.state = AngelState.HUNT

    # -- state machine ------------------------------------------------------
    def next_state(self, game):
        if game.is_lit(self.x, self.y):
            return AngelState.FROZEN
        return AngelState.HUNT if self.target(game) else AngelState.BLOCKED

    def update(self, game, dt):
        self.state = self.next_state(game)
        if self.state is not AngelState.HUNT:
            return
        tx, ty = self.target(game)
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        step = game.angel_speed() * dt
        if dist <= step or dist == 0:
            self.x, self.y = tx, ty
        else:
            self.x += dx / dist * step
            self.y += dy / dist * step

    # -- navigation -----------------------------------------------------------
    def target(self, game):
        """Next point to walk to, or None when there is no way to the player."""
        L = game.layout
        here, goal = L.room_of(self.x, self.y), game.player_room()
        if here == goal:
            return game.player.x, game.player.y
        locked = game.events.locked
        if here in locked:
            return None
        path = shortest_path(L.neighbors, here, goal, blocked=set(locked))
        if not path:
            return None
        nxt = path[1]
        cx, cy = L.door_center(here, nxt)
        hx, hy = L.center(nxt)[0] - L.center(here)[0], L.center(nxt)[1] - L.center(here)[1]
        norm = math.hypot(hx, hy)
        ux, uy = hx / norm, hy / norm                      # direction from this room into the next
        rx, ry = self.x - cx, self.y - cy
        before = -(rx * ux + ry * uy)                      # distance still to go before the wall
        lateral = rx * -uy + ry * ux                       # sideways offset from the doorway centre
        if abs(lateral) > 6 and before > 6:                # line up with the doorway first
            return cx - ux * 16, cy - uy * 16
        return cx + ux * 16, cy + uy * 16                  # then walk straight through it
