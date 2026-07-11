---
name: kb-ask
description: Answer a question about this repo by checking knowledge_base/outputs/qna/ for an existing answer first, then knowledge_base/wiki/, falling back to actual repo source, then optionally file the answer into knowledge_base/outputs/qna/. Use when the user runs /kb-ask <question>.
---

# kb-ask

Read `knowledge_base/README.md` first if this is your first time touching `knowledge_base/` this session.

**Scope**: this skill reads freely across the repo and `knowledge_base/`. It writes under
`knowledge_base/outputs/qna/` only when the user opts in (step 5), and may write a gap entry to
`knowledge_base/wiki/QUESTIONS.md` (step 7) regardless of that opt-in — logging a known gap isn't the same
as filing the Q&A itself.

## Steps

1. **Check for an existing answer first.** Search `knowledge_base/outputs/qna/*.md` (via
   `knowledge_base/tools/search.py` or a direct read of `outputs/_index.md`) for a filed entry that already
   answers this question, or answers it closely enough to reuse. If one does, that's the answer — don't
   re-derive it from the wiki or repo source. This is the `existing Q&A` provenance tier (see
   `knowledge_base/writing-rules.md`).
2. Otherwise, consult `knowledge_base/wiki/_index.md` to find relevant concept/decision articles, and read
   them.
3. Optionally run `knowledge_base/tools/search.py` with the question's keywords for a quick pass over
   `knowledge_base/**/*.md` before reading files by hand — useful once the corpus is bigger than a skim.
4. If the wiki doesn't fully answer the question, fall back to reading the actual repo source directly (the
   wiki is a shortcut, not the only allowed source of truth). Note whether the wiki contributed nothing
   (`repo source` tier) or contributed part of the answer (`wiki + repo source` tier).
5. Answer the question directly in the chat response first, opening with the `**Answer source:** ...`
   provenance line per `knowledge_base/writing-rules.md`, matching whichever tier steps 1-4 actually used.
6. **Ask the user** whether to file the answer into
   `knowledge_base/outputs/qna/<YYYY-MM-DD>-<slugified-question>.md`. This is opt-in per question, not
   automatic — don't file it unless the user confirms.
7. If filed: write the Q&A file (question, answer, and any sources cited), including the same
   `**Answer source:** ...` line, and rewrite `knowledge_base/outputs/_index.md` to include it.
8. If answering surfaced a gap in the wiki (missing concept, stale info), say so, log it in
   `knowledge_base/wiki/QUESTIONS.md` (check for an existing entry first — update in place rather than
   duplicating), and suggest running `/kb-compile` or `/kb-lint` — don't silently patch the wiki mid-answer.
