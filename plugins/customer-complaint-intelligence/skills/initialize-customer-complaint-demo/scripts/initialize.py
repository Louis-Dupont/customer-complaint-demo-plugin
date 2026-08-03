#!/usr/bin/env python3
"""Create an isolated Customer Complaint Demo Codex capsule."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import uuid
from pathlib import Path


DISPLAY_NAME = "Customer Complaint Demo"
SLUG = "customer-complaint-demo"
PLUGIN_REPOSITORY = "https://github.com/Louis-Dupont/customer-complaint-demo-plugin.git"
PLUGIN_MARKETPLACE = "jad-customer-complaint-intelligence"
PLUGIN_SELECTOR = "customer-complaint-intelligence@jad-customer-complaint-intelligence"
DEFAULT_PLUGIN_REF = "main"
REQUIRED_MARKETPLACES = {
    "openai-bundled": "visualize@openai-bundled",
}
CURATED_SNAPSHOT_NAME = "jad-openai-curated-gmail"
CURATED_SOURCE_NAME = "openai-curated"
TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "demo-project"
CAPSULE_MARKER = ".customer-complaint-demo-capsule.json"


def run_codex(args: list[str], codex_home: Path, *, capture: bool = False) -> str:
    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(codex_home)
    completed = subprocess.run(
        ["codex", *args],
        env=environment,
        check=True,
        text=True,
        capture_output=capture,
    )
    return completed.stdout if capture else ""


def discover_marketplaces(bootstrap_home: Path) -> dict[str, str]:
    payload = json.loads(run_codex(["plugin", "marketplace", "list", "--json"], bootstrap_home, capture=True))
    discovered: dict[str, str] = {}
    required_sources = set(REQUIRED_MARKETPLACES) | {CURATED_SOURCE_NAME}
    for item in payload.get("marketplaces", []):
        name = item.get("name")
        source_info = item.get("marketplaceSource") or {}
        source = source_info.get("source") or item.get("root")
        if name in required_sources and isinstance(source, str) and source:
            discovered[name] = source
    missing = sorted(required_sources - set(discovered))
    if missing:
        raise RuntimeError(
            "The invoking Codex home does not expose the official marketplace source(s): "
            + ", ".join(missing)
        )
    return discovered


def prepare_curated_gmail_snapshot(source_root: Path, runtime_dir: Path) -> Path:
    source_manifest_path = source_root / ".agents" / "plugins" / "marketplace.json"
    source_plugin = source_root / "plugins" / "gmail"
    if not source_manifest_path.is_file() or not source_plugin.is_dir():
        raise RuntimeError(f"cannot prepare Gmail snapshot from {source_root}")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    plugin_entry = next(
        (entry for entry in source_manifest.get("plugins", []) if entry.get("name") == "gmail"),
        None,
    )
    if plugin_entry is None:
        raise RuntimeError(f"Gmail is not present in the curated marketplace at {source_root}")

    snapshot = runtime_dir / "official-marketplaces" / "gmail"
    shutil.copytree(source_plugin, snapshot / "plugins" / "gmail")
    snapshot_manifest = {
        "name": CURATED_SNAPSHOT_NAME,
        "interface": source_manifest.get("interface", {"displayName": "JAD Gmail dependency"}),
        "plugins": [plugin_entry],
    }
    write_text(
        snapshot / ".agents" / "plugins" / "marketplace.json",
        json.dumps(snapshot_manifest, indent=2, ensure_ascii=False) + "\n",
    )
    return snapshot


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_launcher(project_dir: Path, runtime_dir: Path) -> None:
    launcher = f'''#!/bin/sh
set -eu
PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
CAPSULE_HOME="{runtime_dir}"
export CODEX_HOME="$CAPSULE_HOME"

if [ "${{1:-}}" = "--cli" ]; then
  shift
  exec codex -C "$PROJECT_DIR" "$@"
fi

if [ "$#" -ne 0 ]; then
  echo "Usage: $0 [--cli [codex arguments...]]" >&2
  exit 2
fi
exec codex app "$PROJECT_DIR"
'''
    launcher_path = project_dir / "codex-project"
    write_text(launcher_path, launcher)
    launcher_path.chmod(launcher_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(Path.home() / "Projects"))
    parser.add_argument("--runtime-root", default=str(Path.home() / ".codex-products"))
    parser.add_argument(
        "--bootstrap-home",
        default=os.environ.get("CODEX_HOME") or str(Path.home() / ".codex"),
        help="Codex home that invoked this skill; used to discover official marketplace sources",
    )
    parser.add_argument("--marketplace-ref", default=DEFAULT_PLUGIN_REF)
    parser.add_argument("--no-open", action="store_true", help="Create the capsule without opening the Desktop app")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    runtime_root = Path(args.runtime_root).expanduser().resolve()
    bootstrap_home = Path(args.bootstrap_home).expanduser().resolve()
    project_dir = project_root / DISPLAY_NAME
    runtime_dir = runtime_root / SLUG

    if not TEMPLATE.is_dir():
        raise RuntimeError(f"missing bundled demo template: {TEMPLATE}")
    if project_dir.exists():
        raise RuntimeError(f"refusing to overwrite existing project: {project_dir}")
    if runtime_dir.exists():
        raise RuntimeError(f"refusing to overwrite existing Codex home: {runtime_dir}")

    official_sources = discover_marketplaces(bootstrap_home)
    project_root.mkdir(parents=True, exist_ok=True)
    runtime_root.mkdir(parents=True, exist_ok=True)
    staging_id = uuid.uuid4().hex
    staged_project = project_root / f".{SLUG}.project-{staging_id}"
    staged_runtime = runtime_root / f".{SLUG}.runtime-{staging_id}"

    try:
        shutil.copytree(TEMPLATE, staged_project)
        staged_runtime.mkdir(parents=True)
        write_text(
            staged_runtime / "config.toml",
            "# Isolated Codex state for Customer Complaint Demo.\n"
            'mcp_oauth_credentials_store = "file"\n',
        )
        write_launcher(staged_project, runtime_dir)
        write_text(
            staged_project / CAPSULE_MARKER,
            json.dumps(
                {
                    "schema_version": 1,
                    "display_name": DISPLAY_NAME,
                    "slug": SLUG,
                    "project_directory": str(project_dir),
                    "runtime_directory": str(runtime_dir),
                    "plugin_repository": PLUGIN_REPOSITORY,
                    "plugin_ref": args.marketplace_ref,
                    "plugin_selector": PLUGIN_SELECTOR,
                    "email_fixture_policy": "local scaffolding only; not sent by initializer",
                },
                indent=2,
            )
            + "\n",
        )

        for marketplace_name, source in official_sources.items():
            if marketplace_name == CURATED_SOURCE_NAME:
                snapshot = prepare_curated_gmail_snapshot(Path(source), staged_runtime)
                run_codex(["plugin", "marketplace", "add", str(snapshot)], staged_runtime)
            else:
                run_codex(["plugin", "marketplace", "add", source], staged_runtime)
        run_codex(
            ["plugin", "marketplace", "add", PLUGIN_REPOSITORY, "--ref", args.marketplace_ref],
            staged_runtime,
        )
        for plugin_selector in REQUIRED_MARKETPLACES.values():
            run_codex(["plugin", "add", plugin_selector], staged_runtime)
        run_codex(["plugin", "add", f"gmail@{CURATED_SNAPSHOT_NAME}"], staged_runtime)
        run_codex(["plugin", "add", PLUGIN_SELECTOR], staged_runtime)

        staged_project.rename(project_dir)
        staged_runtime.rename(runtime_dir)
    except Exception:
        if staged_project.exists():
            shutil.rmtree(staged_project)
        if staged_runtime.exists():
            shutil.rmtree(staged_runtime)
        raise

    launcher_path = project_dir / "codex-project"
    print(f"Created project: {project_dir}")
    print(f"Created isolated CODEX_HOME: {runtime_dir}")
    print(f"Launch with: {launcher_path}")
    print("Connect Codex and Gmail inside the new capsule before running the demo.")
    if not args.no_open:
        run_codex(["app", str(project_dir)], runtime_dir)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"Customer Complaint Demo setup failed: {error}", file=sys.stderr)
        raise SystemExit(1)
