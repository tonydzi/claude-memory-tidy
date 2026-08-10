#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory_guard.py -- judge the health of Claude Code's always-loaded memory index.

Deterministic, no LLM, no network. Checks every index this machine OWNS (see memory_scope.py):

  budget      bytes / lines / per-entry length
  orphans     a note on disk that nothing points at -- present but unreachable
  dead        a pointer to a file that no longer exists
  duplicates  the same slug listed live twice
  conflicts   *.sync-conflict-* in the memory dir = two machines writing one file

Coverage counts a pointer in MEMORY.md, MEMORY-archive.md, or any hub-*.md.

Exit: 0 GREEN / 1 RED / 2 soft (approaching budget; --soft only) / 3 setup broken.
Usage: memory_guard.py [--soft] [--quiet]
  --soft   pre-emptive trigger for a tidy routine: act before the hard cap
  --quiet  stay silent when healthy (for session-start hooks)
"""
import io, os, re, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_BYTES, MAX_LINES, MAX_ENTRY = 20000, 135, 150
SOFT_BYTES, SOFT_LINES = 15000, 110
GENERATED = {"memory-focus-hints.md"}      # written by tooling, not a memory
SLUG_RE = re.compile(r"\]\(([a-z0-9._-]+\.md)\)")


def owned_indexes():
    p = subprocess.run([sys.executable, os.path.join(HERE, "memory_scope.py"), "--list"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None
    return [l for l in p.stdout.splitlines() if l.strip()]


def read(p):
    with io.open(p, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def check_one(index_path, soft, quiet):
    mem_dir = os.path.dirname(index_path)
    label = os.path.basename(os.path.dirname(mem_dir))
    idx = read(index_path)
    lines = [l.rstrip("\n") for l in idx.splitlines() if l.strip()]
    nbytes, nlines = os.path.getsize(index_path), len(lines)
    over = [l for l in lines if len(l) > MAX_ENTRY]

    arch_p = os.path.join(mem_dir, "MEMORY-archive.md")
    arch = read(arch_p) if os.path.exists(arch_p) else ""
    hubs = "".join(read(os.path.join(mem_dir, f)) for f in os.listdir(mem_dir)
                   if f.startswith("hub-") and f.endswith(".md") and ".sync-conflict-" not in f)

    conflicts = [f for f in os.listdir(mem_dir) if ".sync-conflict-" in f]
    orphans = [f for f in os.listdir(mem_dir)
               if f.endswith(".md") and not f.startswith("MEMORY")
               and ".sync-conflict-" not in f and f not in GENERATED
               and f not in idx and f not in arch and f not in hubs]
    refs = set(SLUG_RE.findall(idx)) | set(SLUG_RE.findall(arch)) | set(SLUG_RE.findall(hubs))
    dead = sorted(s for s in refs if not os.path.exists(os.path.join(mem_dir, s)))
    live = [SLUG_RE.search(l).group(1) for l in lines if SLUG_RE.search(l)]
    dups = sorted({s for s in live if live.count(s) > 1})

    problems = []
    if nbytes > MAX_BYTES:  problems.append("bytes %d > %d" % (nbytes, MAX_BYTES))
    if nlines > MAX_LINES:  problems.append("lines %d > %d" % (nlines, MAX_LINES))
    if over:      problems.append("%d entries over %d chars" % (len(over), MAX_ENTRY))
    if conflicts: problems.append("%d sync-conflict file(s): %s" % (len(conflicts), ", ".join(conflicts[:3])))
    if orphans:   problems.append("%d orphaned note(s) with no pointer: %s" % (len(orphans), ", ".join(orphans[:5])))
    if dead:      problems.append("%d dead pointer(s): %s" % (len(dead), ", ".join(dead[:5])))
    if dups:      problems.append("%d duplicate live line(s): %s" % (len(dups), ", ".join(dups[:5])))

    if not quiet:
        print("[%s] %d bytes / %d lines / %d over-length / %d orphans / %d conflicts"
              % (label, nbytes, nlines, len(over), len(orphans), len(conflicts)))

    if soft:
        if nbytes >= SOFT_BYTES or nlines >= SOFT_LINES or over or orphans:
            print("[%s] SOFT: tidy recommended (>=%dB or >=%d lines or any over-length/orphan)."
                  % (label, SOFT_BYTES, SOFT_LINES))
            return 2
        print("[%s] SOFT: fine, no tidy needed." % label)
        return 0

    if problems:
        print("[%s] RED -> %s" % (label, "; ".join(problems)))
        return 1
    if not quiet:
        print("[%s] GREEN: within budget (<=%dB / <=%d lines / <=%d chars)."
              % (label, MAX_BYTES, MAX_LINES, MAX_ENTRY))
    return 0


def main():
    soft, quiet = "--soft" in sys.argv, "--quiet" in sys.argv
    targets = owned_indexes()
    if targets is None:
        print("RED: memory_scope.py could not resolve ownership for this machine.", file=sys.stderr)
        return 3
    if not targets:
        # Not exit 1: "I found no index at all" is the guard failing, not the index being over
        # budget. Keep the two distinguishable or your dashboards will lie.
        print("RED: this machine owns no MEMORY.md (check memory_scope.json).", file=sys.stderr)
        return 3
    worst = 0
    for t in targets:
        code = check_one(t, soft, quiet)
        if code == 1 or (code == 2 and worst == 0):   # a hard breach outranks a soft hint
            worst = code
    return worst


if __name__ == "__main__":
    sys.exit(main())
