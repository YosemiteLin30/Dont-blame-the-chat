"""Background services: control panel (FastAPI + uvicorn), Twitch bot, optional fake chat."""
import asyncio
import os

import uvicorn

from chat.sim import run_sim_chat
from chat.twitch_bot import make_bot
from server.panel import create_app


async def _main(bridge, host, port, db_path, channel, token, sim_chat):
    config = uvicorn.Config(create_app(bridge, db_path), host=host, port=port, log_level="warning")
    tasks = [uvicorn.Server(config).serve()]
    if channel and token:
        tasks.append(make_bot(token, channel, bridge).start())
    elif channel:
        print("Twitch: set TWITCH_TOKEN (oauth:...) to read chat; the panel still works.")
    if sim_chat:
        tasks.append(run_sim_chat(bridge))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            print(f"Service stopped: {r!r}")


def run_services(bridge, host="127.0.0.1", port=8000, db_path=None, channel=None, sim_chat=False):
    token = os.environ.get("TWITCH_TOKEN")
    asyncio.run(_main(bridge, host, port, db_path, channel, token, sim_chat))
