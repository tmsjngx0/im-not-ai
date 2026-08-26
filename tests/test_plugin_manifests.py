"""The Copilot plugin and Pi package expose the single-call skill and shared references."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODEX_SKILL = (ROOT / "codex" / "skills" / "humanize-korean").resolve()
CLAUDE_SKILL = (ROOT / "skills" / "humanize-korean").resolve()
SHARED_REFS = (
    "quick-rules.md",
    "ai-tell-taxonomy.md",
    "rewriting-playbook.md",
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_single_call_skill(skill: Path) -> None:
    assert skill == CODEX_SKILL
    assert skill != CLAUDE_SKILL
    assert (skill / "SKILL.md").is_file()
    for name in SHARED_REFS:
        assert (skill / "references" / name).is_file(), name


def test_copilot_plugin_exposes_single_call_skill_and_references() -> None:
    manifest = _load(ROOT / "plugin.json")
    skill_root = (ROOT / manifest["skills"][0]).resolve()
    skill = skill_root / "humanize-korean"

    assert manifest["name"] == "humanize-korean"
    _assert_single_call_skill(skill)


def test_pi_package_exposes_single_call_skill_and_references() -> None:
    manifest = _load(ROOT / "package.json")
    pi = manifest["pi"]
    skill_root = (ROOT / pi["skills"][0]).resolve()
    skill = skill_root / "humanize-korean"

    assert manifest["name"] == "im-not-ai"
    assert "pi-package" in manifest["keywords"]
    assert pi["skills"] == ["./codex/skills"]
    assert "extensions" not in pi
    assert "prompts" not in pi
    assert "model" not in manifest
    assert "model" not in pi
    _assert_single_call_skill(skill)


def test_pi_and_copilot_share_the_same_skill_root() -> None:
    pi = _load(ROOT / "package.json")
    copilot = _load(ROOT / "plugin.json")
    pi_root = (ROOT / pi["pi"]["skills"][0]).resolve()
    copilot_root = (ROOT / copilot["skills"][0]).resolve()
    assert pi_root == copilot_root == (ROOT / "codex" / "skills").resolve()


def test_pi_skill_is_agent_skills_compatible() -> None:
    text = (CODEX_SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "${CLAUDE_SKILL_DIR}" not in text
    assert "$ARGUMENTS" not in text


def test_pi_manifest_does_not_advertise_claude_orchestrator() -> None:
    """A missing pi key would auto-discover Claude's skills/ tree. The explicit
    manifest must keep that orchestrator out of the Pi package surface."""
    manifest = _load(ROOT / "package.json")
    claude_text = (CLAUDE_SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "${CLAUDE_SKILL_DIR}" in claude_text
    assert "pi" in manifest
    assert "./skills" not in manifest["pi"]["skills"]
    assert "./skills/humanize-korean" not in manifest["pi"]["skills"]
