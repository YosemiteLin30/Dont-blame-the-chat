"""Don't Blame the Chat, Blame the Game - run the game, control panel and Twitch bot.

  python main.py                       # game + control panel at http://127.0.0.1:8000
  python main.py --channel mychannel   # also read Twitch chat (needs TWITCH_TOKEN=oauth:...)
  python main.py --sim-chat            # fake chat commands for testing without Twitch

Controls: WASD move, mouse aims the flashlight, E interact / pick up, R restart, Esc quit.
"""
import argparse
import math
import threading
import time
from pathlib import Path

import pygame

from game.config import DATA_DIR, load
from game.db import SessionDB
from game.render import Renderer
from game.world import Game, Phase
from server.bridge import GameBridge
from server.services import run_services

FPS = 60
SNAPSHOT_EVERY = 0.2


class Session:
    """Keeps one DB session row per round."""

    def __init__(self, db, game):
        self.db, self.game = db, game
        self.id = db.start_session()
        self.closed = False

    def close_if_over(self):
        if not self.closed and not self.game.running():
            self.db.end_session(self.id, self.game.phase.value, len(self.game.collected), self.game.elapsed)
            self.closed = True


def apply_commands(game, bridge, db, session):
    for source, user, name, arg in bridge.drain_commands():
        ok, msg = game.events.trigger(name, arg)
        db.log_event(session.id, source, user, name, ok, msg)
        bridge.add_log(f"{user}: !{name} -> {msg}", ok)
        if ok:
            game.say(f"{user}: {msg}", 2.5)


def handle_key(game, event):
    if game.code_entry:
        if event.key == pygame.K_ESCAPE:
            game.cancel_entry()
        elif event.key == pygame.K_BACKSPACE:
            game.backspace()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            game.submit_code()
        elif event.unicode and event.unicode.isdigit():
            game.type_digit(event.unicode)
    elif event.key == pygame.K_e:
        game.interact()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--channel", help="Twitch channel to read (needs TWITCH_TOKEN env var)")
    ap.add_argument("--sim-chat", action="store_true", help="simulate random chat commands")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000, help="control panel port")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--db", default=str(DATA_DIR / "sessions.db"))
    args = ap.parse_args(argv)

    cfg, layout_data = load()
    game = Game(cfg, layout_data, seed=args.seed)
    bridge = GameBridge(cfg["chat"]["per_user_cooldown"])
    db = SessionDB(args.db)
    session = Session(db, game)
    threading.Thread(target=run_services, daemon=True, kwargs=dict(
        bridge=bridge, host=args.host, port=args.port, db_path=args.db,
        channel=args.channel, sim_chat=args.sim_chat)).start()

    pygame.init()
    L = game.layout
    screen = pygame.display.set_mode((L.width, L.height + L.hud_h))
    pygame.display.set_caption("Don't Blame the Chat, Blame the Game")
    renderer = Renderer(game, screen)
    clock, last_snap, running = pygame.time.Clock(), 0.0, True
    print(f"Control panel: http://{args.host}:{args.port}/")

    while running:
        dt = min(clock.tick(FPS) / 1000, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and not game.code_entry:
                    running = False
                elif event.key == pygame.K_r and not game.running():
                    bridge.restart()
                else:
                    handle_key(game, event)
        if "restart" in bridge.drain_controls():
            game.reset()
            session = Session(db, game)
            bridge.add_log("New game started")
        apply_commands(game, bridge, db, session)

        keys = pygame.key.get_pressed()
        move = (keys[pygame.K_d] - keys[pygame.K_a], keys[pygame.K_s] - keys[pygame.K_w])
        mx, my = pygame.mouse.get_pos()
        aim = math.atan2(my - game.player.y, mx - game.player.x)
        game.update(dt, move, aim)
        session.close_if_over()

        renderer.draw()
        pygame.display.flip()
        if time.monotonic() - last_snap > SNAPSHOT_EVERY:
            bridge.set_snapshot(game.snapshot())
            last_snap = time.monotonic()
    session.close_if_over()
    db.close()
    pygame.quit()


if __name__ == "__main__":
    main()
