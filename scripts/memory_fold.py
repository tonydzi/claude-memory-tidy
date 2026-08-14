#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory_fold.py -- fold a domain of live index lines into a warm sub-index (hub), verbatim.

THE ARCHITECTURE (decision-memory-index-hot-dispatcher-2026-07-04): MEMORY.md is a HOT
DISPATCHER loaded into every session, so its budget is rent paid on every single turn. A domain
with >=3 related live lines belongs in a `hub-*.md` warm sub-index: ONE vocabulary-rich line
stays in the index, the spokes move into the hub. memory_guard.py counts a pointer inside a hub
as coverage, so nothing becomes an orphan and nothing is deleted.

WHY MECHANICAL: the documented failure mode of folding is SUMMARY-GROUNDING -- an LLM rewrites
the spoke hook "while it's in there", and the detail that made the pointer findable evaporates.
This script MOVES BYTES: each spoke line lands in the hub exactly as it was in the index. The
judgement (which slug belongs to which domain) is the model's job and lives in the mapping file;
the transcription is the script's job, and a script does not paraphrase.

VERIFY built in: after writing, every folded slug must be (a) still a file on disk, (b) present
verbatim in its hub, (c) that hub must have a line in the index. Any miss -> nothing is written
and the run exits 1 (a fold that loses findability is a FAILED fold).

Usage:  python3 memory_fold.py --index <MEMORY.md> --map <mapping.json> [--dry-run]
"""
import io, json, os, re, sys

SLUG_RE = re.compile(r"\]\(([a-z0-9._-]+\.md)\)")


def read(p):
    with io.open(p, encoding="utf-8-sig") as f:
        return f.read()


def write(p, txt):
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)


def main():
    a = sys.argv
    if "--index" not in a or "--map" not in a:
        print(__doc__)
        return 1
    index_p = a[a.index("--index") + 1]
    map_p = a[a.index("--map") + 1]
    dry = "--dry-run" in a
    mem_dir = os.path.dirname(os.path.abspath(index_p))
    mapping = json.load(open(map_p, encoding="utf-8"))

    slug_to_hub = {}
    for hub, spec in mapping["hubs"].items():
        for s in spec["slugs"]:
            slug_to_hub[s if s.endswith(".md") else s + ".md"] = hub

    lines = read(index_p).splitlines()
    kept, moved = [], {h: [] for h in mapping["hubs"]}
    for l in lines:
        m = SLUG_RE.search(l)
        if m and l.lstrip().startswith("-") and m.group(1) in slug_to_hub:
            moved[slug_to_hub[m.group(1)]].append(l)   # VERBATIM, byte for byte
        else:
            kept.append(l)

    total = sum(len(v) for v in moved.values())
    print("fold: %d line(s) into %d hub(s)" % (total, sum(1 for v in moved.values() if v)))
    for h, v in moved.items():
        print("  %-42s %d" % (h, len(v)))
    unmatched = [s for s in slug_to_hub if s not in
                 {SLUG_RE.search(l).group(1) for v in moved.values() for l in v if SLUG_RE.search(l)}]
    if unmatched:
        print("  note: %d mapped slug(s) had no live line (already folded/archived): %s"
              % (len(unmatched), ", ".join(sorted(unmatched)[:6])))

    # --- build hub bodies ---
    hub_texts = {}
    for hub, spec in mapping["hubs"].items():
        if not moved[hub]:
            continue
        p = os.path.join(mem_dir, hub)
        prior = read(p) if os.path.exists(p) else ""
        head = prior if prior else (
            "# %s\n\n> Warm sub-index (hub). NOT auto-loaded — the always-loaded MEMORY.md keeps ONE\n"
            "> line pointing here. Hooks below are VERBATIM from the index; detail lives in each note.\n"
            % spec["title"])
        hub_texts[hub] = head.rstrip("\n") + "\n\n" + "\n".join(moved[hub]) + "\n"

    # --- index: keep everything else, add one line per hub ---
    hub_lines = ["- [%s](%s) — %s" % (mapping["hubs"][h]["title"], h, mapping["hubs"][h]["hook"])
                 for h in mapping["hubs"] if moved[h]]
    over = [l for l in hub_lines if len(l) > 150]
    if over:
        print("RED: hub line over 150 chars: %s" % over[0])
        return 1
    # Where the hub lines go in the index. If your index already has a section for them, put its
    # exact heading in the mapping as "hub_section_marker"; the match is on the stripped line, so
    # it must be byte-identical. No match -> the section is created below the index header.
    marker = mapping.get("hub_section_marker", "## 🗂 Hubs")
    out = []
    placed = False
    for l in kept:
        out.append(l)
        if l.strip() == marker and not placed:
            out += hub_lines
            placed = True
    if not placed:
        # insert the hub section right after the index header block
        idx = 3 if len(out) > 3 else len(out)
        out = out[:idx] + ["", marker] + hub_lines + out[idx:]

    new_index = "\n".join(out).rstrip("\n") + "\n"

    # --- VERIFY before writing anything ---
    problems = []
    for hub, body in hub_texts.items():
        for l in moved[hub]:
            if l not in body:
                problems.append("spoke not verbatim in %s: %s" % (hub, l[:60]))
        if ("](%s)" % hub) not in new_index:
            problems.append("hub %s has no line in the index" % hub)
        for l in moved[hub]:
            m = SLUG_RE.search(l)
            if m and not os.path.exists(os.path.join(mem_dir, m.group(1))):
                problems.append("folded slug has no file: %s" % m.group(1))
    if problems:
        print("RED: fold would lose findability -- nothing written:")
        for p in problems[:8]:
            print("   " + p)
        return 1

    print("index: %d -> %d lines" % (len(lines), len(out)))
    if dry:
        print("dry-run: nothing written")
        return 0
    for hub, body in hub_texts.items():
        write(os.path.join(mem_dir, hub), body)
    write(index_p, new_index)
    print("written: %d hub file(s) + index" % len(hub_texts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
