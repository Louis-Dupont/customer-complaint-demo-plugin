#!/usr/bin/env python3
"""Delete exactly one initialized Customer Complaint Demo directory."""

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


def validate_target(project_dir: Path) -> None:
    marker_path = project_dir / PROJECT_MARKER
    if not project_dir.is_dir() or project_dir.is_symlink():
        raise RuntimeError(f"expected generated project directory: {project_dir}")
    if project_dir.name != DISPLAY_NAME:
        raise RuntimeError(f"unexpected project directory name: {project_dir.name}")
    if not marker_path.is_file() or marker_path.is_symlink():
        raise RuntimeError(f"missing project marker; refusing to delete: {marker_path}")

    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if marker.get("schema_version") != 2:
        raise RuntimeError("unsupported project marker version")
    if marker.get("display_name") != DISPLAY_NAME or marker.get("slug") != SLUG:
        raise RuntimeError("project marker does not belong to Customer Complaint Demo")
    if Path(marker["project_directory"]).expanduser().resolve() != project_dir:
        raise RuntimeError("project marker points to a different directory")


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    validate_target(project_dir)

    if not args.yes:
        print(f"Would delete generated demo directory:\n- {project_dir}")
        print("No files were removed. Pass --yes to confirm.")
        return 0

    shutil.rmtree(project_dir)
    print(f"Deleted generated demo directory: {project_dir}")
    print("Shared plugins, Codex configuration, tasks, and Gmail data were not touched by this script.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyError, json.JSONDecodeError) as error:
        raise SystemExit(f"Customer Complaint Demo deletion failed: {error}")
