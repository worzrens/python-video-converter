# Lint report — 2026-07-11 (2)

Second pass today, run after `/kb-compile` closed out the two compile-backlog items the first report
(`2026-07-11-lint-report.md`) flagged.

## Index sync
- `raw/_index.md`: all 9 raw entries present and linked; no dangling rows. OK.
- `wiki/_index.md`: all 9 articles (6 concepts, 3 decisions) present and linked, including the two added
  this session (`concepts/repo-history.md`, `decisions/ci-block-media-files.md`). No dangling rows. OK.
- `outputs/_index.md`: in sync with `qna/` and `lint-reports/` as of just before this report was filed. OK.

## Link integrity
- All wiki-internal (`concepts/` <-> `decisions/`) `[[...]]` links resolve, including the new links into and
  out of `repo-history.md` and `ci-block-media-files.md`. No broken links found — the two broken links from
  the first lint pass were already fixed and stayed fixed.
- All `Sources:` links into `raw/` resolve locally (`raw/` exists on this machine).

## Fixes applied
None needed this pass.

## Backlink reciprocity
- Checked all 9 articles' "See also" sections. Every link is reciprocated, including the four new
  `repo-history` links (to `docstring-and-banner-conventions`, `ci-block-media-files`, `media-probing`,
  `cli-prompt-flow`) and their return links.
- Note (not a violation): `docstring-and-banner-conventions.md` has an inline body reference to
  `[[no-argparse-interactive-cli]]` that isn't mirrored in either article's "See also" list. The
  reciprocity rule applies to "See also" links specifically, so this isn't flagged as broken — noting it
  only in case a future compile pass wants to promote it to a formal backlink.

## Article size
- All 9 articles are 25-39 lines — within the healthy range. None flagged as too thin (<~5 lines) or too
  long (>~150 lines). `repo-history.md` (39 lines) is the longest, still well within bounds.

## Compile backlog (raw entries not cited by any wiki article)
- None. All 9 raw entries are now cited by at least one wiki article.

## New-article candidates (topical overlap not yet its own article)
- The "copy path" optimization is still folded into `ffmpeg-pipeline.md`. Unchanged from the last report —
  not warranted at current length.
- No new overlap introduced by this session's two new articles.

## Summary
Clean bill of health: no index desyncs, no unresolved links, no reciprocity gaps, no size outliers, and the
compile backlog from the last report is now empty. Nothing outstanding for `/kb-compile`.
