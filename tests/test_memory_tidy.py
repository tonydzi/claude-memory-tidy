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

    # The index above had no hub section, so the fold created one. The other branch -- an index
    # that ALREADY has one -- is where the default marker string matters: a marker that does not
    # match is silent, the section is simply created a second time somewhere else.
    print("fold into an existing hub section")
    mem2 = os.path.join(tmp, "projects", "marked", "memory")
    os.makedirs(mem2)
    io.open(os.path.join(mem2, "MEMORY.md"), "w", encoding="utf-8").write(
        "# Memory Index\n\n## Live\n- [D](d.md) — hook d\n- [E](e.md) — hook e\n"
        "- [F](f.md) — hook f\n\n## 🗂 Hubs\n\n## Tail\n- [Z](z.md) — hook z\n")
    for n in "defz":
        io.open(os.path.join(mem2, n + ".md"), "w", encoding="utf-8").write("body\n")
    mp2 = os.path.join(tmp, "map2.json")
    io.open(mp2, "w", encoding="utf-8").write(json.dumps(
        {"hubs": {"hub-second.md": {"title": "Second", "hook": "three more", "slugs": ["d", "e", "f"]}}}))
    rc, out = run([PY, os.path.join(s, "memory_fold.py"), "--index", os.path.join(mem2, "MEMORY.md"),
                   "--map", mp2], env=env)
    idx2 = io.open(os.path.join(mem2, "MEMORY.md"), encoding="utf-8").read().splitlines()
    at = [i for i, l in enumerate(idx2) if l.strip() == "## 🗂 Hubs"]
    check("default hub marker is matched, so the hub line lands under the existing section",
          len(at) == 1 and idx2[at[0] + 1].startswith("- [Second](hub-second.md)"), "\n".join(idx2))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("guard: every red condition fires, and only when real")
tmp = tempfile.mkdtemp(prefix="cmt2-")
try:
    s = fixture(tmp)
    env = {"MACHINE_KEY": "test-machine"}
    mem = os.path.join(tmp, "projects", "mine", "memory")
    gp = os.path.join(s, "memory_guard.py")

    def guard():
        return run([PY, gp], env=env)

    # the fixture ships one orphan on purpose -- cover it so the baseline is green,
    # then every case below flips exactly one condition and must flip the verdict
    run([PY, os.path.join(s, "memory_orphan_cover.py")], env=env)
    rc, out = guard()
    check("baseline fixture is GREEN", rc == 0, out)

    # over-length entry
    io.open(os.path.join(mem, "MEMORY.md"), "a", encoding="utf-8").write(
        "- [Long](covered.md) — " + "x" * 200 + "\n")
    rc, out = guard()
    check("over-length entry -> RED", rc == 1 and "over" in out, out)
    idx_p = os.path.join(mem, "MEMORY.md")
    t = io.open(idx_p, encoding="utf-8").read()
    io.open(idx_p, "w", encoding="utf-8").write("\n".join(t.splitlines()[:-1]) + "\n")

    # dead pointer
    io.open(idx_p, "a", encoding="utf-8").write("- [Ghost](no-such-note.md) — hook\n")
    rc, out = guard()
    check("dead pointer -> RED and named", rc == 1 and "no-such-note.md" in out, out)
    t = io.open(idx_p, encoding="utf-8").read()
    io.open(idx_p, "w", encoding="utf-8").write(t.replace("- [Ghost](no-such-note.md) — hook\n", ""))

    # duplicate live line
    io.open(idx_p, "a", encoding="utf-8").write(
        "- [Covered again](covered.md) — dup\n")
    rc, out = guard()
    check("duplicate live slug -> RED", rc == 1 and "duplicate" in out, out)
    t = io.open(idx_p, encoding="utf-8").read()
    io.open(idx_p, "w", encoding="utf-8").write(t.replace("- [Covered again](covered.md) — dup\n", ""))

    # sync-conflict copy: two machines fought over the file — must be loud
    cf = os.path.join(mem, "MEMORY.sync-conflict-20260101-000000-AAAAAAA.md")
    io.open(cf, "w", encoding="utf-8").write("conflict copy\n")
    rc, out = guard()
    check("sync-conflict file -> RED", rc == 1 and "sync-conflict" in out, out)
    os.remove(cf)

    # byte budget: a huge index must breach
    io.open(idx_p, "a", encoding="utf-8").write(
        "".join("- [N%d](covered.md) — h\n" % i for i in range(3, 6)))  # dups! restore instead
    io.open(idx_p, "w", encoding="utf-8").write(
        "# Memory Index\n\n- [Covered](covered.md) — hook\n")
    big = os.path.join(mem, "big-note.md")
    io.open(big, "w", encoding="utf-8").write("body\n")
    io.open(idx_p, "a", encoding="utf-8").write(
        "".join("- [B%03d](big-note.md) — %s\n" % (i, "y" * 120) for i in range(180)))
    rc, out = guard()
    check("bytes/lines over hard cap -> RED", rc == 1 and ("bytes" in out or "lines" in out), out)

    # soft mode fires BEFORE the hard cap and exits 2
    io.open(idx_p, "w", encoding="utf-8").write(
        "# Memory Index\n\n- [Covered](covered.md) — hook\n" +
        "".join("- [S%03d](big-note.md) — hook\n" % i for i in range(112)))
    rc, out = run([PY, gp, "--soft"], env=env)
    check("soft redline (>=110 lines) -> exit 2, tidy recommended", rc == 2 and "recommended" in out, out)

    print("orphan cover: hook contract")
    io.open(idx_p, "w", encoding="utf-8").write("# Memory Index\n\n- [Covered](covered.md) — hook\n")
    io.open(os.path.join(mem, "verbose.md"), "w", encoding="utf-8").write(
        "---\nname: verbose\ndescription: " + "word " * 80 + "\n---\nbody\n")
    io.open(os.path.join(mem, "bare.md"), "w", encoding="utf-8").write(
        "no frontmatter here\njust a first line\n")
    rc, out = run([PY, os.path.join(s, "memory_orphan_cover.py")], env=env)
    arch = io.open(os.path.join(mem, "MEMORY-archive.md"), encoding="utf-8").read()
    vline = [l for l in arch.splitlines() if "](verbose.md)" in l]
    bline = [l for l in arch.splitlines() if "](bare.md)" in l]
    check("long description is truncated to the 150-char line contract",
          vline and len(vline[0]) <= 150, vline[0] if vline else "missing")
    check("note without frontmatter falls back to its first body line",
          bline and "no frontmatter here" in bline[0], bline[0] if bline else "missing")
    rc, out = guard()
    check("guard GREEN after covering both", rc == 0, out)

    print("fold: refusal paths (a fold that loses findability writes NOTHING)")
    io.open(idx_p, "a", encoding="utf-8").write(
        "- [G1](g1.md) — hook g1\n- [G2](g2.md) — hook g2\n- [G3](g3.md) — hook g3\n")
    for n in ("g1", "g2", "g3"):
        io.open(os.path.join(mem, n + ".md"), "w", encoding="utf-8").write("body\n")
    before = io.open(idx_p, encoding="utf-8").read()

    mp = os.path.join(tmp, "bad-long.json")
    io.open(mp, "w", encoding="utf-8").write(json.dumps(
        {"hubs": {"hub-long.md": {"title": "Long", "hook": "z" * 200, "slugs": ["g1", "g2", "g3"]}}}))
    rc, out = run([PY, os.path.join(s, "memory_fold.py"), "--index", idx_p, "--map", mp], env=env)
    check("hub line over 150 chars -> refused", rc != 0, out)
    check("refused fold left the index byte-identical",
          io.open(idx_p, encoding="utf-8").read() == before, "index changed on refusal")
    check("refused fold created no hub file", not os.path.exists(os.path.join(mem, "hub-long.md")))

    mp = os.path.join(tmp, "bad-missing.json")
    io.open(mp, "w", encoding="utf-8").write(json.dumps(
        {"hubs": {"hub-miss.md": {"title": "Miss", "hook": "ok", "slugs": ["g1", "ghost-slug"]}}}))
    io.open(idx_p, "a", encoding="utf-8").write("- [Ghost](ghost-slug.md) — will dangle\n")
    rc, out = run([PY, os.path.join(s, "memory_fold.py"), "--index", idx_p, "--map", mp], env=env)
    check("folding a slug whose file is missing -> refused", rc != 0, out)
    check("that refusal also wrote nothing", not os.path.exists(os.path.join(mem, "hub-miss.md")))
    t = io.open(idx_p, encoding="utf-8").read()
    io.open(idx_p, "w", encoding="utf-8").write(t.replace("- [Ghost](ghost-slug.md) — will dangle\n", ""))

    good = os.path.join(tmp, "good.json")
    io.open(good, "w", encoding="utf-8").write(json.dumps(
        {"hubs": {"hub-g.md": {"title": "G", "hook": "three g", "slugs": ["g1", "g2", "g3"]}}}))
    rc, out = run([PY, os.path.join(s, "memory_fold.py"), "--index", idx_p, "--map", good], env=env)
    check("good fold succeeds", rc == 0, out)
    rc, out = run([PY, os.path.join(s, "memory_fold.py"), "--index", idx_p, "--map", good], env=env)
    check("re-running the same fold is a safe no-op (already folded slugs reported, nothing lost)",
          rc == 0 and "no live line" in out, out)
    rc, out = guard()
    check("guard GREEN after fold and re-fold", rc == 0, out)

    print("scope: --exclude output feeds the guard")
    rc, out = run([PY, os.path.join(s, "memory_scope.py"), "--exclude"], env=env)
    check("--exclude lists the worktree project", "proj-worktrees-tmp" in out, out)
    check("--exclude does not list an owned project", "mine" not in out.split(","), out)
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
