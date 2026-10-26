import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from game.config import load
from game.world import Game


@pytest.fixture
def cfgs():
    return load()


@pytest.fixture
def game(cfgs):
    cfg, layout = cfgs
    return Game(cfg, layout, seed=7)
