#!/usr/bin/env bash
set -euo pipefail

QUIET=0
if [[ "${1:-}" == "--quiet" ]]; then
  QUIET=1
fi

say() {
  if [[ "$QUIET" == "0" ]]; then
    echo "$@"
  fi
}

fail() {
  echo "[FAIL] $@" >&2
  exit 1
}

ok() { say "[OK] $@"; }
warn() { say "[WARN] $@"; }
info() { say "[INFO] $@"; }

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
SHELL_PATH="${SHELL:-unknown}"
SHELL_NAME="$(basename "$SHELL_PATH" 2>/dev/null || echo unknown)"

require_cmd() {
  local c="$1"
  if ! command -v "$c" >/dev/null 2>&1; then
    return 1
  fi
  return 0
}

install_hint() {
  local pkg="$1"
  if [[ "$OS" == "darwin" ]]; then
    if command -v brew >/dev/null 2>&1; then
      echo "brew install ${pkg}"
    else
      echo "Install Homebrew, then: brew install ${pkg}"
    fi
    return 0
  fi
  if [[ "$OS" == "linux" ]]; then
    if command -v apt-get >/dev/null 2>&1; then
      echo "sudo apt-get update && sudo apt-get install -y ${pkg}"
      return 0
    fi
    if command -v pacman >/dev/null 2>&1; then
      echo "sudo pacman -S ${pkg}"
      return 0
    fi
    if command -v dnf >/dev/null 2>&1; then
      echo "sudo dnf install ${pkg}"
      return 0
    fi
    echo "Install '${pkg}' using your distro package manager"
    return 0
  fi
  echo "Install '${pkg}' for your OS"
}

info "OS: ${OS}"
info "Shell: ${SHELL_NAME} (${SHELL_PATH})"

# Hard requirements for the skeleton to function.
missing=()
for c in python3 curl; do
  require_cmd "$c" || missing+=("$c")
done

# LaTeX toolchain for PDF compilation.
for c in latexmk lualatex; do
  require_cmd "$c" || missing+=("$c")
done

# Bibliography (default template uses biblatex+biber).
require_cmd biber || missing+=("biber")

# Python project manager (required for dependency bootstrap).
require_cmd uv || missing+=("uv")

# Markdown linter requirement.
require_cmd rumdl || missing+=("rumdl")

if [[ "${#missing[@]}" -gt 0 ]]; then
  say "[FAIL] Missing required tools: ${missing[*]}"
  say ""
  say "Install suggestions (best-effort):"
  for c in "${missing[@]}"; do
    case "$c" in
      python3) say "- python3: $(install_hint python3)" ;;
      curl) say "- curl: $(install_hint curl)" ;;
      latexmk|lualatex|biber)
        if [[ "$OS" == "darwin" ]]; then
          say "- TeX toolchain (${c}): brew install --cask mactex  (or install MacTeX from tug.org)"
        else
          say "- TeX toolchain (${c}): $(install_hint texlive-full)  (or texlive + latexmk + biber)"
        fi
        ;;
      rumdl)
        if require_cmd cargo; then
          say "- rumdl: cargo install rumdl"
        else
          say "- rumdl: $(install_hint rumdl)  (or install Rust + cargo install rumdl)"
        fi
        ;;
      uv)
        if [[ "$OS" == "darwin" ]]; then
          if command -v brew >/dev/null 2>&1; then
            say "- uv: brew install uv"
          else
            say "- uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
          fi
        else
          say "- uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
        fi
        ;;
      *) say "- ${c}: $(install_hint "$c")" ;;
    esac
  done
  exit 1
fi

ok "All required tools are installed."
ok "rumdl: $(rumdl --version 2>/dev/null | head -n 1 || echo installed)"
