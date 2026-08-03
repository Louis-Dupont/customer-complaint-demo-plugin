#!/usr/bin/env python3
"""Remove exactly one initialized Customer Complaint Demo capsule."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


DISPLAY_NAME = "Customer Complaint Demo"
SLUG = "customer-complaint-demo"
CAPSULE_MARKER = ".customer-complaint-demo-capsule.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--yes", action="store_true", help="Confirm deletion")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    marker_path = project_dir / CAPSULE_MARKER
    if not project_dir.is_dir() or project_dir.is_symlink():
        raise RuntimeError(f"expected generated project directory: {project_dir}")
    if not marker_path.is_file():
        raise RuntimeError(f"missing capsule marker; refusing to remove: {marker_path}")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if marker.get("display_name") != DISPLAY_NAME or marker.get("slug") != SLUG:
        raise RuntimeError("capsule marker does not belong to Customer Complaint Demo")
    runtime_dir = Path(marker["runtime_directory"]).expanduser().resolve()
    if not runtime_dir.is_dir() or runtime_dir.is_symlink():
        raise RuntimeError(f"expected generated runtime directory: {runtime_dir}")
    if not args.yes:
        print(f"Would remove:\n- {project_dir}\n- {runtime_dir}\nPass --yes to confirm.")
        return 0
    shutil.rmtree(project_dir)
    shutil.rmtree(runtime_dir)
    print(f"Removed project: {project_dir}")
    print(f"Removed isolated CODEX_HOME: {runtime_dir}")
    print("The shared Codex home, plugin installations, and Gmail data were not touched.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyError, json.JSONDecodeError) as error:
        raise SystemExit(f"Customer Complaint Demo removal failed: {error}")
