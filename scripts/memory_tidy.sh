#!/bin/sh
# =============================================================================
# memory_tidy.sh -- daily quality tidy of Claude Code's always-loaded MEMORY.md.
# macOS / Linux. POSIX sh (it runs under launchd's /bin/sh, not your login shell).
#
# SHAPE -- every step readable and reversible:
#   0. subscription rail only (no paid API key leaks into the run)
#   1. OWNERSHIP  -- memory_scope.py decides which indexes this machine may write
#   2. BACKUP     -- to a LOCAL-ONLY dir (never synced, never committed)
#   3. DETECTORS FIRST -- memory_guard.py --soft. The model is summoned ONLY when
#      there is work, so a quiet day costs ~0 tokens.
#   4. TIDY       -- claude -p on the rendered prompt, with a hard timeout
#   5. VERIFY     -- the guard must print GREEN. The model's own summary is not evidence.
#   6. COUNT      -- one JSONL line per run, so "does anyone use this?" has an answer
#
# Usage:  sh memory_tidy.sh            # normal run (detectors gate the model)
#         sh memory_tidy.sh --force    # tidy even if the detectors are quiet
#         sh memory_tidy.sh --dry-run  # detectors + rendered prompt, never calls the model
# Exit:   0 ok / 1 setup / 2 verify RED / 3 blocked (logged out, undeclared machine)
# =============================================================================
set -u

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
PY="${MEMORY_TIDY_PY:-python3}"
LOG="${MEMORY_TIDY_LOG:-$SCRIPTS/_memory_tidy.log}"
COUNTER="$SCRIPTS/_memory_tidy_usage.jsonl"
SCOPE="$SCRIPTS/memory_scope.py"
GUARD="$SCRIPTS/memory_guard.py"
TMPL="${MEMORY_TIDY_PROMPT:-$SCRIPTS/tidy_prompt.tmpl.md}"
MODEL="${MEMORY_TIDY_MODEL:-opus}"
TIMEOUT="${MEMORY_TIDY_TIMEOUT:-900}"

FORCE=0; DRY=0
for a in "$@"; do
  case "$a" in
    --force)   FORCE=1 ;;
    --dry-run) DRY=1 ;;
  esac
done

# 0. Never bill a paid key for a housekeeping job.
unset ANTHROPIC_API_KEY
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
# launchd/cron hand a process an almost-empty PATH and the CLI usually lives in ~/.local/bin.
PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"; export PATH

NODE="${MACHINE_KEY:-$(hostname -s 2>/dev/null || echo unknown)}"
STAMP=$(date +%Y-%m-%dT%H:%M:%S%z)
echo "==== $STAMP  node=$NODE force=$FORCE dry=$DRY ====" >> "$LOG"
say()   { echo "$@"; echo "$@" >> "$LOG"; }
count() { printf '{"ts":"%s","node":"%s","event":"%s","outcome":"%s","detail":"%s"}\n' \
            "$STAMP" "$NODE" "run" "$1" "$2" >> "$COUNTER"; }

for f in "$SCOPE" "$GUARD" "$TMPL"; do
  [ -f "$f" ] || { say "FAILED: missing $f"; count setup_broken "missing $f"; exit 1; }
done

# 1. OWNERSHIP -------------------------------------------------------------
EXCLUDE=$("$PY" "$SCOPE" --exclude 2>>"$LOG") || {
  say "BLOCKED: machine '$NODE' is not declared in memory_scope.json -- refusing to guess."
  count undeclared_machine "$NODE"; exit 3; }
MEMORY_GUARD_EXCLUDE="$EXCLUDE"; export MEMORY_GUARD_EXCLUDE
OWNED=$("$PY" "$SCOPE" --list 2>>"$LOG")
[ -n "$OWNED" ] || { say "BLOCKED: this machine owns no index."; count owns_nothing "$NODE"; exit 3; }

PRIMARY=$(echo "$OWNED" | while IFS= read -r f; do
            printf '%s %s\n' "$(wc -c < "$f" | tr -d ' ')" "$f"; done | sort -rn | head -1 | cut -d' ' -f2-)
MEMDIR=$(dirname "$PRIMARY")

# 2. BACKUP ----------------------------------------------------------------
# Local-only on purpose: a .bak next to the index rides your sync AND gets committed.
case "$(uname -s)" in
  Darwin) BAKDIR="${MEMORY_TIDY_BACKUP:-$HOME/Library/Application Support/claude-memory-backups}" ;;
  *)      BAKDIR="${MEMORY_TIDY_BACKUP:-$HOME/.local/state/claude-memory-backups}" ;;
esac
mkdir -p "$BAKDIR"
echo "$OWNED" | while IFS= read -r f; do
  proj=$(basename "$(dirname "$(dirname "$f")")")
  cp -f "$f" "$BAKDIR/MEMORY.bak-$proj.md" 2>>"$LOG"
done

# 3. DETECTORS FIRST -------------------------------------------------------
"$PY" "$GUARD" --soft >> "$LOG" 2>&1; SOFT_RC=$?
if [ "$FORCE" -eq 0 ] && [ "$SOFT_RC" -ne 2 ]; then
  say "quiet day: within budget -- model NOT summoned."
  count skipped_quiet "soft=$SOFT_RC"; exit 0
fi

# 4. RENDER + TIDY ---------------------------------------------------------
PROMPT="$SCRIPTS/_tidy_prompt.rendered.md"
{
  printf 'PATHS (resolved for this machine — %s, %s):\n' "$NODE" "$(uname -s)"
  printf -- '- OWNED indexes (tidy ONLY these):\n'
  echo "$OWNED" | sed 's/^/    /'
  printf -- '- ARCHIVE for each: <that index dir>/MEMORY-archive.md (NOT auto-loaded; create if absent)\n'
  printf -- '- topic files: <that index dir>/*.md\n'
  printf -- '- HINTS (read first if present): %s/memory-focus-hints.md\n' "$MEMDIR"
  printf -- '- guard command: MEMORY_GUARD_EXCLUDE="%s" %s %s\n' "$EXCLUDE" "$PY" "$GUARD"
  printf -- '- backup already taken: %s\n' "$BAKDIR"
} > "$PROMPT.paths"
awk -v pf="$PROMPT.paths" '/<!-- PATHS_BLOCK -->/{while((getline l < pf)>0) print l; next} {print}' \
    "$TMPL" > "$PROMPT"
rm -f "$PROMPT.paths"
grep -q '<!-- PATHS_BLOCK -->' "$PROMPT" && { say "FAILED: PATHS block did not render"; count render_failed ""; exit 1; }

if [ "$DRY" -eq 1 ]; then
  say "dry-run: tidy IS needed -- prompt rendered, model NOT called."
  say "  inspect: $PROMPT"
  count dry_run "soft=$SOFT_RC"; exit 0
fi

# A logged-out CLI used to print an error and exit 0 -- routines then stamped green and produced
# nothing. Check before spending the run, and treat it as BLOCKED (not "the tidy failed").
if command -v claude >/dev/null 2>&1; then
  if claude auth status 2>/dev/null | grep -q '"loggedIn": *false'; then
    say "BLOCKED: headless claude CLI is logged out -- tidy not attempted. Fix: claude setup-token"
    count auth_blocked ""; exit 3
  fi
else
  say "BLOCKED: no 'claude' CLI on PATH."; count no_cli ""; exit 3
fi

say "tidy needed -- summoning the model ($MODEL, hard timeout ${TIMEOUT}s)."
# Portable hard timeout: `timeout` is not installed by default on macOS.
"$PY" - "$TIMEOUT" "$PROMPT" "$MODEL" <<'PYEOF' >> "$LOG" 2>&1
import subprocess, sys, os
timeout, prompt, model = int(sys.argv[1]), sys.argv[2], sys.argv[3]
cmd = ["claude", "-p", "Follow the instructions in %s EXACTLY, step by step." % prompt,
       "--model", model, "--dangerously-skip-permissions"]
try:
    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, start_new_session=True)
    sys.exit(p.wait(timeout=timeout))
except subprocess.TimeoutExpired:
    os.killpg(os.getpgid(p.pid), 9)      # kill the whole tree, not just the parent
    sys.exit(124)
PYEOF
CX=$?
echo "---- model exit $CX ----" >> "$LOG"

# 5. VERIFY ----------------------------------------------------------------
"$PY" "$GUARD" >> "$LOG" 2>&1; GRC=$?
if [ "$GRC" -ne 0 ]; then
  say "FAILED: tidy did NOT reach GREEN (guard=$GRC, model exit=$CX). Backup: $BAKDIR"
  count verify_red "guard=$GRC claude=$CX"; exit 2
fi
say "GREEN: index within budget."
count green "claude=$CX"
exit 0
