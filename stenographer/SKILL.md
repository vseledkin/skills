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
- Use `--deps full` when you want best extraction fidelity (creates `.stenographer_venv/` in project root).
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
2. Start capturing dictation into **Raw Notes** (verbatim, minimal edits).
3. After each dictation chunk, respond with:
   - A 3–7 bullet **Normalized Notes** summary
   - A list of **Claims to verify** (each with an ID like `C1`, `C2`)
   - 1–3 **Clarifying questions** that unblock structure or verification

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

## Bundled resources

- Template: `assets/paper_template.md`
- LaTeX template: `assets/latex_project_template/`
- Guidelines: `references/writing_guidelines.md`, `references/citation_rules.md`, `references/review_checklist.md`

[TODO: 1-2 sentences explaining what this skill enables]

## Structuring This Skill

[TODO: Choose the structure that best fits this skill's purpose. Common patterns:

**1. Workflow-Based** (best for sequential processes)
- Works well when there are clear step-by-step procedures
- Example: DOCX skill with "Workflow Decision Tree" -> "Reading" -> "Creating" -> "Editing"
- Structure: ## Overview -> ## Workflow Decision Tree -> ## Step 1 -> ## Step 2...

**2. Task-Based** (best for tool collections)
- Works well when the skill offers different operations/capabilities
- Example: PDF skill with "Quick Start" -> "Merge PDFs" -> "Split PDFs" -> "Extract Text"
- Structure: ## Overview -> ## Quick Start -> ## Task Category 1 -> ## Task Category 2...

**3. Reference/Guidelines** (best for standards or specifications)
- Works well for brand guidelines, coding standards, or requirements
- Example: Brand styling with "Brand Guidelines" -> "Colors" -> "Typography" -> "Features"
- Structure: ## Overview -> ## Guidelines -> ## Specifications -> ## Usage...

**4. Capabilities-Based** (best for integrated systems)
- Works well when the skill provides multiple interrelated features
- Example: Product Management with "Core Capabilities" -> numbered capability list
- Structure: ## Overview -> ## Core Capabilities -> ### 1. Feature -> ### 2. Feature...

Patterns can be mixed and matched as needed. Most skills combine patterns (e.g., start with task-based, add workflow for complex operations).

Delete this entire "Structuring This Skill" section when done - it's just guidance.]

## [TODO: Replace with the first main section based on chosen structure]

[TODO: Add content here. See examples in existing skills:
- Code samples for technical skills
- Decision trees for complex workflows
- Concrete examples with realistic user requests
- References to scripts/templates/references as needed]

## Resources (optional)

Create only the resource directories this skill actually needs. Delete this section if no resources are required.

### scripts/
Executable code (Python/Bash/etc.) that can be run directly to perform specific operations.

**Examples from other skills:**
- PDF skill: `fill_fillable_fields.py`, `extract_form_field_info.py` - utilities for PDF manipulation
- DOCX skill: `document.py`, `utilities.py` - Python modules for document processing

**Appropriate for:** Python scripts, shell scripts, or any executable code that performs automation, data processing, or specific operations.

**Note:** Scripts may be executed without loading into context, but can still be read by Codex for patching or environment adjustments.

### references/
Documentation and reference material intended to be loaded into context to inform Codex's process and thinking.

**Examples from other skills:**
- Product management: `communication.md`, `context_building.md` - detailed workflow guides
- BigQuery: API reference documentation and query examples
- Finance: Schema documentation, company policies

**Appropriate for:** In-depth documentation, API references, database schemas, comprehensive guides, or any detailed information that Codex should reference while working.

### assets/
Files not intended to be loaded into context, but rather used within the output Codex produces.

**Examples from other skills:**
- Brand styling: PowerPoint template files (.pptx), logo files
- Frontend builder: HTML/React boilerplate project directories
- Typography: Font files (.ttf, .woff2)

**Appropriate for:** Templates, boilerplate code, document templates, images, icons, fonts, or any files meant to be copied or used in the final output.

---

**Not every skill requires all three types of resources.**
