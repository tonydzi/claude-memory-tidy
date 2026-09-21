#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""First-run contract for memory_scope.py. No LLM, no network, <1s.

WHY THIS EXISTS. The module docstring and README both promise: an undeclared machine
"owns nothing and says so LOUDLY (exit 3)". On a FRESH CLONE there is no memory_scope.json
next to the script (only memory_scope.example.json), and the promise was broken in the
loudest possible way: a bare FileNotFoundError traceback from load_conf(), which is exit 1
plus a stack trace, not exit 3 plus an instruction. A tool whose whole thesis is "fail loud
and actionable, never silently" must not greet its first user with a traceback.

Caught 2026-09-21 by running the repo from a clean clone before linking it in a public
thread. Run:  python3 tests/test_memory_scope_firstrun.py
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "scripts")
PY = sys.executable
fails = []


def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  -- " + detail) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def run_scope(workdir, args):
    """Run a COPY of memory_scope.py in an isolated dir, so the real config is never seen."""
    env = dict(os.environ)
    env.pop("MACHINE_KEY", None)
    p = subprocess.run([PY, os.path.join(workdir, "memory_scope.py")] + args,
                       capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


tmp = tempfile.mkdtemp(prefix="scope-firstrun-")
try:
    shutil.copy(os.path.join(SRC, "memory_scope.py"), os.path.join(tmp, "memory_scope.py"))
    # deliberately NO memory_scope.json here: this is what a fresh clone looks like

    print("missing config")
    rc, out = run_scope(tmp, ["--explain"])
    check("exits 3, the documented loud code", rc == 3, "rc=%s out=%s" % (rc, out[:200]))
    check("no raw traceback in output", "Traceback (most recent call last)" not in out, out[:200])
    check("names the file it wants", "memory_scope.json" in out, out[:200])
    check("tells the operator what to do", "memory_scope.example.json" in out, out[:200])

    print("help")
    rc, out = run_scope(tmp, ["--help"])
    check("--help exits 0 even with no config", rc == 0, "rc=%s out=%s" % (rc, out[:200]))
    check("--help lists the output modes", "--explain" in out and "--list" in out, out[:200])

    print("unreadable config")
    with open(os.path.join(tmp, "memory_scope.json"), "w", encoding="utf-8") as f:
        f.write("{ this is not json")
    rc, out = run_scope(tmp, ["--explain"])
    check("broken JSON also exits 3, not 1", rc == 3, "rc=%s out=%s" % (rc, out[:200]))
    check("broken JSON gives no traceback", "Traceback (most recent call last)" not in out, out[:200])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("")
if fails:
    print("RED: %d failing -> %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("GREEN: all tests pass")
