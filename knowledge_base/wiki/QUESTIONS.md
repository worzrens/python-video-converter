# Open questions

Open threads, sourcing gaps, held tensions, and future-article candidates surfaced during compile or lint
passes. Entries are removed once resolved (promoted into an article, ingested, or explicitly closed) —
this file tracks what's still open, not a permanent log.

## Sourcing gaps

- **`concepts/repo-history.md` is sourced from a non-verbatim raw entry.** Its only source,
  `raw/2026-07-11-git-history-highlights/meta.md`, is a curated commit-by-commit summary rather than a
  verbatim `git log` dump — `kb-ingest`'s own instructions call for a curated summary on git-history
  ingests, which is weaker provenance than the verbatim-source-code raw entries the other articles rely on.
  Marked `Status: emerging` in the article for this reason. Resolution: re-ingest with the actual `git log`
  output preserved verbatim in `source.md`, moving the curation to the wiki layer where it belongs, then
  promote to `established`.

- **`decisions/no-argparse-interactive-cli.md`'s rationale is explicitly inferred, not sourced.** The
  article's "Why" section is labeled inline as "inferred, not stated anywhere explicitly" — the decision
  itself is well-established from the code, but the *reasoning* behind it has no primary source. Left at
  `Status: established` since the documented decision is solid, but the inferred rationale specifically
  should be treated as unverified until confirmed. Resolution: if the author confirms or corrects the
  inferred motivation, fold that confirmation in as a source and remove this entry.

## Coverage gaps

- **`concepts/cli-prompt-flow.md` and `concepts/track-validation.md` describe the prompt flow but not the
  actual default values.** Neither article states that target height defaults to 1080, the proceed
  confirmation defaults to Yes, menu selections default to the first option, or that the initial estimated
  encode speed is 1.0x — all easily sourced from `tracks.py`, `main.py`, and `progress.py` directly. Answered
  ad hoc in
  [outputs/qna/2026-07-11-cli-prompt-defaults.md](../outputs/qna/2026-07-11-cli-prompt-defaults.md) in the
  meantime. Resolution: next `/kb-compile` pass should fold these concrete values into both articles (or a
  new raw entry citing them directly) and remove this line.

## Process gaps

- **No content-drift detection.** `kb-ingest`'s stable-slug reuse (see `README.md`'s "Working across
  devices") guarantees a re-ingested source lands back at the same `raw/<date>-<slug>/` path an article
  already cites, so `kb-compile` correctly leaves the article alone. But nothing currently checks whether the
  *content itself* changed since the citing article was written — if `media.py` picked up a new behavior
  since `media-probing.md` was compiled, a same-path re-ingest wouldn't surface that as stale. Resolution:
  would need `kb-lint` (or `kb-compile`) to diff a re-ingested `source.md` against what its citing article's
  `Last updated` date implies, and flag rather than silently trust a matching path.

## Future article candidates

- **The "copy path" optimization**, currently a subsection of `concepts/ffmpeg-pipeline.md`. Not warranted
  as its own article yet at current length (noted in both lint reports so far) — revisit if it grows, e.g.
  once benchmark data exists to discuss.

## Un-ingested material

- **`knowledge_base/tools/search.py` and `tests/test_kb_search.py`** are not yet ingested into `raw/` at
  all. Surfaced during a `/kb-ingest` session but the user hadn't picked a target yet — still open. The
  `README.md`'s argparse-exception note already documents *why* `search.py` deviates from the no-argparse
  convention, but the module itself has no raw entry or wiki coverage yet.
