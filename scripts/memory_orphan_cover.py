#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory_orphan_cover.py -- give every ORPHANED memory note a pointer, deterministically.

AN ORPHAN IS SILENT MEMORY LOSS: the note exists on disk, but nothing in MEMORY.md,
MEMORY-archive.md or any hub-*.md points at it, so no session will ever surface it. It is
not lost data -- it is unreachable data, which is the same thing at recall time.

WHY A SCRIPT AND NOT THE MODEL: covering 112 orphans is mechanical (title + one-line hook,
both already sitting in each note's frontmatter). Spending an LLM on it burns tokens and
invents hooks that drift from the note; a script copies what the note itself says. The model's
judgement is needed for the LIVE index (what deserves always-loaded budget) -- not here.
Pointers land in MEMORY-archive.md, which is NOT auto-loaded, so coverage costs 0 live budget.

Line format matches the index contract: `- [Title](file.md) — hook`, whole line <= 150 chars.

Usage:  python3 memory_orphan_cover.py [--dry-run] [--index <MEMORY.md>]
        (no --index = every index this node owns, per memory_scope.py)
Exit:   0 covered / 0 nothing to do, 1 on error.
"""
import io, os, re, sys, subprocess, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_LINE = 150
GENERATED = {"memory-focus-hints.md"}


def owned_indexes():
    out = subprocess.run([sys.executable, os.path.join(HERE, "memory_scope.py"), "--list"],
                         capture_output=True, text=True)
    return [l for l in out.stdout.splitlines() if l.strip()]


def read(p):
    with io.open(p, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def frontmatter(txt):
    """-> (name, description). Both may be ''. Tolerant: notes are hand-edited."""
    if not txt.startswith("---"):
        return "", ""
    end = txt.find("\n---", 3)
    if end < 0:
        return "", ""
    head = txt[3:end]
    def field(key):
        m = re.search(r"^%s:\s*(.+?)\s*$" % key, head, re.M)
        if not m:
            return ""
        v = m.group(1).strip()
        if v[:1] in "\"'" and v[-1:] == v[:1]:
            v = v[1:-1]
        return v
    return field("name"), field("description")


def first_body_line(txt):
    body = txt.split("\n---", 1)[-1] if txt.startswith("---") else txt
    for l in body.splitlines():
        l = l.strip().lstrip("#").strip()
        if l and not l.startswith("---"):
            return l
    return ""


def hook_for(path):
    txt = read(path)
    name, desc = frontmatter(txt)
    title = name or os.path.basename(path)[:-3]
    hook = desc or first_body_line(txt)
    hook = re.sub(r"\s+", " ", hook).strip()
    # strip markdown that would break the one-line pointer contract
    hook = hook.replace("[[", "").replace("]]", "").replace("`", "")
    return title, hook


def pointer_line(path):
    fname = os.path.basename(path)
    title, hook = hook_for(path)
    prefix = "- [%s](%s) — " % (title, fname)
    room = MAX_LINE - len(prefix)
    if room < 12:                      # pathological slug: keep the pointer, drop the hook
        return ("- [%s](%s)" % (title, fname))[:MAX_LINE]
    if len(hook) > room:
        hook = hook[:room - 1].rstrip() + "…"
    return prefix + hook


def orphans_of(index_path):
    mem_dir = os.path.dirname(index_path)
    idx = read(index_path)
    arch_p = os.path.join(mem_dir, "MEMORY-archive.md")
    arch = read(arch_p) if os.path.exists(arch_p) else ""
    hubs = ""
    for f in os.listdir(mem_dir):
        if f.startswith("hub-") and f.endswith(".md") and ".sync-conflict-" not in f:
            hubs += read(os.path.join(mem_dir, f))
    return sorted(f for f in os.listdir(mem_dir)
                  if f.endswith(".md") and not f.startswith("MEMORY")
                  and ".sync-conflict-" not in f and f not in GENERATED
                  and f not in idx and f not in arch and f not in hubs)


def cover(index_path, dry):
    mem_dir = os.path.dirname(index_path)
    orph = orphans_of(index_path)
    proj = os.path.basename(os.path.dirname(mem_dir))
    if not orph:
        print("[%s] 0 orphans -- nothing to cover." % proj)
        return 0
    arch_p = os.path.join(mem_dir, "MEMORY-archive.md")
    lines = [pointer_line(os.path.join(mem_dir, f)) for f in orph]
    print("[%s] %d orphan(s) -> pointers in MEMORY-archive.md" % (proj, len(orph)))
    for l in lines[:5]:
        print("    " + l)
    if len(lines) > 5:
        print("    ... and %d more" % (len(lines) - 5))
    if dry:
        return len(orph)           # report the real count; a dry-run that says 0 is a lying preview
    today = datetime.date.today().isoformat()
    # The heading says what happened, so a human reading the archive months later does not
    # mistake coverage for archiving: nothing moved and nothing was deleted, the notes were
    # merely made findable.
    block = ("\n## Covered by a pointer %s (orphans: the file was on disk with nothing "
             "pointing at it — nothing deleted, it just became findable)\n" % today) \
        + "\n".join(lines) + "\n"
    if not os.path.exists(arch_p):
        block = ("# Memory Archive (DONE / superseded — moved out of the live index, "
                 "never deleted)\n" + block)
    with io.open(arch_p, "a", encoding="utf-8", newline="\n") as f:
        f.write(block)
    return len(orph)


def main():
    dry = "--dry-run" in sys.argv
    if "--index" in sys.argv:
        targets = [sys.argv[sys.argv.index("--index") + 1]]
    else:
        targets = owned_indexes()
    if not targets:
        print("RED: no owned index found (memory_scope.py)", file=sys.stderr)
        return 1
    total = 0
    for t in targets:
        total += cover(t, dry)
    print(("dry-run: would cover %d" if dry else "covered %d") % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
