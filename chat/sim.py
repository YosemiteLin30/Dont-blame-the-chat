"""Fake chat for demos without Twitch: random viewers send random commands."""
import asyncio
import random

from game.events import COMMANDS

VIEWERS = ["ghost", "zed", "nina", "kiwi", "bolt", "mara", "oni", "pax"]


async def run_sim_chat(bridge, rng=None):
    rng = rng or random.Random()
    while True:
        await asyncio.sleep(rng.uniform(2.0, 6.0))
        name = rng.choice(COMMANDS)
        user = rng.choice(VIEWERS)
        text = f"!{name}" + (f" {rng.randint(1, 9)}" if name == "lock" and rng.random() < 0.5 else "")
        bridge.submit_text("sim", user, text)
