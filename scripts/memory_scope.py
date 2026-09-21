#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory_scope.py -- WHICH MEMORY.md indexes does THIS machine own (and may write)?

WHY THIS EXISTS. ~/.claude/projects/ holds a mix of three things:
  (a) this machine's OWN always-loaded indexes  -> tidy them;
  (b) indexes SYNCED byte-identical from another machine (Syncthing/Dropbox/etc.) whose own
      tidy owns them -> a SECOND writer there produces sync-conflicts and loses memory;
  (c) throwaway worktree projects with 2-line indexes -> tidying them is pure noise.
A tool that globs `projects/*/memory/MEMORY.md` and writes to everything it finds is the bug.
So ownership is DECLARED (allowlist), never guessed.

Output modes:
  --list      print every index path this machine owns (one per line)
  --exclude   print project dir names to EXCLUDE, comma-joined
  --explain   human table: every project found, owned yes/no, and WHY

Config: memory_scope.json next to this file. An unknown machine owns nothing and says so
LOUDLY (exit 3): a machine that quietly tidies nothing looks identical to a healthy one.
"""
import json, os, sys, glob, fnmatch

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.join(HERE, "memory_scope.json")
PROJ_ROOT = os.path.normpath(os.path.join(HERE, "..", "projects"))


def node_key():
    """Same identity source as the rest of the fleet (fleet_nodes.json is keyed by this)."""
    for env in ("MACHINE_KEY", "COMPUTERNAME"):
        v = os.environ.get(env)
        if v:
            return v.strip()
    try:
        import socket
        return socket.gethostname().split(".")[0]
    except Exception:
        return ""


def load_conf():
    """-> conf dict, or None after printing an ACTIONABLE reason on stderr.

    A fresh clone ships memory_scope.example.json and no memory_scope.json, so this is the
    very first thing a new operator hits. Failing here with a raw traceback contradicts the
    contract this file documents (exit 3, loudly): a stack trace is neither loud nor
    actionable. Updated 2026-09-21 after a clean-clone run produced FileNotFoundError.
    """
    try:
        with open(CONF, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("RED: no %s next to this script -- refusing to guess which indexes this machine "
              "may write.\n     Start from the shipped template:\n"
              "       cp %s %s\n"
              "     then declare this node (key: %r) in its \"nodes\" map."
              % (os.path.basename(CONF), os.path.join(HERE, "memory_scope.example.json"),
                 CONF, node_key()), file=sys.stderr)
        return None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print("RED: %s is not readable JSON (%s) -- refusing to run on a config I cannot parse.\n"
              "     Fix the file or re-copy memory_scope.example.json over it."
              % (CONF, e), file=sys.stderr)
        return None


def projects():
    """Every project dir that actually HAS an always-loaded index, sorted."""
    out = []
    for p in sorted(glob.glob(os.path.join(PROJ_ROOT, "*", "memory", "MEMORY.md"))):
        out.append((os.path.basename(os.path.dirname(os.path.dirname(p))), os.path.normpath(p)))
    return out


def classify(conf, key):
    """-> (owned, skipped) where each item is (project_name, path, reason)."""
    node = conf.get("nodes", {}).get(key)
    if node is None:
        return None, None
    owns = node.get("owns", [])
    never = conf.get("never", [])
    never_glob = conf.get("never_glob", [])
    owned, skipped = [], []
    for name, path in projects():
        if name in never:
            skipped.append((name, path, "never: owned by another node (synced byte-identical)"))
            continue
        if any(fnmatch.fnmatch(name, g) for g in never_glob):
            skipped.append((name, path, "never_glob: throwaway/foreign project"))
            continue
        if owns == "*" or any(fnmatch.fnmatch(name, g) for g in owns):
            owned.append((name, path, "declared in owns"))
        else:
            skipped.append((name, path, "not in this node's owns list"))
    return owned, skipped


USAGE = """usage: memory_scope.py [--explain | --list | --exclude]

Which always-loaded MEMORY.md indexes does THIS machine own (and may write)?

  --explain   (default) human table: every index found, owned yes/no, and WHY
  --list      print every index path this machine owns, one per line
  --exclude   print project dir names to EXCLUDE, comma-joined (for memory_guard.py)
  --help      this text

Config: memory_scope.json next to this script (start from memory_scope.example.json).
Ownership is DECLARED, never guessed: an undeclared machine owns nothing and exits 3.
"""


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(USAGE, end="")
        return 0
    key = node_key()
    conf = load_conf()
    if conf is None:
        return 3
    owned, skipped = classify(conf, key)
    if owned is None:
        print("RED: node %r is not declared in %s -- refusing to guess ownership. "
              "Add it (owns: []) before running the tidy." % (key, os.path.basename(CONF)),
              file=sys.stderr)
        return 3

    if "--exclude" in sys.argv:
        # memory_guard.py takes a comma-separated list of project dir names to skip.
        print(",".join(n for n, _, _ in skipped))
        return 0
    if "--list" in sys.argv:
        for _, p, _ in owned:
            print(p)
        return 0
    # --explain (default)
    print("node: %s   config: %s" % (key, CONF))
    print("OWNED (this node tidies):")
    for n, p, why in owned or []:
        print("  + %-70s %s" % (n, why))
    if not owned:
        print("  (none)")
    print("SKIPPED (hands off):")
    for n, p, why in skipped or []:
        print("  - %-70s %s" % (n, why))
    return 0


if __name__ == "__main__":
    sys.exit(main())
