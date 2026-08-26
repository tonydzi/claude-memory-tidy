# claude-memory-tidy

**Your always-loaded memory index is rent you pay on every single turn — and when it overflows, it fails silently.**

Claude Code loads `MEMORY.md` into every session. The harness truncates it past a fixed size, and
nothing tells you: no error, no warning. The index just gets shorter at the bottom and your agent
quietly stops knowing things it "remembers". Meanwhile the notes on disk are still there, orphaned —
present but unreachable, which at recall time is the same as deleted.

This is a small, boring, deterministic toolkit that keeps that index healthy. macOS and Linux.

```bash
sh scripts/memory_tidy.sh --dry-run    # what would happen
sh scripts/memory_tidy.sh              # do it
```

Real numbers from the machine it was built on, one run:

| | before | after |
|---|---|---|
| index size | 26 275 B | **8 606 B** |
| index lines | 164 | **52** |
| orphaned notes | 112 | **0** |
| unreachable notes | 112 | **0** |

Nothing was deleted. Every note is still on disk and still reachable.

---

## The idea: hot dispatcher, warm hubs, cold archive

Three tiers, and the only expensive one is the first:

* **`MEMORY.md` — hot dispatcher.** Loaded every turn. Aim for 60–100 lines. One line per pointer,
  `- [Title](file.md) — hook`, ≤150 chars. This is the only file that costs you tokens continuously.
* **`hub-*.md` — warm sub-indexes.** Not auto-loaded. A domain with ≥3 related lines gets folded into
  a hub; the index keeps ONE vocabulary-rich line pointing at it.
* **`MEMORY-archive.md` — cold.** Not auto-loaded, grep-only. Done work, closed lessons, and pointers
  for otherwise-orphaned notes. Coverage here costs zero live budget.

## What the tools do

| tool | job | LLM? |
|---|---|---|
| `memory_guard.py` | **judge**: size, line count, over-length entries, orphans, dead pointers, duplicates, sync-conflicts | no |
| `memory_orphan_cover.py` | give every orphaned note a pointer in the archive, using the note's own `description:` | no |
| `memory_fold.py` | move a domain into a hub **verbatim**, then verify every folded slug is still reachable | no |
| `memory_scope.py` | decide which indexes this machine is allowed to write | no |
| `memory_tidy.sh` | run the above, then call the model **only if the detectors say there is work** | yes, gated |

`memory_fold.py` puts the hub lines under a `## 🗂 Hubs` heading. If your index already keeps them
somewhere else, put that heading verbatim in the mapping file as `"hub_section_marker"` — the match
is exact, and a marker that does not match is silent: you get a second hub section instead of an
error.

The split is deliberate: **mechanical work goes to scripts, judgement goes to the model.** Covering
112 orphans is transcription — a script copies what each note already says about itself. Deciding
what deserves always-loaded budget is judgement. Sending the first job to an LLM burns tokens and
invents hooks that drift from the notes.

## Install

```bash
git clone https://github.com/tonydzi/claude-memory-tidy
cd claude-memory-tidy
cp scripts/*.py scripts/*.sh prompt/*.md ~/.claude/scripts/
cp scripts/memory_scope.example.json ~/.claude/scripts/memory_scope.json

python3 ~/.claude/scripts/memory_scope.py --explain      # declare what this machine owns
python3 tests/test_memory_tidy.py                        # 10 checks, ~1s, no LLM, no network
sh ~/.claude/scripts/memory_tidy.sh --dry-run
```

Optional: install `SKILL.md` as a Claude Code skill so you can just say `/memory-tidy`.

```bash
mkdir -p ~/.claude/skills/memory-tidy && cp SKILL.md ~/.claude/skills/memory-tidy/
```

Schedule it with `launchd` (macOS) or `cron` (Linux); a sample plist is in `examples/`.
Note that **launchd has no anacron catch-up** — a calendar job whose moment passed while the machine
slept is skipped silently, so schedule two slots. The second one is free: on a quiet day the
detectors return "nothing to do" and the model is never called.

## Five failure modes this was built around

Each of these cost a real debugging session. They are the reason the code looks the way it does.

**1. Two writers on one file.** `~/.claude/projects/` mixes indexes this machine owns with indexes
synced byte-identical from another machine. A tool that globs `projects/*/memory/MEMORY.md` and
writes to everything it finds will produce sync-conflicts and lose somebody's memory. Ownership is
**declared** in `memory_scope.json`, never inferred. An undeclared machine exits 3 loudly rather than
tidying nothing — a node that silently does nothing looks exactly like a healthy one.

**2. An alarm that can never be cleared.** A shared pin-list named memories that existed on only one
machine. Everywhere else the "a pinned rule fell out of the index!" tripwire fired forever, and
"restoring" the pointer would have created a *dead* pointer — red for a new reason. A watchdog that
is always red teaches everyone to ignore red. A pin now applies to an index only if the note is
actually next to it.

**3. Counting generated files as memories.** The detector writes a hints file next to the index;
the guard counted it as an orphan and demanded a pointer to a file that gets overwritten on the next
run. An eternal chore nobody can close is a bug in the checker, not a task.

**4. Summary-grounding when folding.** The documented way folding goes wrong: a model rewrites the
hook "while it's in there", and the detail that made the pointer findable evaporates. So folding
moves bytes — `memory_fold.py` never paraphrases, and it refuses to write at all if any folded slug
would lose reachability.

**5. A logged-out CLI that exits zero.** Headless `claude -p` on a logged-out machine printed an
error and exited **0**. Routines stamped green heartbeats and produced nothing. Check `claude auth
status` before trusting any headless run, and make your wrapper turn that into a non-zero code.

## Design rules

* **Detectors before the model.** Two cheap deterministic checks gate the expensive call, so a quiet
  day costs ~0 tokens.
* **The tool never grades its own homework.** After the model edits, the guard runs again and must
  print GREEN. The model's own summary is not evidence.
* **Nothing is deleted, ever.** The only destructive-looking operation is moving a pointer line
  between files. Notes stay on disk.
* **Back up outside the synced tree.** A `.bak` next to the index rides your sync and gets committed;
  backups go to a local-only directory.
* **When unsure whether something is still live, keep it live.** Over-pruning costs more than
  under-pruning.

## Not included

No telemetry, no network calls, no dependencies beyond the Python standard library. The tidy step
shells out to whatever `claude` CLI you already have; everything else runs offline.

## License

MIT — see [LICENSE](LICENSE).

<!-- CONTACT-FOOTER -->
## About & contact

Built and battle-tested at **Palo Alto AI Research Lab** — a fleet of Claude Code machines
running 24/7 as a second brain and synthetic cofounder. The five failure modes above are
incidents that hit that fleet first; none was invented for the repo.

Hit a sixth failure mode, or think one of the budgets is set wrong? Say so — a reproducible
case from someone else's index is the most useful thing anyone can send us.

- 👤 Author: **Anton Dziatkovskii** — Telegram [@tonydzi](https://t.me/tonydzi) · WhatsApp [+1 341 222 9178](https://wa.me/13412229178) · X [@Tony_Stef_](https://x.com/Tony_Stef_)
- 📣 Channels: [@ClawRus](https://t.me/ClawRus) (RU) · [@ClawEng](https://t.me/ClawEng) (EN)
- 🌐 [palo-alto.ai](https://palo-alto.ai) · [Palo Alto AI Research Lab](https://github.com/tonydzi)
- 🧪 **Engineers: want to test-drive this setup?** Message me — I hand out free starter seeds to engineers who test and report back.

---

<!--ecosystem-map:start-->

## 🧩 One piece of a working system

This repository is one piece lifted out of a live operation: one non-technical founder, an AI
cofounder, and a fleet of machines that reach consensus with each other and wake the human only
for money or the irreversible. It was extracted after it survived production, not written as a
demo — and it runs on its own: nothing here phones home to the rest.

**See how the whole thing fits together → [SYSTEM.md](https://github.com/tonydzi/tonydzi/blob/main/SYSTEM.md)**

<!--ecosystem-map:end-->

## AI contributors

This project is built by a human + AI team, and the git log says so: Claude writes most of
the code, Codex and Grok review it, Gemini feeds the research. Each is credited on a commit
**only if its output changed that commit's content** — no decorative credits. Lab-wide
policy, one source for every repo: [AI-CONTRIBUTORS.md](https://github.com/tonydzi/.github/blob/main/AI-CONTRIBUTORS.md).
