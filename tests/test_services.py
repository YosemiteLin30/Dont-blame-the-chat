import time

import pygame
import pytest
from fastapi.testclient import TestClient

from chat.commands import parse_chat
from chat.twitch_bot import handle_message, make_bot
from game.db import SessionDB
from game.render import Renderer
from game.world import Phase
from server.bridge import GameBridge
from server.panel import create_app


def test_parse_chat():
    assert parse_chat("!lock") == ("lock", None) and parse_chat("!LOCK 4") == ("lock", 4)
    assert parse_chat("!shuffle now") == ("shuffle", None) and parse_chat("  !chaos") == ("chaos", None)
    for bad in ("hello", "!dance", "", "lock", "!"):
        assert parse_chat(bad) is None


def test_bridge_per_user_cooldown_and_panel_bypass():
    b = GameBridge(per_user_cooldown=60)
    assert handle_message(b, "ann", "!lock") and not handle_message(b, "ann", "!shuffle")
    assert handle_message(b, "bob", "!shuffle") and not handle_message(b, "bob", "hi")
    assert b.submit("panel", "streamer", "speed") and b.submit("panel", "streamer", "speed")
    names = [c[2] for c in b.drain_commands()]
    assert names == ["lock", "shuffle", "speed", "speed"] and b.drain_commands() == []


def test_twitch_bot_can_be_built_without_connecting():
    bot = make_bot("oauth:dummy", "somechannel", GameBridge())
    assert bot is not None


def test_database_sessions_and_events(tmp_path):
    db = SessionDB(tmp_path / "t.db")
    sid = db.start_session()
    db.log_event(sid, "twitch", "ann", "lock", True, "ok")
    db.log_event(sid, "panel", "streamer", "speed", False, "cooldown")
    db.end_session(sid, "won", 3, 91.5)
    rows = SessionDB.read_recent(tmp_path / "t.db")
    assert rows == [{"id": sid, "result": "won", "digits_found": 3, "seconds": 91.5, "events": 2}]
    db.close()


def test_panel_api_and_websocket(tmp_path):
    bridge = GameBridge()
    bridge.set_snapshot({"phase": "playing", "elapsed": 1.0})
    bridge.add_log("hello")
    with TestClient(create_app(bridge, tmp_path / "p.db")) as client:
        assert "Control Panel" in client.get("/").text
        assert client.get("/api/state").json()["phase"] == "playing"
        assert client.post("/api/command/lock").json() == {"ok": True}
        assert client.post("/api/command/dance").json()["ok"] is False
        assert client.post("/api/restart").json() == {"ok": True}
        assert client.get("/api/history").json() == []
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["phase"] == "playing"
            ws.send_json({"cmd": "shuffle"})
            ws.send_json({"cmd": "bogus"})
            ws.send_text("not json")
    cmds = bridge.drain_commands()
    assert [c[2] for c in cmds] == ["lock", "shuffle"] and bridge.drain_controls() == ["restart"]


def test_renderer_draws_every_phase(game, tmp_path):
    pygame.init()
    L = game.layout
    screen = pygame.display.set_mode((L.width, L.height + L.hud_h))
    r = Renderer(game, screen)
    game.events.trigger("lock")
    game.collected = [(4, 2, 0)]
    for phase in (Phase.PLAYING, Phase.FINAL, Phase.WON, Phase.LOST):
        game.phase = phase
        game.code_entry = phase is Phase.PLAYING
        game.code_buffer = "5"
        r.draw()
    assert screen.get_at((20, 20)) is not None
    pygame.image.save(screen, tmp_path / "frame.png")
