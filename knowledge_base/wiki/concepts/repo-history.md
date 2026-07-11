# repo history: from single script to five modules

> Sources: [[../../raw/2026-07-11-git-history-highlights/meta.md]]
> Status: emerging — sole source is a curated summary, not verbatim `git log`; see [[../QUESTIONS.md]]
> Last updated: 2026-07-11

The repo's git history (`2a5b951`..`7f87966`, seven commits) traces a single-file script hardening into the
current five-module structure (`main.py`, `media.py`, `progress.py`, `tracks.py`, `conversion.py`).

**Early stabilization.** `9082294` ("fix: stabilize folder progress and ignore local artifacts") added
`.gitignore` (video extensions, `.idea/`, etc.), stabilized folder-mode progress reporting, and added
`uv.lock` — housekeeping before any structural split.

**The module split, in two commits.** `173d5a5` ("refactor: split converter logic and refine folder
prompts") shrank `main.py` from 1000+ lines to ~500 by extracting `media.py` (202 lines, see
[[media-probing]]) and `progress.py` (198 lines, see [[progress-eta-parsing]]), and added `tracks.py` (183
lines, see [[track-validation]]) for folder-prompt refinement. `efebc0c` ("refactor: decouple conversion
helpers and clean modules") then extracted `conversion.py` (259 lines, see [[ffmpeg-pipeline]]) out of
`main.py`, dropping it by another 265 lines and completing the current five-module shape — see
[[cli-prompt-flow]] for how `main.py` orchestrates all four extracted modules today.

**Two reactive fixes.** `a614d26` ("refactor: split CLI flow and add media guard") added the CI media-file
guard (see [[../decisions/ci-block-media-files]]) alongside further `main.py` CLI-flow reorganization.
`25757c5` ("fix: repair Cyrillic track titles in console") added `_repair_metadata_text()` to `media.py` to
fix ffprobe/terminal mojibake in Cyrillic track titles — see [[media-probing]]. Neither was a planned
refactor; both were responses to problems hit while using the tool.

**Convention formalization.** The most recent commit, `7f87966` ("refactor(main.py): add docstrings, type
alias, and string constants"), added `plans/main-refactoring-plan.md` and implemented it across `main.py`:
Google-style docstrings on every function, the `_StreamPositions` type alias, and the `_PROMPT_*`/`_MSG_*`
string-constant banner sections — see [[../decisions/docstring-and-banner-conventions]] for the full
rationale.

The five-module split happened in exactly two commits (`173d5a5`, `efebc0c`), not an incremental drift —
the repo went from monolith to its current shape deliberately and quickly.

## See also
- [[../decisions/docstring-and-banner-conventions]]
- [[../decisions/ci-block-media-files]]
- [[media-probing]]
- [[cli-prompt-flow]]
