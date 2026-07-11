# knowledge_base

A self-documenting knowledge base for this repo (`python-video-converter`), built the way Andrej Karpathy
described his personal LLM knowledge bases: raw source material goes into `raw/`, an LLM (here, Claude Code,
driven interactively via the `/kb-*` skills) incrementally "compiles" it into a linked `.md` wiki, and the
same agent answers questions against the wiki and periodically lints it for gaps.

This file is the constitution: the rules and templates every `/kb-*` skill relies on. Read this first if
you're a skill (or a human) about to touch anything under `knowledge_base/`.

## Scope

- This knowledge base documents **this repo only** — its modules, its design decisions, its history. It is
  not a general-purpose research tool for arbitrary topics.
- Skills only ever **write** under `knowledge_base/`. They may **read** the rest of the repo (source files,
  `git log`) but must never modify `main.py`, `conversion.py`, `media.py`, `progress.py`, `tracks.py`, or any
  other file outside `knowledge_base/`.
- No Obsidian, no Marp, no graph-view/wikilink plugins. Everything is plain markdown, viewable in any editor.
  `[[relative/path]]` links are a plain-text convention only — literal text, not a tooling dependency.

## Directory structure

```
knowledge_base/
  README.md          # this file
  writing-rules.md   # prose style rules for wiki/outputs; see "Writing standards" below
  raw/                # UNTRACKED (gitignored) — personal ingest scratch, local only
    _index.md
    <YYYY-MM-DD>-<slug>/
      source.md       # the ingested content (code as fenced ```python blocks, noting the commit sha)
      meta.md         # fixed template, see below
  wiki/               # TRACKED — the compiled, shareable value
    _index.md
    QUESTIONS.md      # open threads, sourcing gaps, held tensions, future-article candidates
    concepts/*.md
    decisions/*.md
  outputs/            # TRACKED — filed answers and lint reports
    _index.md
    qna/<YYYY-MM-DD>-<slug>.md
    lint-reports/<YYYY-MM-DD>-lint-report.md
  tools/
    search.py         # naive keyword search CLI over knowledge_base/**/*.md
```

`raw/` is gitignored on purpose: it's personal ingest scratch, not shared truth. Anyone who clones this repo
gets the compiled `wiki/` and `outputs/` but not `raw/`. This means wiki articles' `Sources:` links to
`raw/` will only resolve for whoever ran the ingest locally — that's expected. **A wiki article's body must
stand on its own** for a reader without local `raw/`; treat `Sources:` as provenance for the person
maintaining the KB, not as a required reference for reading the article.

## Working across devices

Cloning this repo on a new device (or after deleting local `raw/` scratch) gives you `wiki/` and `outputs/`
as-is, but an empty `raw/`. Every `Sources:` link in the wiki will dangle until you re-ingest — that part is
expected (see above). What must **not** happen is `/kb-ingest`-ing the same source again and ending up with
a second, differently-dated raw entry that `/kb-compile` then treats as brand new, producing a near-duplicate
article next to the one that already covers that source.

This is prevented structurally, not by convention alone: `kb-ingest` derives a **deterministic slug** from a
source's identity (the same repo file always kebab-cases to the same slug — see that skill's own docs), and
before minting a new dated folder it greps the wiki for an existing `Sources:` reference to
`raw/<any-date>-<slug>/meta.md` with a matching slug. If one exists, it **reuses that exact date+slug**
regardless of today's date, so the restored entry lands precisely where the wiki already expects it. From
`kb-compile`'s side, "already cited" is an exact path match — a restored entry at its original path is
indistinguishable from one that was never deleted, so the existing article is left alone. The same mechanism
also fixes a same-device footgun: re-ingesting a source you already have in `raw/` refreshes that one entry
in place instead of piling up a second dated copy of it.

This does **not** cover content drift — if a source file changed since it was last ingested, re-ingesting it
lands at the same path with updated content, but nothing currently re-checks whether the wiki article's
claims still match. That gap is logged in `wiki/QUESTIONS.md` rather than silently assumed away.

## Templates

### `raw/<date>-<slug>/meta.md`

```markdown
# <Title>

- Source: <original repo path, or "git log" with a commit range, or a free-text description>
- Ingested: <YYYY-MM-DD>
- One-line summary: <...>

## Summary
<3-8 sentence summary>

## Key facts / quotes
- ...
```

### `wiki/concepts/*.md` and `wiki/decisions/*.md`

```markdown
# <Concept Name>

> Sources: [[../../raw/<date>-<slug>/meta.md]], [[../../raw/<date>-<slug-2>/meta.md]]
> Status: established | emerging | speculative
> Last updated: <YYYY-MM-DD>

<article body, ~30-80 lines>

## See also
- [[<other-concept>]]
```

**Status** is a trust signal, not decoration — set it deliberately:
- **established** — grounded directly in primary sources (actual repo code, a design doc's own stated
  rationale) with no unsourced inference load-bearing in the article.
- **emerging** — worth tracking, but the sourcing is thinner than `established` requires: a single
  non-verbatim source, or a source that's itself a curated summary rather than primary material.
- **speculative** — the article leans on the librarian's own unconfirmed reasoning as a central claim, not
  just an aside.

If an article's *core* claim is unsourced, mark the whole article `speculative`. If only a *specific aside*
within an otherwise well-sourced article is inferred, keep the article's overall status and instead log that
one claim in `wiki/QUESTIONS.md` (see the no-fabrication rule below) — don't downgrade the whole article over
one flagged aside. `Last updated` bumps whenever the article's body changes, not on backlink-only edits.

### `_index.md` (one per directory: `raw/`, `wiki/`, `outputs/`)

A flat list, rewritten in full each time (the corpus is small — tens of files — so full rewrites are simpler
and safer than incremental patching):

```markdown
# <Directory> index

- [<entry name>](<relative link>) — <one-line summary>
```

## Writing standards

Wiki articles and prose-heavy `outputs/` files (e.g. `outputs/qna/*.md`) follow `writing-rules.md` in this
directory — American spelling, a small banned-words list, and the em-dash-bullet-pattern fix (`**Term** —`
→ `**Term:**`). `kb-compile` applies these rules when drafting or updating an article; `kb-lint` audits
existing articles against them and fixes unambiguous violations directly, same as it does for broken
backlinks. Navigation files (`_index.md`, `QUESTIONS.md`, this `README.md`, `raw/**/meta.md`,
`raw/**/source.md`) and verbatim quotes/code excerpts are exempt.

## `wiki/QUESTIONS.md`

Tracks open threads that don't belong in a finished article: sourcing gaps, claims that lean on unconfirmed
inference, held tensions between articles, and future-article candidates that aren't warranted yet. Any
skill that surfaces a gap it isn't fixing immediately — `kb-compile` hitting a claim it can't source,
`kb-lint` finding an article's evidence thinner than its `Status` claims, `kb-ask` noticing the wiki doesn't
fully answer a question — logs it here instead of letting it evaporate at the end of the chat turn. Entries
are removed once resolved, not archived in place; the file tracks what's still open, not a full history (use
`CHANGELOG`-style logs like the lint reports in `outputs/lint-reports/` for that).

## Suggested lint cadence (not yet automated)

There is no scheduled task running `/kb-lint` automatically today — every lint pass so far has been run
on demand, in-session. If this corpus grows enough that staleness becomes a real risk, the natural shape for
automation (not yet implemented) would be:

- **Cadence**: monthly is enough at this repo's pace of change; a delta pass (only articles touched since
  the last lint) most months, with a full pass over every article quarterly.
- **Skip-if-unchanged**: if nothing under `knowledge_base/` changed since the last lint report, write a
  one-line "skipped, no changes" entry instead of a full report — avoids report churn between real changes.
- **How to wire it up**: this repo's tooling includes a `schedule`/cron mechanism for recurring agent runs;
  a scheduled task would invoke `/kb-lint` on that cadence and rely on the existing skip-if-unchanged check
  above rather than needing new logic.
- Given this KB documents a single repo (not a multi-corpus personal research library), the failure mode
  automation would guard against — drift silently accumulating between manual passes — is currently low
  risk. Revisit if `knowledge_base/` starts changing faster than someone remembers to run `/kb-lint`.

## Rules

1. **Index-maintenance rule**: any skill that adds or removes an entry from `raw/`, `wiki/`, or `outputs/`
   must rewrite that directory's `_index.md` in the same turn.
2. **Backlink-reciprocity rule**: if concept article A links to B under "See also", B must link back to A.
   `kb-lint` enforces this.
3. **No fabrication rule**: every claim in a wiki article must trace to something in `raw/` or to the actual
   repo source. If a skill is unsure, it marks `<!-- TODO: verify -->` inline, or logs the gap in
   `wiki/QUESTIONS.md`, rather than guessing.
4. **Ingest/compile decoupling rule**: `kb-ingest` only ever touches `raw/`. Compiling into `wiki/` is always
   a separate, deliberate step (`kb-compile`), so raw material can be staged without immediately forcing a
   wiki rewrite.
5. **`search.py` is a deliberate exception to this repo's no-argparse convention.** The rest of this repo's
   CLI (`main.py`) is a single-shot interactive tool (prompts, defaults, confirmations), which is why it
   avoids argparse. `knowledge_base/tools/search.py` is structurally different: it's a query tool invoked
   headlessly — by a human running one command, and by Claude shelling out to it mid-skill — where an
   `input()`-prompt loop would be actively wrong. Do not "fix" this back to interactive prompts.
6. **Status-integrity rule**: `kb-lint` checks that each article's `Status` still matches its sourcing —
   promote `emerging` → `established` once a second independent, sufficiently primary source exists; flag
   (don't silently promote) anything that looks miscalibrated the other way.
7. **QUESTIONS-mirroring rule**: any gap logged in `wiki/QUESTIONS.md` gets removed only when the thing it
   describes is actually resolved (re-sourced, ingested, promoted) — not just because a lint pass ran again.
   Don't duplicate an existing entry; update it in place if a later pass adds information.
8. **Stable-slug rule**: `kb-ingest` must derive the same slug for the same source every time (see "Working
   across devices" above) and must check the wiki for an existing citation before minting a new dated raw
   folder. Re-ingesting an already-covered source reuses its existing `<date>-<slug>` path — it never creates
   a second, differently-dated raw entry for the same source, whether that's because of a fresh clone or just
   running `/kb-ingest` twice on the same device.

## Out of scope / deferred

These elements from the original workflow description are intentionally not implemented:

- **Obsidian, graph view, wikilink plugins** — dropped. Plain `.md` only.
- **Marp slideshows** — dropped. No presentation need for a code-documentation KB.
- **matplotlib image outputs** — deferred. Nothing here currently needs charts; revisit if e.g. conversion
  benchmark data gets tracked.
- **Synthetic data generation + fine-tuning** — deferred, out of active scope. This KB stays a context-window
  artifact for now.
