"""Deterministic contracts for the native Pi multi-call package surface."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PI_SKILL = ROOT / "pi" / "skills" / "humanize-korean" / "SKILL.md"
PI_AGENTS = ROOT / "pi" / "agents"
PROMPTS = ROOT / "prompts"
AGENTS = ("humanize-monolith", "humanize-diagnostician", "humanize-finalizer")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    raw = text.split("\n---\n", 1)[0][4:]
    values: dict[str, str] = {}
    for line in raw.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip().strip('"')
    return values


def test_pi_manifest_declares_native_skill_prompts_and_subagents() -> None:
    manifest = _load(ROOT / "package.json")
    pi = manifest["pi"]

    assert pi["skills"] == ["./pi/skills"]
    assert pi["prompts"] == ["./prompts"]
    assert pi["subagents"]["agents"] == ["./pi/agents"]
    assert "pi-subagents" in manifest["description"]


def test_native_pi_skill_is_a_route_orchestrator() -> None:
    text = PI_SKILL.read_text(encoding="utf-8")

    assert "Claude-specific environment" in text
    assert "Agent 도구" not in text
    assert "subagent" in text
    assert all(route in text for route in ("light", "standard", "heavy"))
    assert "light: 1" in text
    assert "standard: 2" in text
    assert "heavy: 3" in text
    assert "concurrency" in text and "4" in text
    assert "prepare_monolith_input.py" in text
    assert "verify_gates.py" in text
    assert "Resolve\nall relative paths against that skill directory." in text


def test_pi_runtime_agents_are_package_scoped_and_model_agnostic() -> None:
    for name in AGENTS:
        path = PI_AGENTS / f"{name}.md"
        frontmatter = _frontmatter(path)
        assert frontmatter["name"] == name
        assert frontmatter["package"] == "im-not-ai"
        assert "model" not in frontmatter
        text = path.read_text(encoding="utf-8")
        assert "${CLAUDE_SKILL_DIR}" not in text
        assert "Claude Code" not in text
        assert "Do not call other agents" in text
        assert "output_path" in text or "output paths" in text


def test_pi_prompt_entry_points_are_available() -> None:
    for name in ("humanize", "humanize-redo"):
        path = PROMPTS / f"{name}.md"
        frontmatter = _frontmatter(path)
        assert frontmatter["description"]
        assert "/skill:humanize-korean" in path.read_text(encoding="utf-8")


def test_pi_skill_uses_shared_references_without_copying_them() -> None:
    skill_dir = PI_SKILL.parent
    references = skill_dir / "references"
    assert references.is_symlink()
    assert references.resolve() == (ROOT / "skills" / "humanize-korean" / "references").resolve()
    for name in ("quick-rules.md", "diagnosis-rules.md", "rewriting-playbook.md"):
        assert (references / name).is_file(), name


def test_pi_skill_documents_absolute_path_derivation_from_its_location() -> None:
    text = PI_SKILL.read_text(encoding="utf-8")
    assert "skill directory" in text.lower()
    assert "package root" in text.lower()
    assert "../../../scripts" in text
    assert "<skill directory>/references/" in text
