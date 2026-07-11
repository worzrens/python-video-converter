# Lint report — 2026-07-11

## Index sync
- `raw/_index.md`: all 9 raw entries present and linked; no dangling rows. OK.
- `wiki/_index.md`: all 7 articles (5 concepts, 2 decisions) present and linked; no dangling rows. OK.
- `outputs/_index.md`: in sync with `qna/` and `lint-reports/` contents as of this report. OK.

## Link integrity
- All wiki-internal (`concepts/` <-> `decisions/`) `[[...]]` links resolve. Two broken links were found and
  fixed during this pass (see "Fixes applied" below) — both were bare same-directory references from
  `decisions/*.md` to concept articles that actually live in `../concepts/`.
- All `Sources:` links into `raw/` resolve locally (expected, since `raw/` exists on this machine; these
  links will not resolve for anyone who clones the repo without running `/kb-ingest` themselves — that's
  expected per `knowledge_base/README.md`).

## Fixes applied (mechanical only — no article content rewritten)
- `wiki/decisions/docstring-and-banner-conventions.md`: `[[cli-prompt-flow]]` → `[[../concepts/cli-prompt-flow]]` (two occurrences).
- `wiki/decisions/no-argparse-interactive-cli.md`: `[[track-validation]]` → `[[../concepts/track-validation]]`, `[[cli-prompt-flow]]` → `[[../concepts/cli-prompt-flow]]`.

## Backlink reciprocity
- Checked all 7 articles' "See also" sections. Every link is reciprocated. No one-directional backlinks found.

## Article size
- All 7 articles are 25-35 lines — within the healthy range. None flagged as too thin (<~5 lines) or too
  long (>~150 lines).

## Compile backlog (raw entries not cited by any wiki article)
- `raw/2026-07-11-git-history-highlights` — not yet referenced by any concept/decision article. Candidate:
  either fold its commit-by-commit narrative into `docstring-and-banner-conventions.md` (which already
  covers the `7f87966` commit) and a new "repo history" note, or leave as background context only.
- `raw/2026-07-11-ci-block-media-files` — not yet referenced by any article. Candidate: a new short decision
  article, e.g. `decisions/media-files-stay-out-of-git.md`, combining this with the relevant `.gitignore`
  video-extension rules.

## New-article candidates (topical overlap not yet its own article)
- The "copy path" optimization is currently folded into `ffmpeg-pipeline.md`. If it grows (e.g. once
  benchmark data exists), it could split into its own article — not needed yet at current length.

## Summary
No index desyncs, no unresolved wiki-internal links, no reciprocity gaps, no size outliers. Two raw entries
(git history, CI workflow) are genuine compile backlog — recommend running `/kb-compile` targeted at those
next, or leaving them as background-only raw material if they don't warrant a dedicated article.
