#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a stenographer paper project: <name>.md + <name>_latex/ with LaTeX src/."
    )
    parser.add_argument("name", help="Base name (without extension), e.g. 'paper' or 'my-article'")
    parser.add_argument(
        "--dir",
        default=".",
        help="Target directory where <name>.md and <name>_latex/ will be created (default: current dir)",
    )
    args = parser.parse_args()

    base = Path(args.dir).resolve()
    base.mkdir(parents=True, exist_ok=True)

    md_path = base / f"{args.name}.md"
    latex_dir = base / f"{args.name}_latex"

    skill_dir = Path(__file__).resolve().parents[1]
    md_template = skill_dir / "assets" / "paper_template.md"
    latex_template = skill_dir / "assets" / "latex_project_template"

    if not md_path.exists():
        shutil.copyfile(md_template, md_path)
        print(f"[OK] Created {md_path}")
    else:
        print(f"[SKIP] Exists {md_path}")

    if not latex_dir.exists():
        shutil.copytree(latex_template, latex_dir)
        print(f"[OK] Created {latex_dir}")
    else:
        print(f"[SKIP] Exists {latex_dir}")

    # Ensure expected build folder exists
    (latex_dir / "build").mkdir(parents=True, exist_ok=True)

    # Write a small Makefile for convenience
    makefile = base / "Makefile"
    if not makefile.exists():
        makefile.write_text(
            f"""\
.PHONY: pdf watch clean

NAME := {args.name}
LATEX_DIR := $(NAME)_latex

pdf:
\t./$(LATEX_DIR)/scripts/build.sh $(NAME)

watch:
\t./$(LATEX_DIR)/scripts/watch.sh $(NAME)

clean:
\t./$(LATEX_DIR)/scripts/clean.sh $(NAME)
""",
            encoding="utf-8",
        )
        print(f"[OK] Created {makefile}")
    else:
        print(f"[SKIP] Exists {makefile}")

    # Create root References folder and index
    references_dir = base / "References"
    references_dir.mkdir(parents=True, exist_ok=True)
    index_md = references_dir / "index.md"
    if not index_md.exists():
        index_md.write_text(
            "# References (local archive)\n\n"
            "This folder stores a local, human-readable copy of every cited source.\n"
            "- For web pages: a best-effort Markdown capture (`.md`).\n"
            "- For PDFs: both the original PDF (`.pdf`) and an extracted Markdown (`.md`).\n\n"
            "## Index\n\n",
            encoding="utf-8",
        )
        print(f"[OK] Created {index_md}")
    else:
        print(f"[SKIP] Exists {index_md}")

    # Drop helper scripts into the LaTeX folder (so they travel with the project)
    scripts_dir = latex_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    for name, content in {
        "build.sh": BUILD_SH,
        "watch.sh": WATCH_SH,
        "clean.sh": CLEAN_SH,
        "sync_md_to_tex.py": SYNC_PY,
    }.items():
        out = scripts_dir / name
        if not out.exists():
            out.write_text(content, encoding="utf-8")
            out.chmod(0o755)
            print(f"[OK] Created {out}")
        else:
            print(f"[SKIP] Exists {out}")

    add_reference_out = scripts_dir / "add_reference.py"
    if not add_reference_out.exists():
        src = skill_dir / "scripts" / "project_add_reference.py"
        add_reference_out.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        add_reference_out.chmod(0o755)
        print(f"[OK] Created {add_reference_out}")
    else:
        print(f"[SKIP] Exists {add_reference_out}")

    return 0


BUILD_SH = """#!/usr/bin/env bash
set -euo pipefail

NAME="${1:?base name required, e.g. paper}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${ROOT_DIR}/src"
BUILD_DIR="${ROOT_DIR}/build"
OUT_PDF="${ROOT_DIR}/../${NAME}.pdf"
MD_PATH="${ROOT_DIR}/../${NAME}.md"

mkdir -p "${BUILD_DIR}"

if [[ -f "${MD_PATH}" ]]; then
  python3 "${ROOT_DIR}/scripts/sync_md_to_tex.py" "${MD_PATH}" "${SRC_DIR}"
fi

set +e
latexmk \\
  -r "${SRC_DIR}/latexmkrc" \\
  -cd \\
  -pdf \\
  -f \\
  -outdir="${BUILD_DIR}" \\
  -jobname="${NAME}" \\
  "${SRC_DIR}/main.tex"
LATEXMK_STATUS=$?
set -e

if [[ -f "${BUILD_DIR}/${NAME}.pdf" ]]; then
  cp -f "${BUILD_DIR}/${NAME}.pdf" "${OUT_PDF}"
  echo "[OK] Wrote ${OUT_PDF}"
else
  echo "[FAIL] PDF not produced: ${BUILD_DIR}/${NAME}.pdf" >&2
  exit 1
fi

if [[ "${LATEXMK_STATUS}" != "0" ]]; then
  echo "[WARN] latexmk exited with ${LATEXMK_STATUS}; PDF was produced anyway" >&2
fi
exit 0
"""


WATCH_SH = """#!/usr/bin/env bash
set -euo pipefail

NAME="${1:?base name required, e.g. paper}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${ROOT_DIR}/src"
BUILD_DIR="${ROOT_DIR}/build"
OUT_PDF="${ROOT_DIR}/../${NAME}.pdf"
MD_PATH="${ROOT_DIR}/../${NAME}.md"

mkdir -p "${BUILD_DIR}"

echo "[INFO] Watching LaTeX sources; PDF will be copied to: ${OUT_PDF}"
echo "[INFO] Stop with Ctrl+C"

# If the paired Markdown exists, keep meta/content/abstract in sync by polling
# mtime (works without extra tools like fswatch/entr).
(
  last_md_mtime=""
  while true; do
    if [[ -f "${MD_PATH}" ]]; then
      mtime="$(stat -f "%m" "${MD_PATH}" 2>/dev/null || true)"
      if [[ -n "${mtime}" && "${mtime}" != "${last_md_mtime}" ]]; then
        python3 "${ROOT_DIR}/scripts/sync_md_to_tex.py" "${MD_PATH}" "${SRC_DIR}" || true
        last_md_mtime="${mtime}"
        echo "[OK] Synced ${MD_PATH} -> ${SRC_DIR}"
      fi
    fi
    sleep 0.5
  done
) &
SYNC_PID=$!

# latexmk -pvc runs continuously. We copy the PDF after each successful build
# using a background loop that checks the mtime.
(
  last_mtime=""
  while true; do
    if [[ -f "${BUILD_DIR}/${NAME}.pdf" ]]; then
      mtime="$(stat -f "%m" "${BUILD_DIR}/${NAME}.pdf" 2>/dev/null || true)"
      if [[ -n "${mtime}" && "${mtime}" != "${last_mtime}" ]]; then
        cp -f "${BUILD_DIR}/${NAME}.pdf" "${OUT_PDF}"
        echo "[OK] Updated ${OUT_PDF}"
        last_mtime="${mtime}"
      fi
    fi
    sleep 0.5
  done
) &
COPIER_PID=$!
trap 'kill "${SYNC_PID}" 2>/dev/null || true; kill "${COPIER_PID}" 2>/dev/null || true' EXIT

latexmk \\
  -r "${SRC_DIR}/latexmkrc" \\
  -cd \\
  -pdf \\
  -f \\
  -pvc \\
  -outdir="${BUILD_DIR}" \\
  -jobname="${NAME}" \\
  "${SRC_DIR}/main.tex"
"""


CLEAN_SH = """#!/usr/bin/env bash
set -euo pipefail

NAME="${1:?base name required, e.g. paper}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"

latexmk -C -outdir="${BUILD_DIR}" -jobname="${NAME}" "${ROOT_DIR}/src/main.tex" || true
rm -rf "${BUILD_DIR}"
echo "[OK] Cleaned ${BUILD_DIR}"
"""

SYNC_PY = r"""#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def escape_tex(text: str) -> str:
    # Keep this conservative: escape only characters that commonly break LaTeX.
    # Allow backslashes so users can write raw LaTeX when needed.
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = []
    for ch in text:
        out.append(replacements.get(ch, ch))
    return "".join(out)


LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CODE_RE = re.compile(r"`([^`]+)`")
BIBKEY_RE = re.compile(r"\[@([A-Za-z0-9:_-]+)\]")


def inline_md_to_tex(s: str) -> str:
    s = LINK_RE.sub(lambda m: rf"\href{{{m.group(2)}}}{{{escape_tex(m.group(1))}}}", s)
    s = BIBKEY_RE.sub(lambda m: rf"\cite{{{m.group(1)}}}", s)
    s = CODE_RE.sub(lambda m: rf"\texttt{{{escape_tex(m.group(1))}}}", s)
    s = s.replace("**", "")  # keep simple; author can refine in LaTeX directly
    return escape_tex(s)


def convert(md: str) -> tuple[str, str, str, str]:
    lines = md.splitlines()
    title = ""
    author = ""
    abstract_lines: list[str] = []

    content_lines: list[str] = []

    i = 0
    in_code = False
    code_lang = ""
    buf_list: list[str] = []
    list_kind: str | None = None  # "itemize" or "enumerate"

    def flush_list() -> None:
        nonlocal buf_list, list_kind
        if not list_kind:
            return
        content_lines.append(r"\begin{" + list_kind + "}")
        for item in buf_list:
            content_lines.append(r"\item " + inline_md_to_tex(item))
        content_lines.append(r"\end{" + list_kind + "}")
        buf_list = []
        list_kind = None

    # Parse title and lightweight author from the default template
    for raw in lines[:30]:
        if raw.startswith("# "):
            title = raw[2:].strip()
        if raw.strip().lower().startswith("*author"):
            author = raw.split(":", 1)[-1].strip().strip("*").strip()

    # Extract abstract block from markdown template: under "## Abstract" until next "## "
    in_abstract = False
    for raw in lines:
        if raw.startswith("## Abstract"):
            in_abstract = True
            continue
        if in_abstract and raw.startswith("## "):
            break
        if in_abstract:
            abstract_lines.append(raw)

    # Convert the rest to LaTeX content. Keep it simple and robust.
    in_body = False
    for raw in lines:
        if raw.startswith("## 1.") or raw.startswith("## Introduction") or raw.startswith("## 1 "):
            in_body = True
        if raw.startswith("## References"):
            break
        if not in_body:
            continue

        line = raw.rstrip("\n")

        if line.startswith("```"):
            if not in_code:
                flush_list()
                in_code = True
                code_lang = line[3:].strip()
                if code_lang == "latex":
                    content_lines.append("% BEGIN raw LaTeX")
                else:
                    content_lines.append(r"\begin{verbatim}")
            else:
                if code_lang == "latex":
                    content_lines.append("% END raw LaTeX")
                else:
                    content_lines.append(r"\end{verbatim}")
                in_code = False
                code_lang = ""
            continue

        if in_code:
            # For ```latex blocks, pass through as-is; otherwise verbatim environment handles.
            content_lines.append(line)
            continue

        if not line.strip():
            flush_list()
            content_lines.append("")
            continue

        if line.startswith("### "):
            flush_list()
            content_lines.append(r"\subsection{" + inline_md_to_tex(line[4:].strip()) + "}")
            continue
        if line.startswith("## "):
            flush_list()
            heading = line[3:].strip()
            # Strip leading numbering like "1. " to keep LaTeX clean
            heading = re.sub(r"^\d+\.\s*", "", heading)
            content_lines.append(r"\section{" + inline_md_to_tex(heading) + "}")
            continue
        if line.startswith("# "):
            continue  # title handled separately

        if re.match(r"^\d+\.\s+", line):
            if list_kind not in (None, "enumerate"):
                flush_list()
            list_kind = "enumerate"
            buf_list.append(re.sub(r"^\d+\.\s+", "", line).strip())
            continue
        if line.startswith("- "):
            if list_kind not in (None, "itemize"):
                flush_list()
            list_kind = "itemize"
            buf_list.append(line[2:].strip())
            continue

        flush_list()
        content_lines.append(inline_md_to_tex(line))

    flush_list()

    title_tex = title or "[Title]"
    author_tex = author or "[Author]"
    abstract_tex = "\n".join([inline_md_to_tex(l) for l in abstract_lines if l.strip()]) or "[Abstract]"
    content_tex = "\n".join(content_lines).strip() or r"\section{Introduction}" + "\n" + "[Intro]"

    return title_tex, author_tex, abstract_tex, content_tex


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: sync_md_to_tex.py <paper.md> <latex_src_dir>")
        return 2

    md_path = Path(sys.argv[1]).resolve()
    src_dir = Path(sys.argv[2]).resolve()

    md = md_path.read_text(encoding="utf-8")
    title, author, abstract_tex, content_tex = convert(md)

    (src_dir / "meta.tex").write_text(
        "\\title{" + escape_tex(title) + "}\n"
        "\\author{" + escape_tex(author) + "}\n"
        "\\date{\\today}\n",
        encoding="utf-8",
    )
    (src_dir / "abstract.tex").write_text(abstract_tex + "\n", encoding="utf-8")
    (src_dir / "content.tex").write_text(content_tex + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


if __name__ == "__main__":
    raise SystemExit(main())
