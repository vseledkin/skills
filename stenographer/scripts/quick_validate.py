#!/usr/bin/env python3
"""
Minimal, dependency-free validator for this skill folder.

Rationale: the system-level skill-creator validator depends on PyYAML, which may
not be available in all environments.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(f"Missing file: {path}")


def parse_frontmatter(skill_md: str) -> dict[str, str]:
    lines = skill_md.splitlines()
    if not lines or lines[0].strip() != "---":
        fail("SKILL.md: missing starting '---' frontmatter line")
    try:
        end = lines.index("---", 1)
    except ValueError:
        fail("SKILL.md: missing closing '---' frontmatter line")

    data: dict[str, str] = {}
    for raw in lines[1:end]:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            fail(f"SKILL.md frontmatter: invalid line (expected key: value): {raw!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            fail(f"SKILL.md frontmatter: empty key in line: {raw!r}")
        data[key] = value.strip('"').strip("'")
    return data


def validate() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    folder_name = skill_dir.name

    if not NAME_RE.match(folder_name):
        fail(f"Folder name is not a valid skill name: {folder_name!r}")
    ok(f"Folder name looks valid: {folder_name}")

    skill_md_path = skill_dir / "SKILL.md"
    skill_md = read_text(skill_md_path)
    fm = parse_frontmatter(skill_md)

    name = fm.get("name")
    description = fm.get("description")
    if not name:
        fail("SKILL.md frontmatter: missing 'name'")
    if name != folder_name:
        fail(f"SKILL.md frontmatter: name={name!r} does not match folder {folder_name!r}")
    ok("SKILL.md frontmatter: name OK")

    if not description or "TODO" in description.upper():
        fail("SKILL.md frontmatter: description is missing or still TODO")
    ok("SKILL.md frontmatter: description OK")

    openai_yaml_path = skill_dir / "agents" / "openai.yaml"
    openai_yaml = read_text(openai_yaml_path)
    if "interface:" not in openai_yaml:
        fail("agents/openai.yaml: missing 'interface:'")
    if "default_prompt:" not in openai_yaml:
        fail("agents/openai.yaml: missing 'default_prompt'")
    if "$" + folder_name not in openai_yaml:
        fail(f"agents/openai.yaml: default_prompt should mention ${folder_name}")
    ok("agents/openai.yaml: basic fields OK")

    for required in [
        skill_dir / "assets" / "paper_template.md",
        skill_dir / "assets" / "paper_template_en.md",
        skill_dir / "assets" / "latex_project_template" / "src" / "main.tex",
        skill_dir / "assets" / "latex_project_template" / "src" / "preamble.tex",
        skill_dir / "assets" / "latex_project_template" / "src" / "latexmkrc",
        skill_dir / "references" / "writing_guidelines.md",
        skill_dir / "references" / "citation_rules.md",
        skill_dir / "references" / "review_checklist.md",
        skill_dir / "scripts" / "init_steno_paper.py",
        skill_dir / "scripts" / "project_add_reference.py",
        skill_dir / "scripts" / "project_doctor.sh",
        skill_dir / "scripts" / "project_status.py",
    ]:
        if not required.exists():
            fail(f"Missing required resource: {required}")
    ok("Bundled resources present")


if __name__ == "__main__":
    validate()
