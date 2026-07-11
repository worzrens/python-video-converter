# decision: CI guard against committing media files

> Sources: [[../../raw/2026-07-11-ci-block-media-files/meta.md]]
> Status: established
> Last updated: 2026-07-11

**Decision:** the only CI workflow in this repo, `.github/workflows/block-media-files.yml`, runs on every
push and pull request and fails the build if any video file is tracked in git. It checks out the repo, runs
`git ls-files -- '*.mp4' '*.mkv'`, and exits 1 (printing the offending paths) if that returns anything.

**Why:** this is a video-conversion tool that routinely handles large media files locally, but those files
must never end up in git history — binary video files would bloat the repo permanently, since git history
isn't easily rewritten after the fact. `.gitignore` already excludes a wide set of video extensions
(`.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`, `.m4v`, `.ts`, `.flv`, `.wmv`) by default, so this workflow is a
hard backstop for the case where someone force-adds a media file (`git add -f`) despite the ignore rules —
`.gitignore` alone can't stop that.

**Scope:** the workflow only checks `*.mp4` and `*.mkv` explicitly, narrower than the full set of extensions
`.gitignore` blocks. There is no lint or test job anywhere in this repo's CI — this is the sole workflow, and
its only job is keeping tracked binaries out of history, not verifying code correctness.

**Origin:** added in commit `a614d26` ("refactor: split CLI flow and add media guard"), landing alongside a
`main.py` CLI-flow refactor rather than as a standalone change — see [[../concepts/repo-history]] for how
this fits into the repo's broader evolution.

This is also why `knowledge_base/raw/` needed its own explicit `.gitignore` entry rather than relying on this
workflow: the workflow only blocks git history at push/PR time, it doesn't prevent files from being written
to disk or staged locally, and `raw/`'s ingested content is meant to stay local-only regardless.

## See also
- [[../concepts/repo-history]]
