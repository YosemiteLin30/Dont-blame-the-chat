"""Pygame renderer: dark maze, flashlight cone, statues, digits and the HUD."""
import math

import pygame

from .angel import AngelState
from .events import COMMANDS
from .geometry import ray_distance
from .world import Phase

TILE = 32
FLOOR_A, FLOOR_B = (54, 47, 68), (62, 54, 78)
WALL, WALL_LINE = (122, 98, 102), (82, 64, 70)
ACCENT, TEXT, DIM = (167, 139, 250), (225, 222, 255), (140, 134, 180)
ORANGE, RED, GREEN = (232, 150, 70), (230, 80, 90), (110, 231, 168)
COMMAND_HELP = {"lock": "Lock a room for 2s", "shuffle": "Shuffle the rooms", "blackout": "Light out for 3s",
                "chaos": "Shuffle + blackout", "speed": "Angels 30% faster"}


class Renderer:
    def __init__(self, game, screen):
        self.game, self.screen = game, screen
        self.L = game.layout
        self.font = pygame.font.Font(None, 22)
        self.small = pygame.font.Font(None, 18)
        self.big = pygame.font.Font(None, 56)
        self.dark = pygame.Surface((self.L.width, self.L.height), pygame.SRCALPHA)
        self.floor = self._build_floor()

    def _build_floor(self):
        surf = pygame.Surface((self.L.width, self.L.height))
        for ty in range(0, self.L.height, TILE):
            for tx in range(0, self.L.width, TILE):
                surf.fill(FLOOR_A if (tx // TILE + ty // TILE) % 2 == 0 else FLOOR_B, (tx, ty, TILE, TILE))
        return surf

    # -- frame ------------------------------------------------------------------
    def draw(self):
        g = self.game
        self.screen.fill((8, 7, 14))
        self.screen.blit(self.floor, (0, 0))
        self._draw_rooms()
        self._draw_walls()
        self._draw_exit()
        for d in g.digits:
            if not d.taken:
                self._text(self.big, str(d.value), (d.x, d.y), ORANGE, center=True)
        for a in g.angels:
            self._draw_angel(a)
        self._draw_player()
        self._draw_darkness()
        self._draw_hud()
        self._draw_overlays()

    def _text(self, font, text, pos, color=TEXT, center=False):
        img = font.render(text, True, color)
        rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
        self.screen.blit(img, rect)

    # -- world ----------------------------------------------------------------------
    def _draw_rooms(self):
        for room in self.L.rooms:
            ox, oy = self.L.origin(room)
            self._text(self.small, str(room), (ox + 14, oy + 12), (70, 64, 96), center=True)
        for room in self.game.events.locked:
            ox, oy = self.L.origin(room)
            veil = pygame.Surface((self.L.rw, self.L.rh), pygame.SRCALPHA)
            veil.fill((200, 60, 70, 60))
            self.screen.blit(veil, (ox, oy))

    def _draw_walls(self):
        for rect in self.game.walls():
            r = pygame.Rect(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
            pygame.draw.rect(self.screen, WALL, r)
            pygame.draw.rect(self.screen, WALL_LINE, r, 1)

    def _draw_exit(self):
        ex, ey = self.L.exit_point()
        open_ = self.game.phase in (Phase.FINAL, Phase.WON)
        door = pygame.Rect(ex - 10, ey - 26, 14, 52)
        pygame.draw.rect(self.screen, (20, 20, 20) if open_ else (110, 70, 40), door)
        pygame.draw.rect(self.screen, (200, 160, 90), door, 2)
        if not open_:
            pygame.draw.circle(self.screen, (230, 200, 90), (door.x + 4, door.centery), 3)

    def _draw_angel(self, a):
        x, y = int(a.x), int(a.y)
        shade = (150, 150, 160) if a.state is AngelState.FROZEN else (118, 118, 130)
        pygame.draw.rect(self.screen, shade, (x - 7, y - 4, 14, 18))                 # robe
        pygame.draw.circle(self.screen, (170, 170, 180), (x, y - 9), 6)             # head
        pygame.draw.rect(self.screen, shade, (x - 11, y - 12, 5, 12))               # arms over the face
        pygame.draw.rect(self.screen, shade, (x + 6, y - 12, 5, 12))
        pygame.draw.rect(self.screen, (40, 40, 48), (x - 5, y - 11, 10, 3))

    def _draw_player(self):
        p = self.game.player
        x, y = int(p.x), int(p.y)
        pygame.draw.circle(self.screen, (210, 80, 80), (x, y), 8)
        pygame.draw.circle(self.screen, (235, 200, 160), (x, y - 3), 5)
        tip = (x + math.cos(p.facing) * 14, y + math.sin(p.facing) * 14)
        pygame.draw.line(self.screen, (255, 235, 150), (x, y), tip, 3)

    # -- light ----------------------------------------------------------------------------
    def light_polygon(self, scale=1.0, rays=36):
        g, p = self.game, self.game.player
        rng = g.cfg["flashlight"]["range"] * scale
        half = g.beam_angle() / 2
        walls = g.walls()
        pts = [(p.x, p.y)]
        for i in range(rays + 1):
            ang = p.facing - half + (2 * half) * i / rays
            d = min(ray_distance((p.x, p.y), ang, g.cfg["flashlight"]["range"], walls) + 6, rng)   # +6 lights the wall face
            pts.append((p.x + math.cos(ang) * d, p.y + math.sin(ang) * d))
        return pts

    def _draw_darkness(self):
        g, p = self.game, self.game.player
        self.dark.fill((0, 0, 0, 250))
        if g.light_possible():
            for scale, alpha in ((1.0, 175), (0.8, 110), (0.6, 50), (0.4, 0)):
                pygame.draw.polygon(self.dark, (0, 0, 0, alpha), self.light_polygon(scale))
        amb = g.cfg["flashlight"]["ambient"]
        for r, alpha in ((amb, 150), (amb * 0.7, 90), (amb * 0.4, 30)):
            pygame.draw.circle(self.dark, (0, 0, 0, int(alpha)), (int(p.x), int(p.y)), int(r))
        self.screen.blit(self.dark, (0, 0))
        self._draw_player()                       # keep the player visible inside the dark

    # -- HUD ---------------------------------------------------------------------------------
    def _panel(self, rect, title):
        pygame.draw.rect(self.screen, (16, 14, 28), rect)
        pygame.draw.rect(self.screen, (60, 52, 110), rect, 2)
        self._text(self.small, title, (rect[0] + 10, rect[1] + 8), ACCENT)

    def _draw_hud(self):
        g, L = self.game, self.L
        y0, h = L.height, L.hud_h
        pygame.draw.rect(self.screen, (8, 7, 14), (0, y0, L.width, h))
        # digits and mini map
        self._panel((8, y0 + 6, 292, h - 12), "DIGITS / ROOM")
        for i in range(g.cfg["digits"]["count"]):
            box = pygame.Rect(20 + i * 52, y0 + 34, 44, 52)
            pygame.draw.rect(self.screen, (28, 24, 48), box)
            pygame.draw.rect(self.screen, (90, 80, 150), box, 2)
            text = str(g.collected[i][0]) if i < len(g.collected) else "_"
            self._text(self.big, text, box.center, ORANGE, center=True)
        here = g.player_room()
        for room in L.rooms:
            col, row = (room - 1) % 3, (room - 1) // 3
            cell = pygame.Rect(196 + col * 30, y0 + 26 + row * 25, 28, 23)
            pygame.draw.rect(self.screen, (70, 56, 160) if room == here else (26, 22, 44), cell)
            pygame.draw.rect(self.screen, (90, 80, 150), cell, 1)
            self._text(self.small, str(room), cell.center, TEXT if room == here else DIM, center=True)
        # chat commands
        self._panel((308, y0 + 6, 350, h - 12), "CHAT CAN")
        for i, name in enumerate(COMMANDS):
            cd = g.events.cooldown[name]
            line_y = y0 + 26 + i * 16
            self._text(self.small, f"!{name}", (320, line_y), TEXT)
            self._text(self.small, COMMAND_HELP[name], (400, line_y), DIM)
            self._text(self.small, "ready" if cd <= 0 else f"{cd:.0f}s", (610, line_y), GREEN if cd <= 0 else RED)
        # effects and message
        self._panel((666, y0 + 6, 286, h - 12), "ACTIVE EFFECTS")
        effects = g.events.active() or [("none", 0)]
        for i, (name, left) in enumerate(effects[:3]):
            label = name if left <= 0 else f"{name}  0:{int(math.ceil(left)):02d}"
            self._text(self.font, label, (678, y0 + 28 + i * 20), RED if left > 0 else DIM)
        if g.message_left > 0:
            self._text(self.small, g.message[:44], (678, y0 + 90), TEXT)

    # -- overlays -------------------------------------------------------------------------------
    def _draw_overlays(self):
        g, L = self.game, self.L
        cx, cy = L.width // 2, L.height // 2
        if g.code_entry:
            box = pygame.Rect(cx - 150, cy - 70, 300, 140)
            pygame.draw.rect(self.screen, (12, 10, 24), box)
            pygame.draw.rect(self.screen, ACCENT, box, 3)
            self._text(self.font, "ENTER THE CODE (Esc to cancel)", (cx, cy - 46), TEXT, center=True)
            shown = g.code_buffer.ljust(g.cfg["digits"]["count"], "_")
            self._text(self.big, " ".join(shown), (cx, cy + 6), ORANGE, center=True)
            self._text(self.small, "Digits sorted by the room number where you found them",
                       (cx, cy + 50), DIM, center=True)
        if g.phase is Phase.FINAL:
            self._text(self.font, "FINAL BLACKOUT - RUN TO THE EXIT", (cx, 18), RED, center=True)
        if g.phase in (Phase.WON, Phase.LOST):
            veil = pygame.Surface((L.width, L.height), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 170))
            self.screen.blit(veil, (0, 0))
            won = g.phase is Phase.WON
            self._text(self.big, "YOU ESCAPED" if won else "THEY GOT YOU", (cx, cy - 20), GREEN if won else RED, center=True)
            self._text(self.font, f"Time {g.elapsed:.0f}s   Digits {len(g.collected)}/{g.cfg['digits']['count']}"
                       "   Press R for a new game", (cx, cy + 24), TEXT, center=True)
