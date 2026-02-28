#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("/", " ")
    text = re.sub(r"[^\w\s.-]", "", text, flags=re.UNICODE)
    text = text.strip().replace(" ", "-")
    text = re.sub(r"-{2,}", "-", text)
    return (text[:160] if text else "reference").strip("-") or "reference"


def run(
    cmd: list[str],
    *,
    check: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def fetch_bytes(url: str) -> tuple[bytes, str]:
    # Use curl for redirects and reasonable TLS defaults.
    proc = subprocess.run(
        ["curl", "-L", "-sS", "-D", "-", url],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    raw = proc.stdout
    header_end = raw.rfind(b"\r\n\r\n")
    headers = b""
    body = raw
    if header_end != -1:
        headers = raw[:header_end]
        body = raw[header_end + 4 :]
    content_type = ""
    for line in headers.splitlines():
        if line.lower().startswith(b"content-type:"):
            content_type = line.split(b":", 1)[1].strip().decode("utf-8", "ignore")
    return body, content_type


def looks_like_pdf(url: str, content_type: str, body: bytes) -> bool:
    if "pdf" in content_type.lower():
        return True
    if urlparse(url).path.lower().endswith(".pdf"):
        return True
    return body.startswith(b"%PDF")


def ensure_dirs(project_root: Path) -> tuple[Path, Path]:
    refs = project_root / "References"
    refs.mkdir(parents=True, exist_ok=True)
    tmp = refs / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    return refs, tmp


def append_index(refs_dir: Path, title: str, slug: str, url: str, bibkey: str | None) -> None:
    index = refs_dir / "index.md"
    if not index.exists():
        index.write_text("# References (local archive)\n\n## Index\n\n", encoding="utf-8")

    # Ensure the list is preceded by a blank line.
    existing = index.read_text(encoding="utf-8", errors="ignore")
    prefix = "" if existing.endswith("\n\n") else "\n"

    line = f"- [{title}](./{slug}.md) — <{url}>"
    if bibkey:
        line += f" (`{bibkey}`)"
    line += f" — retrieved {now_utc_iso()}\n"
    with index.open("a", encoding="utf-8") as f:
        f.write(prefix + line)


def extract_pdf_to_text(pdf_path: Path) -> str:
    try:
        import fitz  # type: ignore

        doc = fitz.open(pdf_path)
        parts: list[str] = []
        for page in doc:
            t = (page.get_text("text") or "").strip()
            if t:
                parts.append(t)
        return "\n\n".join(parts) + "\n"
    except Exception:
        pass

    try:
        import pdfplumber  # type: ignore

        parts = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for p in pdf.pages:
                t = (p.extract_text() or "").strip()
                if t:
                    parts.append(t)
        return "\n\n".join(parts) + "\n"
    except Exception:
        pass

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        parts = []
        for page in reader.pages:
            t = (page.extract_text() or "").strip()
            if t:
                parts.append(t)
        return "\n\n".join(parts) + "\n"
    except Exception:
        pass

    if shutil.which("pdftotext"):
        with tempfile.TemporaryDirectory() as td:
            out_txt = Path(td) / "out.txt"
            subprocess.run(["pdftotext", str(pdf_path), str(out_txt)], check=False)
            if out_txt.exists():
                return out_txt.read_text(encoding="utf-8", errors="ignore")

    return ""


def html_to_md(url: str, html: str) -> tuple[str, str]:
    # Prefer pandoc when available for higher fidelity.
    if shutil.which("pandoc"):
        with tempfile.TemporaryDirectory() as td:
            in_path = Path(td) / "in.html"
            in_path.write_text(html, encoding="utf-8", errors="ignore")
            proc = subprocess.run(
                ["pandoc", str(in_path), "--from=html", "--to=gfm", "--wrap=none"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            md = (proc.stdout or "").strip()
            if md:
                title = ""
                m = re.search(r"^#\s+(.+)$", md, flags=re.MULTILINE)
                if m:
                    title = m.group(1).strip()
                return (title or "Reference"), md + "\n"

    title = ""
    md = ""
    try:
        import trafilatura  # type: ignore

        extracted = trafilatura.extract(html, include_comments=False, include_tables=True, output_format="markdown")
        if extracted:
            md = extracted
        meta = trafilatura.metadata.extract_metadata(html)
        if meta and getattr(meta, "title", None):
            title = meta.title
    except Exception:
        pass

    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()

    if not md:
        try:
            from bs4 import BeautifulSoup  # type: ignore

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text("\n")
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            md = text
        except Exception:
            md = html

    return (title or url), md.strip() + "\n"


def select_latex_dir(project_root: Path, paper: str | None, latex_dir_arg: str | None) -> Path | None:
    if latex_dir_arg:
        p = Path(latex_dir_arg)
        if not p.is_absolute():
            p = (project_root / p).resolve()
        return p if p.exists() else None

    if paper:
        candidate = project_root / f"{paper}_latex"
        if candidate.exists():
            return candidate

    candidates = sorted([p for p in project_root.glob("*_latex") if p.is_dir()])
    if len(candidates) == 1:
        return candidates[0]
    return None


def update_bib(latex_dir: Path, bibkey: str, title: str, url: str, accessed_iso: str) -> None:
    bib_path = latex_dir / "src" / "references.bib"
    bib_path.parent.mkdir(parents=True, exist_ok=True)
    if bib_path.exists():
        existing = bib_path.read_text(encoding="utf-8", errors="ignore")
        if re.search(rf"@\w+\{{\s*{re.escape(bibkey)}\s*,", existing):
            return

    entry = (
        f"@online{{{bibkey},\n"
        f"  title   = {{{title}}},\n"
        f"  url     = {{{url}}},\n"
        f"  urldate = {{{accessed_iso[:10]}}},\n"
        f"}}\n\n"
    )
    with bib_path.open("a", encoding="utf-8") as f:
        f.write(entry)


def ensure_deps(project_root: Path, level: str) -> None:
    if level == "none":
        return
    if not shutil.which("uv"):
        raise SystemExit(
            "[FAIL] uv is required to install optional dependencies. Install it (macOS: `brew install uv`, or `curl -LsSf https://astral.sh/uv/install.sh | sh`)."
        )

    # Ensure a uv-managed virtualenv exists and install extras declared in pyproject.toml.
    # This creates/updates `.venv/` at the project root by default.
    extra = level
    run(["uv", "sync", "--quiet", "--extra", extra], cwd=project_root)

    py = project_root / ".venv" / "bin" / "python"
    if not py.exists():
        raise SystemExit("[FAIL] uv sync did not create .venv/bin/python as expected.")
    env = os.environ.copy()
    env["STENOGRAPHER_DEPS_READY"] = "1"
    os.execve(str(py), [str(py), *sys.argv], env)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive a cited source into root References/ as Markdown (and PDF+MD when applicable)."
    )
    parser.add_argument("url", help="Source URL (HTML or PDF)")
    parser.add_argument("--paper", help="Base name (stem) like 'paper' (used to locate <paper>_latex/)")
    parser.add_argument("--latex-dir", help="Override path to *_latex directory")
    parser.add_argument("--title", help="Override title used for filename and headings")
    parser.add_argument("--slug", help="Override filename slug (without extension)")
    parser.add_argument("--bibkey", help="Bib key to use for citations (use in Markdown as [@bibkey])")
    parser.add_argument("--update-bib", action="store_true", help="Append an @online entry to LaTeX references.bib")
    parser.add_argument(
        "--deps",
        choices=["none", "basic", "full"],
        default="none",
        help="Install optional deps via uv into .venv (best fidelity: full).",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    refs_dir, tmp_dir = ensure_dirs(project_root)

    if args.deps != "none" and os.environ.get("STENOGRAPHER_DEPS_READY") != "1":
        ensure_deps(project_root, args.deps)

    body, content_type = fetch_bytes(args.url)
    accessed = now_utc_iso()

    if looks_like_pdf(args.url, content_type, body):
        tmp_pdf = tmp_dir / "download.pdf"
        tmp_pdf.write_bytes(body)

        url_name = Path(urlparse(args.url).path).name
        title = args.title or (Path(url_name).stem if url_name else "Reference")
        slug = args.slug or slugify(title)

        pdf_out = refs_dir / f"{slug}.pdf"
        md_out = refs_dir / f"{slug}.md"
        shutil.copyfile(tmp_pdf, pdf_out)

        extracted = extract_pdf_to_text(pdf_out)
        header = (
            f"---\nsource_url: {args.url}\nretrieved_utc: {accessed}\nformat: pdf\n"
            + (f"bibkey: {args.bibkey}\n" if args.bibkey else "")
            + "---\n\n"
            + f"# {title}\n\n"
        )
        if extracted.strip():
            md_out.write_text(header + extracted, encoding="utf-8")
        else:
            md_out.write_text(
                header + "PDF saved alongside this file. Text extraction produced empty output.\n",
                encoding="utf-8",
            )

        append_index(refs_dir, title, slug, args.url, args.bibkey)

        latex_dir = select_latex_dir(project_root, args.paper, args.latex_dir)
        if args.update_bib and args.bibkey and latex_dir:
            update_bib(latex_dir, args.bibkey, title, args.url, accessed)

        print(json.dumps({"slug": slug, "title": title, "md": str(md_out), "pdf": str(pdf_out)}, ensure_ascii=False))
        return 0

    html = body.decode("utf-8", errors="ignore")
    title, md = html_to_md(args.url, html)
    if args.title:
        title = args.title
    slug = args.slug or slugify(title)

    md_out = refs_dir / f"{slug}.md"
    header = (
        f"---\nsource_url: {args.url}\nretrieved_utc: {accessed}\nformat: html\n"
        + (f"bibkey: {args.bibkey}\n" if args.bibkey else "")
        + "---\n\n"
        + f"# {title}\n\n"
    )
    md_out.write_text(header + md, encoding="utf-8")
    append_index(refs_dir, title, slug, args.url, args.bibkey)

    latex_dir = select_latex_dir(project_root, args.paper, args.latex_dir)
    if args.update_bib and args.bibkey and latex_dir:
        update_bib(latex_dir, args.bibkey, title, args.url, accessed)

    print(json.dumps({"slug": slug, "title": title, "md": str(md_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
