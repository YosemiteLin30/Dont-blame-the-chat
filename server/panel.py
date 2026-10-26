"""FastAPI control panel: live state over WebSocket, plus buttons to trigger events."""
import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from game.db import SessionDB
from game.events import COMMANDS

PANEL_HTML = (Path(__file__).parent / "panel.html").read_text(encoding="utf-8")
PUSH_INTERVAL = 0.25


def create_app(bridge, db_path=None):
    app = FastAPI(title="Don't Blame the Chat - control panel")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return PANEL_HTML

    @app.get("/api/state")
    def state():
        return bridge.state()

    @app.post("/api/command/{name}")
    def command(name: str):
        if name not in COMMANDS:
            return {"ok": False, "message": "Unknown command"}
        return {"ok": bridge.submit("panel", "streamer", name)}

    @app.post("/api/restart")
    def restart():
        bridge.restart()
        return {"ok": True}

    @app.get("/api/history")
    def history():
        return SessionDB.read_recent(db_path, 10) if db_path else []

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()

        async def sender():
            while True:
                await socket.send_text(json.dumps(bridge.state()))
                await asyncio.sleep(PUSH_INTERVAL)

        task = asyncio.create_task(sender())
        try:
            while True:
                msg = json.loads(await socket.receive_text())
                cmd = msg.get("cmd") if isinstance(msg, dict) else None
                if cmd == "restart":
                    bridge.restart()
                elif cmd in COMMANDS:
                    bridge.submit("panel", "streamer", cmd)
        except (WebSocketDisconnect, ValueError):
            pass
        finally:
            task.cancel()

    return app
