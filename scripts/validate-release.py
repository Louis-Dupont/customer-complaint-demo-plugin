#!/usr/bin/env python3
"""Validate the repository's Codex plugin and skill boundaries."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "customer-complaint-intelligence"
MANIFEST = PLUGIN / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
EXPECTED_SKILLS = {
    "extract-gmail-complaints",
    "analyze-complaint-patterns",
    "investigate-complaint-evidence",
    "apply-complaint-labels",
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain an object")
    return value


def main() -> None:
    manifest = load_json(MANIFEST)
    marketplace = load_json(MARKETPLACE)
    assert manifest["name"] == PLUGIN.name
    assert manifest["skills"] == "./skills/"
    assert "mcpServers" not in manifest
    assert "apps" not in manifest
    assert marketplace["plugins"][0]["name"] == PLUGIN.name
    assert marketplace["plugins"][0]["source"]["path"] == "./plugins/customer-complaint-intelligence"

    actual_skills = {
        path.name
        for path in (PLUGIN / "skills").iterdir()
        if path.is_dir() and not path.name.startswith(".")
    }
    assert actual_skills == EXPECTED_SKILLS, (actual_skills, EXPECTED_SKILLS)
    for skill_name in EXPECTED_SKILLS:
        skill_file = PLUGIN / "skills" / skill_name / "SKILL.md"
        assert skill_file.is_file(), skill_file
        content = skill_file.read_text(encoding="utf-8")
        assert content.startswith("---\nname:"), skill_file
        assert "TODO" not in content, skill_file
        metadata = PLUGIN / "skills" / skill_name / "agents" / "openai.yaml"
        assert metadata.is_file(), metadata
        assert metadata.read_text(encoding="utf-8").startswith("interface:"), metadata

    assert (PLUGIN / "skills" / "extract-gmail-complaints" / "scripts" / "validate-register.py").is_file()
    assert (PLUGIN / "skills" / "analyze-complaint-patterns" / "scripts" / "prepare-analysis.py").is_file()
    assert not list(PLUGIN.rglob("*.eml"))
    assert not list(PLUGIN.rglob("*.csv"))

    print(f"validated {PLUGIN.name}: {len(actual_skills)} skills")


if __name__ == "__main__":
    main()
