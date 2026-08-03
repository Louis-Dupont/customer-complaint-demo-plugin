#!/usr/bin/env python3
"""Reset local demo outputs without touching the reusable plugin."""

from __future__ import annotations

import shutil
from pathlib import Path

from generate_demo_data import main as generate_fixtures


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "workspace"


def main() -> None:
    generate_fixtures()
    WORKSPACE.mkdir(exist_ok=True)
    for child in WORKSPACE.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    print(f"reset local workspace: {WORKSPACE}")


if __name__ == "__main__":
    main()
