---
name: kb-ingest
description: Ingest a source (repo file, git history range, or pasted text) into knowledge_base/raw/ as a new dated entry, and update the raw index. Use when the user runs /kb-ingest <path-or-description>.
---

# kb-ingest

Read `knowledge_base/README.md` first if this is your first time touching `knowledge_base/` this session —
it has the templates and rules this skill relies on.

**Scope**: this skill only ever writes under `knowledge_base/raw/`. It may read the rest of the repo
(source files, `git log`) but must never modify `main.py`, `conversion.py`, `media.py`, `progress.py`,
`tracks.py`, or anything else outside `knowledge_base/`. It never touches `knowledge_base/wiki/` — ingest and
compile are decoupled steps.

## Steps

1. Resolve what "source" means from the argument the user gave:
   - a repo file path (e.g. `plans/main-refactoring-plan.md`, `tracks.py`) — read the file directly;
   - a git-history request (e.g. "git log for tracks.py", "recent commits") — run `git log` and read the
     relevant diffs, then write a **curated summary**, not a raw log dump;
   - free text pasted or described by the user — use it as-is.
2. Derive a slug **deterministically from the source's identity**, not freely each time: for a repo file,
   kebab-case its path with a `module-` prefix for the top-level CLI modules (`media.py` → `module-media`,
   `tracks.py` → `module-tracks`, etc.) and no prefix for other files (`README.md` → `readme`); for a
   git-history request, base it on the commit range or topic (e.g. `git-history-highlights`); for pasted
   text, a short descriptive slug. The point: ingesting the *same* source later — including on a different
   device — must reproduce the *same* slug, because step 3 depends on it.
3. **Check for an existing raw path before minting a new one.** Grep `knowledge_base/wiki/**/*.md` for a
   `Sources:` reference matching `raw/<any-date>-<slug>/meta.md` with the slug from step 2 (date wildcarded —
   ignore what today's date is for this search).
   - **Match found**: an article already cites this exact source. Reuse that literal `<date>-<slug>` as the
     folder name — `knowledge_base/raw/<that-same-date>-<slug>/` — regardless of today's date. This is what
     makes re-ingesting on a new device (where `raw/` doesn't exist locally, per `.gitignore`) restore the
     entry at the path the wiki article already expects, instead of creating a duplicate under today's date
     that `kb-compile` would treat as new and uncited. If the folder already exists locally (same-device
     refresh, e.g. the source changed since last ingest), overwrite its contents in place — still one entry,
     never a second dated copy of the same source.
   - **No match found**: genuinely new source. Create `knowledge_base/raw/<YYYY-MM-DD>-<slug>/` using today's
     date as usual.
4. Write `source.md` inside it:
   - for a repo file, embed its content. If it's a Python module, wrap it in a fenced ```python block and
     add a note: "Verbatim copy as of commit `<sha>` — may drift; re-run `/kb-ingest` to refresh." (Get the
     sha via `git log -1 --format=%h -- <path>`.)
   - for git history, write the curated summary described above.
   - for pasted text, embed it directly.
5. Write `meta.md` using the fixed template from `knowledge_base/README.md` (Source / Ingested date /
   one-line summary / Summary / Key facts). `Ingested:` always reflects *today's* date, even when step 3
   reused an older folder name — the folder name is a stable identity, not a timestamp, once an article
   cites it.
6. Rewrite `knowledge_base/raw/_index.md` in full: one bullet per raw entry, sorted by date, each linking to
   its `meta.md` with its one-line summary. Don't otherwise change existing rows' content.
7. Print a short confirmation. If step 3 found a match, say so explicitly — e.g. "Restored
   `raw/2026-07-11-module-media/`, already cited by `wiki/concepts/media-probing.md` — no `/kb-compile` step
   needed, the article stays as-is unless the source content actually changed." Otherwise, report the new
   directory path and one-line summary, and suggest running `/kb-compile` next.

Do not fabricate content — if a source is ambiguous or you can't find it, ask the user rather than guessing.
