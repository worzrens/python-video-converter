---
name: kb-lint
description: Run a health check over knowledge_base/ - broken links, stale indexes, thin or bloated articles, uncompiled raw entries, and candidate new articles - and file a lint report. Use when the user runs /kb-lint.
---

# kb-lint

Read `knowledge_base/README.md` first if this is your first time touching `knowledge_base/` this session.

**Scope**: this skill writes under `knowledge_base/outputs/lint-reports/` and `knowledge_base/wiki/QUESTIONS.md`
(plus the mechanical fixes described in step 3). It never rewrites article *body* content — writing-rules
fixes touch only the flagged word/pattern, not surrounding prose — and never touches anything outside
`knowledge_base/`.

## Steps

1. Read `knowledge_base/writing-rules.md` and `knowledge_base/wiki/QUESTIONS.md` alongside the usual state.
   Check that `raw/_index.md`, `wiki/_index.md`, and `outputs/_index.md` are each in sync with the actual
   contents of their directories — no missing entries, no entries pointing at deleted files.
2. Check every wiki article's `Sources:` line and `See also` backlinks resolve.
   - A dangling link into `raw/` is **expected and OK** if `knowledge_base/raw/` doesn't exist locally at all
     (e.g. a fresh clone) — only flag it as broken if `raw/` exists locally and the specific target is still
     missing.
   - A dangling link *within* `wiki/` (concept-to-concept) is always a real bug.
3. Mechanical fixes you MAY apply directly: broken backlinks that should be reciprocal but aren't, stale
   `_index.md` rows, unambiguous `writing-rules.md` violations (banned-word swaps with a clear replacement,
   the em-dash-bullet-pattern fix, obvious US→UK spelling slips), and `Status: emerging` → `established`
   promotions per the Status-integrity rule (a second independent, sufficiently primary source now exists).
   Do NOT rewrite article body content beyond these targeted fixes — broader rewrites are `kb-compile`'s job.
   Log every fix in the CHANGELOG-style "Fixes applied" section of the report (see below).
4. Flag concept/decision articles under ~5 lines (too thin — candidate for merging) or over ~150 lines
   (candidate for splitting). Flag any article whose `Status` looks miscalibrated against its actual sourcing
   (e.g. `established` resting on a single non-primary source) — don't auto-downgrade, that's a judgement
   call.
5. Flag raw entries that no wiki article cites at all ("compile backlog").
6. Look for topical overlap across raw entries or existing articles that suggests a new article candidate
   not yet written — propose it, don't auto-create it.
7. Flag banned-word or spelling violations where the replacement isn't obvious, same treatment as any other
   judgement call — don't force an awkward rewrite.
8. **Mirror gaps into `wiki/QUESTIONS.md`.** Anything this pass surfaces that it doesn't fix outright —
   compile backlog, a miscalibrated `Status`, a new-article candidate, an unresolved banned-word call — gets
   logged there if it isn't already (check for an existing entry first; update in place rather than
   duplicating). Conversely, if this pass shows an existing `QUESTIONS.md` entry is now resolved, remove it.
9. Write findings to `knowledge_base/outputs/lint-reports/<YYYY-MM-DD>-lint-report.md` (always file this,
   unlike `kb-ask`'s opt-in filing — a lint report is inherently a log) and rewrite
   `knowledge_base/outputs/_index.md` to include it.
10. Print a short summary in chat. Let the user decide whether to act on suggestions via `/kb-compile` or a
    manual edit.

There is no scheduled trigger for this skill yet — see `knowledge_base/README.md`'s "Suggested lint cadence"
section for the (currently manual-only) design. Every run today is on-demand.
