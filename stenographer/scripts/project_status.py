#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path


def fmt_time(ts: float | None) -> str:
    if not ts:
        return "n/a"
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def human_bytes(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}TB"


def find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(10):
        if (cur / "pyproject.toml").exists() and (cur / "References").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def list_variants(root: Path) -> list[str]:
    stems: list[str] = []
    for p in sorted(root.glob("*_latex")):
        if p.is_dir():
            stems.append(p.name[: -len("_latex")])
    return stems


def file_info(path: Path) -> tuple[str, str]:
    if not path.exists():
        return ("missing", "n/a")
    st = path.stat()
    return (fmt_time(st.st_mtime), human_bytes(st.st_size))


def main() -> int:
    parser = argparse.ArgumentParser(description="Show current stenographer project state and suggested next commands.")
    parser.add_argument("path", nargs="?", default=".", help="Project path (default: .)")
    args = parser.parse_args()

    root = find_project_root(Path(args.path))
    print(f"Project root: {root}")
    print(f"Working dir:  {Path.cwd()}")
    print("")

    doctor = root / "doctor.sh"
    if doctor.exists() and os.access(doctor, os.X_OK):
        print("Preflight: ./doctor.sh (run to verify tooling)")
    else:
        print("Preflight: doctor.sh not found (older project)")
    print("")

    stems = list_variants(root)
    if not stems:
        print("[WARN] No *_latex variants found. Expected at least one <stem>_latex/ directory.")
        return 1

    print("Variants:")
    for stem in stems:
        md = root / f"{stem}.md"
        pdf = root / f"{stem}.pdf"
        latex_dir = root / f"{stem}_latex"
        md_mtime, md_size = file_info(md)
        pdf_mtime, pdf_size = file_info(pdf)
        print(f"- {stem}")
        print(f"  - Markdown: {md.name}  (mtime: {md_mtime}, size: {md_size})")
        print(f"  - PDF:      {pdf.name} (mtime: {pdf_mtime}, size: {pdf_size})")
        print(f"  - LaTeX:    {latex_dir.name}/")
    print("")

    refs = root / "References"
    idx = refs / "index.md"
    if refs.exists():
        md_files = sorted([p for p in refs.glob("*.md") if p.name != "index.md"], key=lambda p: p.stat().st_mtime, reverse=True)
        pdf_files = sorted(list(refs.glob("*.pdf")), key=lambda p: p.stat().st_mtime, reverse=True)
        print("References archive:")
        print(f"- Folder: {refs}")
        print(f"- Index:  {idx} ({'present' if idx.exists() else 'missing'})")
        print(f"- Files:  {len(md_files)} markdown, {len(pdf_files)} pdf")
        if md_files:
            print("- Recent:")
            for p in md_files[:5]:
                st = p.stat()
                print(f"  - {p.name} (mtime: {fmt_time(st.st_mtime)})")
        print("")

    extras_hint = "uv sync --extra full"
    if (root / "uv.lock").exists():
        print(f"Python env: uv.lock present; recommended: `{extras_hint}` (if you need full extraction fidelity)")
    else:
        print(f"Python env: uv.lock missing; run `{extras_hint}` if you need optional deps")
    print("")

    print("Suggested next commands:")
    print(f"- Lint Markdown: rumdl check {root}")
    for stem in stems:
        print(f"- Watch PDF:     ./{stem}_latex/scripts/watch.sh {stem}")
    print("")
    print("If you want a preview now: pick a variant and open its files:")
    for stem in stems:
        print(f"- {stem}: {root / f'{stem}.md'}  and  {root / f'{stem}.pdf'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

