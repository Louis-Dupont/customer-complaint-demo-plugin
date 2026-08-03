#!/usr/bin/env python3
"""Remove exactly one initialized Customer Complaint Demo project."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


DISPLAY_NAME = "Customer Complaint Demo"
SLUG = "customer-complaint-demo"
PROJECT_MARKER = ".customer-complaint-demo-project.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--yes", action="store_true", help="Confirm deletion")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    marker_path = project_dir / PROJECT_MARKER
    if not project_dir.is_dir() or project_dir.is_symlink():
        raise RuntimeError(f"expected generated project directory: {project_dir}")
    if not marker_path.is_file():
        raise RuntimeError(f"missing project marker; refusing to remove: {marker_path}")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if marker.get("schema_version") != 2:
        raise RuntimeError("unsupported project marker version")
    if marker.get("display_name") != DISPLAY_NAME or marker.get("slug") != SLUG:
        raise RuntimeError("project marker does not belong to Customer Complaint Demo")
    if Path(marker["project_directory"]).expanduser().resolve() != project_dir:
        raise RuntimeError("project marker points to a different directory")
    if not args.yes:
        print(f"Would remove:\n- {project_dir}\nPass --yes to confirm.")
        return 0
    shutil.rmtree(project_dir)
    print(f"Removed project: {project_dir}")
    print("Shared plugins, Codex configuration, tasks, and Gmail data were not touched.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyError, json.JSONDecodeError) as error:
        raise SystemExit(f"Customer Complaint Demo removal failed: {error}")
