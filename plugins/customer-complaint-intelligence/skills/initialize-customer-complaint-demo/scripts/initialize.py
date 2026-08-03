#!/usr/bin/env python3
"""Create the local Customer Complaint Demo project from its bundled template."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


DISPLAY_NAME = "Customer Complaint Demo"
SLUG = "customer-complaint-demo"
PLUGIN_REPOSITORY = "https://github.com/Louis-Dupont/customer-complaint-demo-plugin.git"
PLUGIN_SELECTOR = "customer-complaint-intelligence@jad-customer-complaint-intelligence"
TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "demo-project"
PROJECT_MARKER = ".customer-complaint-demo-project.json"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(Path.home() / "Projects"))
    parser.add_argument("--no-open", action="store_true", help="Create the project without opening Codex Desktop")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    project_dir = project_root / DISPLAY_NAME

    if not TEMPLATE.is_dir():
        raise RuntimeError(f"missing bundled demo template: {TEMPLATE}")
    if project_dir.exists():
        raise RuntimeError(f"refusing to overwrite existing project: {project_dir}")

    project_root.mkdir(parents=True, exist_ok=True)
    staged_project = project_root / f".{SLUG}.project-{uuid.uuid4().hex}"

    try:
        shutil.copytree(TEMPLATE, staged_project)
        write_text(
            staged_project / PROJECT_MARKER,
            json.dumps(
                {
                    "schema_version": 2,
                    "display_name": DISPLAY_NAME,
                    "slug": SLUG,
                    "project_directory": str(project_dir),
                    "plugin_repository": PLUGIN_REPOSITORY,
                    "plugin_selector": PLUGIN_SELECTOR,
                    "codex_environment": "shared invoking Codex environment",
                    "connector_policy": "use existing connections; connect natively on first use when absent",
                    "email_fixture_policy": "local scaffolding only; not sent by initializer",
                },
                indent=2,
            )
            + "\n",
        )
        staged_project.rename(project_dir)
    except Exception:
        if staged_project.exists():
            shutil.rmtree(staged_project)
        raise

    print(f"Created project: {project_dir}")
    print("Codex plugins and connector authentication remain in the invoking user's shared environment.")
    if not args.no_open:
        subprocess.run(["codex", "app", str(project_dir)], check=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Customer Complaint Demo setup failed: {error}", file=sys.stderr)
        raise SystemExit(1)
