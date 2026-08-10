#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for claude-memory-tidy. No LLM, no network, ~1s.

Everything runs against a TEMPORARY fake ~/.claude tree, so the suite passes on any machine
and never touches your real memory. Run:  python3 tests/test_memory_tidy.py
"""
import io, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "scripts")
PY = sys.executable
fails = []


def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  -- " + detail) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def run(cmd, cwd=None, env=None):
    e = dict(os.environ)
    e.pop("MACHINE_KEY", None)
    if env:
        e.update(env)
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=e)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def fixture(tmp, machine="test-machine", owns="*", never=None):
    """Build scripts/ + projects/ under tmp and return the scripts dir."""
    scripts = os.path.join(tmp, "scripts")
    os.makedirs(scripts)
    for f in ("memory_scope.py", "memory_guard.py", "memory_orphan_cover.py", "memory_fold.py"):
        shutil.copy(os.path.join(SRC, f), scripts)
    conf = {"never": never or [], "never_glob": ["*-worktrees-*"],
            "nodes": {machine: {"owns": owns}}}
    io.open(os.path.join(scripts, "memory_scope.json"), "w", encoding="utf-8").write(
        json.dumps(conf, ensure_ascii=False))

    def mkproj(name, index_body, notes):
        d = os.path.join(tmp, "projects", name, "memory")
        os.makedirs(d)
        io.open(os.path.join(d, "MEMORY.md"), "w", encoding="utf-8").write(index_body)
        for n, body in notes.items():
            io.open(os.path.join(d, n), "w", encoding="utf-8").write(body)
        return d

    mkproj("mine", "# Memory Index\n\n- [Covered](covered.md) — hook\n",
           {"covered.md": "---\nname: covered\ndescription: a covered note\n---\nbody\n",
            "lonely.md": "---\nname: lonely\ndescription: an uncovered note\n---\nbody\n",
            "memory-focus-hints.md": "# generated\n"})
    mkproj("theirs", "# Memory Index\n\n- [Foreign](foreign.md) — hook\n",
           {"foreign.md": "body\n"})
    mkproj("proj-worktrees-tmp", "# Memory Index\n\n- [W](w.md) — hook\n", {"w.md": "body\n"})
    return scripts


print("ownership")
tmp = tempfile.mkdtemp(prefix="cmt-")
try:
    s = fixture(tmp, never=["theirs"])
    env = {"MACHINE_KEY": "test-machine"}
    rc, out = run([PY, os.path.join(s, "memory_scope.py"), "--explain"], env=env)
    check("owns its own project", "+ mine" in out, out)
    check("never-list project is skipped", "+ theirs" not in out, out)
    check("worktree project is skipped", "+ proj-worktrees-tmp" not in out, out)
    rc, out = run([PY, os.path.join(s, "memory_scope.py"), "--list"], env={"MACHINE_KEY": "unknown-box"})
    check("undeclared machine exits 3 loudly", rc == 3 and "not declared" in out, "rc=%s %s" % (rc, out[:120]))

    print("guard")
    rc, out = run([PY, os.path.join(s, "memory_guard.py")], env=env)
    check("uncovered note is reported as an orphan", "lonely.md" in out, out)
    check("generated hints file is NOT an orphan", "memory-focus-hints.md" not in out, out)
    check("foreign index is not judged", "theirs" not in out, out)

    print("orphan coverage")
    rc, out = run([PY, os.path.join(s, "memory_orphan_cover.py"), "--dry-run"], env=env)
    check("dry-run reports the real count, not 0", "would cover 1" in out, out)
    rc, out = run([PY, os.path.join(s, "memory_orphan_cover.py")], env=env)
    arch = io.open(os.path.join(tmp, "projects", "mine", "memory", "MEMORY-archive.md"),
                   encoding="utf-8").read()
    check("pointer uses the note's own description", "an uncovered note" in arch, arch[:200])
    idx = io.open(os.path.join(tmp, "projects", "mine", "memory", "MEMORY.md"), encoding="utf-8").read()
    check("coverage costs 0 live-index budget", "lonely.md" not in idx, idx)
    rc, out = run([PY, os.path.join(s, "memory_guard.py")], env=env)
    check("guard is GREEN after coverage", "GREEN" in out and rc == 0, out)

    print("fold")
    mem = os.path.join(tmp, "projects", "mine", "memory")
    io.open(os.path.join(mem, "MEMORY.md"), "a", encoding="utf-8").write(
        "- [A](a.md) — hook a\n- [B](b.md) — hook b\n- [C](c.md) — hook c\n")
    for n in "abc":
        io.open(os.path.join(mem, n + ".md"), "w", encoding="utf-8").write("body\n")
    mp = os.path.join(tmp, "map.json")
    io.open(mp, "w", encoding="utf-8").write(json.dumps(
        {"hubs": {"hub-demo.md": {"title": "Demo", "hook": "three things", "slugs": ["a", "b", "c"]}}}))
    rc, out = run([PY, os.path.join(s, "memory_fold.py"), "--index", os.path.join(mem, "MEMORY.md"),
                   "--map", mp], env=env)
    hub = io.open(os.path.join(mem, "hub-demo.md"), encoding="utf-8").read()
    idx = io.open(os.path.join(mem, "MEMORY.md"), encoding="utf-8").read()
    check("spoke hook moved VERBATIM (no paraphrase)", "- [A](a.md) — hook a" in hub, hub[:200])
    check("index keeps exactly one line for the hub", idx.count("hub-demo.md") == 1, idx)
    check("spokes are gone from the live index", "](a.md)" not in idx, idx)
    rc, out = run([PY, os.path.join(s, "memory_guard.py")], env=env)
    check("folded notes are still reachable (guard GREEN)", rc == 0 and "GREEN" in out, out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("runner")
rc, out = run(["sh", "-n", os.path.join(SRC, "memory_tidy.sh")])
check("POSIX sh syntax valid", rc == 0, out[:200])

print("")
if fails:
    print("RED: %d failing -> %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("GREEN: all tests pass")
