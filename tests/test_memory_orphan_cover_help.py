#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Red-first guard: `memory_orphan_cover.py --help` must answer, on ANY machine.

The script parses sys.argv by hand (no argparse), so --help used to fall through to the
scope lookup and die with `RED: no owned index found` + exit 1 on a clean clone. A tool
whose --help is a red error teaches the reader that the tool is broken, and --help is the
first evidence anyone collects before deciding something is impossible.

Contract: --help / -h -> usage text on stdout, exit 0, no index required, nothing written.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "memory_orphan_cover.py")

fails = 0


def check(name, ok, detail=""):
    global fails
    print(("  ok   " if ok else "  FAIL ") + name + (("  -- " + detail) if detail and not ok else ""))
    if not ok:
        fails += 1


for flag in ("--help", "-h"):
    p = subprocess.run([sys.executable, SCRIPT, flag], capture_output=True, text=True)
    check("%s exits 0" % flag, p.returncode == 0, "rc=%d stderr=%s" % (p.returncode, (p.stderr or "").strip()[:80]))
    check("%s prints usage on stdout" % flag, "Usage:" in (p.stdout or ""), "stdout=%r" % (p.stdout or "")[:80])
    check("%s does not print the no-index error" % flag, "no owned index" not in (p.stderr or ""))

print("GREEN: all tests pass" if not fails else "RED: %d check(s) failed" % fails)
sys.exit(1 if fails else 0)
