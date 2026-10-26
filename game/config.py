"""Load the JSON configuration and room layout."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    cfg = json.loads((data_dir / "config.json").read_text())
    layout = json.loads((data_dir / "layout.json").read_text())
    return cfg, layout
