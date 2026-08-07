#!/usr/bin/env bash
# install.sh - install the hermes-prime-bridge plugin into a native Hermes Agent.
# Works from a local working tree (dev) or a git URL (any host).
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PLUGIN_NAME="hermes-prime-bridge"
PLUGINS_DIR="${HERMES_HOME}/plugins"
TARGET="${PLUGINS_DIR}/${PLUGIN_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${1:-$SCRIPT_DIR/..}"   # default: this working tree

echo "== hermes-prime-bridge installer =="
echo "  Source     : ${SOURCE}"
echo "  Target     : ${TARGET}"
echo "  Hermes home: ${HERMES_HOME}"

# ---- locate Hermes command -------------------------------------------------
hermes_cmd=""
for cand in "$(command -v hermes 2>/dev/null)" "$HOME/.local/bin/hermes" "$HERMES_HOME/hermes-agent/venv/bin/hermes"; do
  if [ -n "$cand" ] && [ -x "$cand" ]; then hermes_cmd="$cand"; break; fi
done
echo "  Hermes cmd : ${hermes_cmd:-<not found>}"

# ---- (re)install plugin tree ----------------------------------------------
if [ -e "$TARGET" ]; then
  echo "Removing existing plugin dir: ${TARGET}"
  rm -rf "$TARGET"
fi
mkdir -p "$PLUGINS_DIR"

# Use git clone --recurse-submodules for BOTH local and remote sources so the
# prime-agent submodule is materialized as an independent, pinned checkout
# (rsync would strip git metadata and break the live-upstream guarantee).
case "$SOURCE" in
  git@*|https://*|git://*|ssh://*)
    echo "Cloning ${SOURCE} with submodules..."
    git clone --recurse-submodules "$SOURCE" "$TARGET"
    ;;
  *)
    if [ -d "$SOURCE/.git" ] || [ -f "$SOURCE/.git" ]; then
      echo "Cloning local tree ${SOURCE} with submodules..."
      git clone --recurse-submodules "$SOURCE" "$TARGET"
    else
      echo "Source has no git metadata; copying files (submodule may be missing)."
      mkdir -p "$TARGET"
      cp -r "$SOURCE"/. "$TARGET"/
    fi
    ;;
esac

# ---- verify submodule materialization --------------------------------------
if [ -e "$TARGET/vendor/prime-agent/prime-agent-runtime/src/rlm/__init__.py" ]; then
  echo "  OK: prime-agent runtime source present."
  rev="$(git -C "$TARGET/vendor/prime-agent" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  echo "      vendored prime-agent @ ${rev}"
else
  echo "  WARNING: prime-agent runtime missing; bridge rlm features disabled."
  echo "  Fix with: git -C ${TARGET} submodule update --init --recursive"
fi

# ---- enable + diagnose -----------------------------------------------------
if [ -n "$hermes_cmd" ]; then
  "$hermes_cmd" plugins enable "$PLUGIN_NAME" >/dev/null 2>&1 || true
  echo
  echo "== Hermes plugins (matching) =="
  "$hermes_cmd" plugins list 2>/dev/null | grep -i "${PLUGIN_NAME}" || true
  echo
  echo "== Hermes doctor =="
  "$hermes_cmd" doctor || true
else
  echo "NOTE: Hermes command not found; plugin tree installed but not enabled/diagnosed."
fi
echo
echo "Done. Validate with:  hermes tools list   |   hermes"
