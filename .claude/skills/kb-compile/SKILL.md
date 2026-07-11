---
name: kb-compile
description: Compile un-compiled entries from knowledge_base/raw/ into linked concept/decision articles under knowledge_base/wiki/, maintaining backlinks and the wiki index. Use when the user runs /kb-compile or /kb-compile <concept name>.
---

# kb-compile

Read `knowledge_base/README.md` first if this is your first time touching `knowledge_base/` this session —
it has the templates and rules this skill relies on.

**Scope**: this skill only ever writes under `knowledge_base/wiki/`. It may read the rest of the repo but
must never modify anything outside `knowledge_base/`.

## Steps

1. Read `knowledge_base/raw/_index.md` and every `meta.md` under `knowledge_base/raw/`. Read
   `knowledge_base/wiki/_index.md`, `knowledge_base/wiki/QUESTIONS.md`, and every existing article under
   `wiki/concepts/` and `wiki/decisions/`. Read `knowledge_base/writing-rules.md`.
2. Identify which raw entries are **not yet cited** by any wiki article's `Sources:` line. "Cited" means the
   entry's exact `raw/<date>-<slug>/meta.md` path string appears in some article's `Sources:` line — check
   the literal path, not just whether the topic sounds related. This is deliberately exact-match: `kb-ingest`
   now reuses an already-cited `<date>-<slug>` path when a source is re-ingested (e.g. after a fresh clone,
   where `raw/` doesn't exist locally per `.gitignore` — see `knowledge_base/README.md`'s "Working across
   devices" section), specifically so that a re-ingested entry lands back on an already-cited path and shows
   up here as **already cited** — meaning **skip it**, don't touch the article, don't create a near-duplicate
   one. If the user gave a specific concept name, restrict work to raw entries relevant to that concept;
   otherwise process all uncited entries. If the user names a concept whose raw source is already cited at
   its current path, say so and stop for that concept — don't rewrite an article just because it was invoked
   directly, unless the raw content genuinely changed since the citation (compare against what the article
   already claims; if the source is unchanged, there's nothing to update).
3. For each uncited raw entry, decide:
   - **belongs to an existing article** → append/update a section in that article, and add the raw entry to
     its `Sources:` line;
   - **needs a new article** → create it under `wiki/concepts/` or `wiki/decisions/` using the fixed template
     from `knowledge_base/README.md` (title, `Sources:` line, `Status:`/`Last updated:` lines, body,
     `See also`). Set `Status` per the guidance in `knowledge_base/README.md`'s template section — default
     new single-source articles to `emerging` unless the source is unambiguous primary material (e.g.
     verbatim source code).
4. When creating or updating an article, populate/update `See also` by scanning other wiki articles for
   topical overlap (shared modules, shared raw sources, related concepts). Apply the
   **backlink-reciprocity rule**: if article A now links to B, add a link back from B to A. Bump the
   article's `Last updated` date whenever its body changes (not for backlink-only edits).
5. Never fabricate — every claim must trace to a raw entry or to the actual repo source. If unsure, mark
   `<!-- TODO: verify -->` inline for a small aside, or log the gap in `wiki/QUESTIONS.md` (don't duplicate
   an existing entry there) rather than guessing.
6. Apply `writing-rules.md` to any prose you write or rewrite: American spelling, the banned-words list, and
   the em-dash-bullet-pattern fix. Doesn't apply to `Sources:`/`Status:`/`See also` lines or code excerpts.
7. Keep articles roughly 30-80 lines. If an article is growing past that, split the overflow into a new,
   more specific article rather than letting it become a dumping ground.
8. Rewrite `knowledge_base/wiki/_index.md` in full: grouped by `concepts/` and `decisions/`, one line per
   article with its one-line summary and relative link.
9. If this pass resolved anything logged in `wiki/QUESTIONS.md` (re-sourced a claim, promoted a `Status`,
   ingested previously-missing material), remove that entry.
10. Print a short summary of what was created/updated.
