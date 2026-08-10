You are running UNATTENDED to do a QUALITY tidy of the always-loaded memory index MEMORY.md.
Quality matters more than speed: preserve meaning, never lose a real pointer. Work carefully, then report.

<!-- PATHS_BLOCK -->

CAPS (hard budget): <=135 lines, <=20000 bytes, every entry <=150 CHARACTERS.
Format of an entry: `- [Title](file.md) — short one-line hook`.

HOT-DISPATCHER ARCHITECTURE (decision-memory-index-hot-dispatcher-2026-07-04 + DR26-07-04-HUB-01):
- MEMORY.md = hot DISPATCHER, not a second instruction file. Operating zone 60-100 lines / 8-12KB;
  soft-redline 15KB/110 lines. Aim <=100 lines.
- H1 DEMOTION CRITERION: a LIVE line whose rule already has a full SECTION in the global CLAUDE.md
  (trigger + directive + nuances) is a redundant second always-loaded trace -> move to ARCHIVE.
  EXCEPTION (keep live): the line adds retrieval aliases / routing / a high-frequency trigger that the
  CLAUDE.md wording lacks. Pinned slugs are NEVER demoted.
- HUBS: warm sub-indexes `hub-*.md`. A spoke listed inside a hub file is COVERED — do not re-add spokes
  as live lines. Promoting a topic of a hub's domain -> prefer adding it as a spoke line INSIDE the hub
  file, not as a live line (unless truly hot for current work).
- ⭐ H2 IS A MANDATE, NOT A SUGGESTION. A domain with >=3 related live lines and no hub -> BUILD the hub
  and fold them, THIS RUN, unattended. Do NOT ask permission and do NOT "note it for the owner": the
  architecture was ALREADY approved on 2026-07-04 — applying it is execution, not a new decision.
  WHY THIS LINE EXISTS: the old wording said "consider clustering" while the conservatism rule said
  "unsure about a large structural change -> do the safe minimum and flag it", so conservatism
  always won. In practice this tidy asked for approval four runs in a row, never got it, and the index
  decayed to 122 lines / 20.2KB with 38 bytes of headroom. Requiring approval to APPLY an approved
  architecture is the bug.
- HOW to fold safely (deterministic and reversible — this is what makes it unattended-safe): spoke hooks
  move VERBATIM into the hub file (never a blurred summary — summary-grounding is a documented failure
  mode); the index line becomes ONE hub line <=150 chars, vocabulary-rich; nothing is deleted (topic
  files stay; the guard counts a pointer inside a `hub-*.md` as coverage).
- KEEP LIVE even if the domain has a hub: STANDING rules/preferences that fire OUTSIDE their own domain.
  Test: "could this rule need to fire in a session that never opens the hub?" -> yes = live.

CAPTAIN'S TABLE (focus-aware, bidirectional):
The index is the always-loaded "captain's table" — it should hold the pointers relevant to what we are
working on NOW, not merely shrink over time. A deterministic detector (memory_focus.py) already ran and
wrote HINTS (path in the PATHS block). READ THE HINTS FIRST. It lists (a) ⬆️ PROMOTE candidates —
archived topics that are HOT again — and (b) 🔴 PINNED-BUT-MISSING — standing rules that fell out.
- 🔴 PINNED-BUT-MISSING -> RESTORE that pointer into MEMORY.md immediately. A standing rule must never be
  absent. Non-negotiable. If the topic file itself is missing, say so LOUDLY in the report.
- ⬆️ PROMOTE candidate -> CONFIRM it is genuinely relevant to current work (do NOT promote a clearly-DONE
  one-off just because a word matched — the detector proposes, you judge). If relevant, MOVE its pointer
  line from MEMORY-archive.md back into MEMORY.md.
- HYSTERESIS: the detector already excluded anything moved within the last 3 days — don't re-move those.
- PINS: never demote a slug listed in the pin file, whatever its activity.
- If a promote would push the index over caps, demote a clearly-DONE/superseded LIVE pointer to make room
  (never a pinned one).

PROCEDURE (do in order):
1. A backup already exists (the wrapper copied it — path in the PATHS block). Do NOT delete any topic
   file. Nothing here is destructive except moving a POINTER line between MEMORY.md and MEMORY-archive.md.
   FIRST read the HINTS file and handle pinned-but-missing + confirmed promote candidates as part of this
   tidy.
2. Read MEMORY.md. For EACH entry over 150 chars: rewrite the hook shorter, KEEPING the disambiguating
   essence (what is in the file; a key id/path if vital). Detail stays in the topic file — the index is a
   pointer. Do not flatten two different entries into one vague line.
3. Decide what belongs in the LIVE index vs ARCHIVE:
   - LIVE (keep): STANDING rules / preferences / working style, the constitution and key protocols, and
     LIVE projects/tools/routines actively in use.
   - ARCHIVE (move the pointer to MEMORY-archive.md): DONE one-off imports (data already in the vault),
     finished projects, one-off lessons/fixes already encoded elsewhere, superseded/declined tools.
4. ⚠️ BEFORE archiving any entry, grep its topic file for OPEN TAILS:
   `pending|BLOCKED|TODO|deferred|not yet|next =|Phase B|⚠`. A genuine undone ACTION (not just a
   gotcha/lesson) -> put it on the hanging-tasks board (path in the PATHS block; group by owner:
   🔴 owner / 🟡 agent / ⏳ external) so it is NOT buried. Only then move the pointer to the archive.
5. ORPHANS (a topic file on disk with no pointer anywhere) are silent memory loss: the file exists, but
   nothing will ever surface it. For each orphan decide — genuinely useful now -> add a live line;
   historical -> add its pointer to MEMORY-archive.md. Never delete the file. The guard counts a pointer
   in EITHER file as coverage, so an orphan is always fixable without spending live-index budget.
6. Keep the LIVE index in the hot-dispatcher zone (aim <=100 lines / <=12KB). Do not over-prune — when
   unsure whether something is still live, KEEP it live.
7. ⭐ H2 DRIFT CHECK (do this EVERY run — it is what keeps the zone): scan the LIVE index for any domain
   with >=3 related lines and no hub. Found one -> BUILD the hub and fold it NOW (see the H2 mandate).
8. VERIFY — all gates must pass before you may say GREEN:
   a) guard: run the guard command from the PATHS block. It MUST print GREEN for every OWNED index
      (0 over-length, 0 orphans, 0 dead pointers, 0 dups, within caps). Do not finish RED.
   b) pin-tripwire: run the focus command from the PATHS block; it must report 0 missing pins.
   c) retrieval-regression (only if you folded anything): every folded slug must still be reachable —
      file on disk + listed in a hub file + that hub has a line in the index + its hook is verbatim.
      A fold that loses findability is a FAILED fold: revert it.
9. Be conservative ONLY about NEW POLICY, never about applying decided policy. Escalate to the owner ONLY for:
   changing the architecture/caps/pin rules, or a judgment call the rules genuinely do not cover.
   Applying H1/H2 within the decided architecture = just do it and report. "Do the safe minimum and note
   it for the owner" is NOT an option for a domain that meets the H2 threshold.

SCOPE DISCIPLINE (non-negotiable): tidy ONLY the indexes listed as OWNED in the PATHS block. Other
`projects/*/memory/MEMORY.md` files on this disk are byte-identical copies SYNCED from another node whose
tidy owns them — writing there creates a sync-conflict and loses somebody's memory. If an owned index
does not exist, say so; do not go find another one to tidy instead.

OUTPUT: print a concise summary — lines/bytes before→after per index, what you trimmed, what you
archived, which pins you restored, which orphans you covered, what undone tails you put on the board,
any hub you built, and the final guard line. The wrapper forwards this to the owner's notification channel. If you could
NOT reach GREEN, or you hit an error, say so LOUDLY at the very top with the word FAILED.
