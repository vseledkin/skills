---
name: stenographer
description: Convert a user's dictated brainstorm (raw transcript, voice notes, meeting notes, scattered bullets) into a coherent scientific article draft with a rigorous structure, explicit assumptions, and verifiable citations. Use when the user wants an interactive "think aloud" workflow where Codex asks clarifying questions, distinguishes hypotheses from facts, optionally searches the web to confirm or refute claims, and—only with the user's approval—incorporates sourced statements and links into the evolving paper.
---

# Stenographer

## Overview

Turn messy spoken ideas into a publication-style draft by running two tight loops: (1) **capture → normalize → structure**, and (2) **claims → evidence → citations → integrate**.

Primary outputs (unless the user requests otherwise):

- `paper.md` (full draft, scientific tone)
- `paper.pdf` (continuously compiled from LaTeX)
- `paper_latex/` (LaTeX project folder; has `src/` and `build/`)
- `outline.md` (section outline + open questions)
- `evidence.md` (claim/evidence table + source links)
- `References/` (local archive of every cited source)

Use `assets/paper_template.md` as the starting scaffold.
Use `assets/latex_project_template/` as the LaTeX scaffold.

## Deliverable layout (default)

For a base name like `paper` (same stem everywhere):

- `paper.md`
- `paper.pdf` (generated)
- `References/` (source archive; see below)
- `paper_latex/src/` (`main.tex`, `preamble.tex`, `macros.tex`, `references.bib`, `latexmkrc`)
- `paper_latex/src/meta.tex`, `paper_latex/src/abstract.tex`, `paper_latex/src/content.tex` (auto-synced from `paper.md`)
- `paper_latex/build/` (aux/build artifacts)

If multiple output languages are requested, create one full variant per language and add the language tag to filenames:

- `paper_en.md`, `paper_en.pdf`, `paper_en_latex/`
- `paper_ru.md`, `paper_ru.pdf`, `paper_ru_latex/`

Initialize this layout by running the bundled initializer script:

- `python3 ~/.codex/skills/stenographer/scripts/init_steno_paper.py paper --dir .`
- Multi-language example: `python3 ~/.codex/skills/stenographer/scripts/init_steno_paper.py paper --dir . --langs en,ru`

Then build/watch:

- `./paper_latex/scripts/build.sh paper` (build once; writes `paper.pdf`)
- `./paper_latex/scripts/watch.sh paper` (continuous compile; keeps `paper.pdf` updated)

If `make` is available on the system, the initializer also creates a `Makefile` so `make pdf` / `make watch` work as shortcuts.

## Source archiving (required)

Rule: if the paper cites a source, the project must contain a local copy in `References/`:

- For a web page: `References/<human-title>.md` (best-effort Markdown capture).
- For a PDF: `References/<human-title>.pdf` + `References/<human-title>.md` (extracted text).

Update `References/index.md` so the project stays searchable.

Use the project helper script created by the initializer:

- From project root: `./paper_latex/scripts/add_reference.py <url> --paper paper --bibkey <key> --update-bib --deps full`

Notes:

- Use `--deps full` when you want best extraction fidelity (runs `uv sync --extra full` and creates/uses `.venv/` in project root).
- Use `--title` if the source title is messy; this controls human-readable filenames.
- Cite in Markdown as `[@bibkey]` so LaTeX can render `\\cite{bibkey}`.
- In multi-language projects, run the helper against the specific LaTeX variant using `--latex-dir`, e.g. `--latex-dir paper_en_latex`.

## Quick start (first 5 minutes)

1. Ask for (or infer) the basics:
   - Topic + intended contribution (what is new/useful?)
   - Target audience / venue (blog post vs workshop paper vs internal memo)
   - Output language(s) (one or more; e.g. `en`, `ru`, `de`). If multiple languages are requested, produce one full output variant per language and add the language tag to filenames (e.g. `paper_en.md`, `paper_en.pdf`, `paper_en_latex/`).
   - Citation style (default: numeric)
   - Whether web browsing is allowed for this task (and any domains to prefer/avoid)
2. Preflight: ensure the project has all required tooling before producing artifacts:
   - Run `./doctor.sh` from the project root.
   - If it fails, follow its OS/shell-specific install suggestions.
3. Start capturing dictation into **Raw Notes** (verbatim, minimal edits).
4. After each dictation chunk, respond with:
   - A 3–7 bullet **Normalized Notes** summary
   - A list of **Claims to verify** (each with an ID like `C1`, `C2`)
   - 1–3 **Clarifying questions** that unblock structure or verification

## Python environment (uv)

Each stenographer project is bootstrapped as a local `uv`-managed Python project:

- Dependencies live in `pyproject.toml` as optional extras (`basic`, `full`).
- The virtualenv lives at `.venv/`.

For best reference capture fidelity up front, run:

- `uv sync --extra full`

## Language correctness (template translation)

Rule: each language variant must be fully written in its target language, including headings and boilerplate text.

Bootstrap behavior:

- The initializer creates each Markdown draft from an English template.
- If the user requests a non-English language, the initializer adds a note at the top of `<stem>.md` instructing you to translate the template into that language before continuing.

Ongoing behavior:

- When editing a non-English variant, keep all newly added prose in that language.
- The PDF inherits section titles and content from the Markdown via the sync step, so language correctness in Markdown implies language correctness in PDF.

## Realtime update loop (dictation → files → preview)

Goal: after each user dictation chunk, update *all* deliverables so the user can immediately inspect the latest `*.md` and `*.pdf` if they want.

### A) Start live compilation (recommended)

For each language variant you are actively editing, run the watcher:

- Single language: `./paper_latex/scripts/watch.sh paper`
- Multi-language: run one watcher per variant, e.g.:
  - `./paper_en_latex/scripts/watch.sh paper_en`
  - `./paper_ru_latex/scripts/watch.sh paper_ru`

In watch mode, any change to `<stem>.md` is synced into `*_latex/src/` and triggers rebuild; the resulting PDF is copied next to the Markdown as `../<stem>.pdf`.

### B) Dictation turn protocol (every time the user speaks)

For each dictation chunk:

1. Update the appropriate Markdown draft file(s) (`<stem>.md`).
2. Ensure Markdown remains lint-clean (required): `rumdl check .` (the watch/build scripts also run this).
3. Ensure LaTeX sync is up to date (automatic in watch mode):
   - Regenerates `*_latex/src/{meta,abstract,content}.tex` from `<stem>.md`.
4. Ensure the PDF artifact is current:
   - Watch mode: continuously updated and copied to `../<stem>.pdf`.
   - Build-on-demand: run `./<stem>_latex/scripts/build.sh <stem>`.
5. Offer immediate preview:
   - If the user wants to review outputs now, point them to the updated paths: `<stem>.md` and `<stem>.pdf` (and ask which one to open/inspect).

### C) If the user asks to “show the PDF now”

Confirm which language variant they mean (if multiple), then provide the exact path to the freshest `*.pdf` next to the corresponding `*.md`. Keep the loop tight: review → edit → rerender → recheck.

## Resume in a new session (recover current state)

It is common to reconnect mid-project from a fresh chat session. Use this protocol to quickly recover the current state and continue without guessing.

1. Identify the project root (the folder that contains `pyproject.toml`, `References/`, and one or more `*_latex/` folders).
2. Run the status helper (created by the initializer):
   - `./status.py`
   - If it does not exist (older projects), run: `python3 ~/.codex/skills/stenographer/scripts/project_status.py .`
3. Based on the report:
   - Restart watch mode for the active language variant(s) so PDFs update live.
   - If linting fails, fix Markdown issues first (`rumdl check .`) before continuing.
4. Ask the user what they want to review now:
   - The current draft Markdown (`<stem>.md`)
   - The current PDF (`<stem>.pdf`)
   - The outline/evidence tables (`outline.md`, `evidence.md`)

## Workflow (dictation → paper)

### 0) Ground rules (always)

- Do not silently "upgrade" a user's idea into a factual statement.
- For every non-trivial factual claim that is not common knowledge, attach a citation or label it as an assumption/hypothesis.
- If web browsing is disallowed, do not browse; instead flag claims as *unverified* and ask the user for sources or permission.
- Ask for explicit approval before adding external sources to the paper (user can approve per-source or per-batch).
- Prefer minimal, high-quality citations (primary sources, standards, canonical textbooks, reputable surveys).

### 1) Intake & scope

Create/confirm:

- Working title (can be temporary)
- 1–2 sentence contribution statement
- Definitions for key terms (avoid ambiguity)
- Scope boundaries (what is explicitly *out of scope*)

If the user is brainstorming, offer 2–3 plausible paper framings (e.g., "position paper", "survey", "methods note") and ask which one to pursue.

### 2) Capture (Raw Notes)

Maintain a verbatim-ish **Raw Notes** section in `outline.md` (or in the chat if the user doesn't want files yet). Do not over-edit; preserve uncertainty and hedging.

### 3) Normalize (turn speech into structured units)

Rewrite Raw Notes into items tagged like:

- `Claim:` testable/falsifiable statement
- `Hypothesis:` proposed mechanism/explanation
- `Definition:` term mapping
- `Observation:` anecdote/experience
- `Method:` steps/algorithm/protocol
- `Question:` missing info to ask the user
- `TODO:` follow-up work

Assign stable IDs:

- Claims: `C1, C2, ...`
- Hypotheses: `H1, H2, ...`
- Methods: `M1, M2, ...`

### 4) Paper skeleton (use the template)

Copy `assets/paper_template.md` into `paper.md` and fill top-down:

- Abstract (draft early; revise often)
- Introduction (problem, motivation, contribution)
- Related work (only after you know the claims)
- Approach / Methods (what is actually done)
- Results / Examples (even if qualitative; be concrete)
- Discussion (implications, tradeoffs)
- Limitations (be explicit)
- Conclusion (what the reader should remember)

### 5) Evidence loop (web research + citation)

Build an `evidence.md` table with columns:

- `ID` (e.g., `C3`)
- `Claim text`
- `Status` (unverified / supported / contradicted / unclear)
- `Best sources` (links, DOI, standard, paper)
- `Notes` (what the source actually supports; avoid overclaiming)

When web browsing is allowed:

1. Propose search queries for each claim cluster.
2. Browse and collect 1–3 best sources per claim (prefer primary sources).
3. Summarize each source in 2–4 sentences focused on what it *does* and *does not* support.
4. Ask: "OK to cite these in the paper?" (include a short list).
5. Only then integrate: add citations inline and update `References`.

If sources disagree, represent the disagreement explicitly and cite both sides.

### 5.1) Keep Markdown and LaTeX in sync

Treat the Markdown file as the user-facing draft and the LaTeX project as the publication-quality renderer.

Workflow rule:

- Every time you modify `paper.md`, also ensure the LaTeX side is updated (at minimum by re-running the sync step; optionally by improving LaTeX-specific rendering for tables/figures).

Default sync mechanism (no extra dependencies):

- `paper_latex/scripts/sync_md_to_tex.py` converts a subset of Markdown into LaTeX and writes:
  - `paper_latex/src/meta.tex`
  - `paper_latex/src/abstract.tex`
  - `paper_latex/src/content.tex`

When the user needs rich formatting:

- Put complex tables/figures directly in LaTeX:
  - In Markdown, add a fenced block ```latex ...``` with the exact LaTeX snippet.
  - The sync step will pass ` ```latex ` blocks through as raw LaTeX.

For citations:

- Prefer bibkeys and cite them in Markdown as `[@bibkey]` so the sync step produces `\\cite{bibkey}` in LaTeX.
- Add the full entry to `paper_latex/src/references.bib` (after user approval).

### 6) Drafting style rules (scientific best practices)

- Make the argument falsifiable: clearly separate **what is proposed** vs **what is observed** vs **what is established**.
- Avoid rhetorical overreach ("proves", "always", "solves") unless the evidence truly supports it.
- Prefer precise nouns/verbs over adjectives.
- Use consistent terminology; keep a glossary if needed.
- Keep paragraphs single-purpose: topic sentence → support → takeaway.

### 7) Review & consistency checks

Before calling the draft "ready", run this checklist:

- Every core claim in Abstract/Intro has either a citation or a clearly marked hypothesis label.
- The Methods section is specific enough that another person could reproduce the approach in principle.
- Limitations are real (not performative) and match the scope.
- References are complete and clickable; no dead links if possible.

If useful, generate a "Claim map" appendix: list `C*` and where each is addressed (section pointers).

## Citation format (default)

Use numeric citations like `[1]` in the text and a `References` section with numbered entries. Each entry should include at least a title + venue/publisher + year + a stable link (DOI/URL).

If the user requests a different style (APA/MLA/BibTeX), switch, but stay consistent throughout.

## Tooling (LaTeX/PDF)

Preferred toolchain:

- `latexmk` + TeX Live / MacTeX
- Engine: `lualatex` (default in template)
- Bibliography: `biblatex` + `biber` (default in template)

On systems without LaTeX tooling, install:

- macOS (Homebrew): `brew install --cask mactex` (or `basictex` + needed packages)
- Ubuntu/Debian: `sudo apt-get install texlive-latex-extra texlive-bibtex-extra biber latexmk`
- Arch: `sudo pacman -S texlive-most biber`

If `biber` is missing or broken, fall back to `natbib` + `bibtex` (lower fidelity but widely available).

Optional (nice-to-have, not required by default workflow):

- `pandoc` for higher-fidelity Markdown→LaTeX conversion
- `fswatch`/`entr` for event-based file watching (the template watch script works without them)

## Markdown linting (required)

All Markdown files produced by this workflow must be checked with `rumdl` (RoomDL):

- Project-wide: `rumdl check .` (uses `.rumdl.toml` created by the initializer)
- Via Makefile: `make lint`

If `rumdl` is missing, `./doctor.sh` will fail and provide installation instructions for the user's OS/shell.

## Bundled resources

- Template: `assets/paper_template.md`
- LaTeX template: `assets/latex_project_template/`
- Guidelines: `references/writing_guidelines.md`, `references/citation_rules.md`, `references/review_checklist.md`
