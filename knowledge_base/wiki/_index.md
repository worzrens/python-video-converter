# wiki index

See [QUESTIONS.md](QUESTIONS.md) for open sourcing gaps, held tensions, and future-article candidates.

## concepts

- [ffmpeg-pipeline](concepts/ffmpeg-pipeline.md) — Encode defaults, the copy-path optimization, and subtitle-embedding validation in `conversion.py`.
- [media-probing](concepts/media-probing.md) — ffprobe parsing, Cyrillic mojibake repair, and the only-downscale resize rule in `media.py`.
- [track-validation](concepts/track-validation.md) — Folder track-consistency checks and content-based common-track matching in `tracks.py`.
- [progress-eta-parsing](concepts/progress-eta-parsing.md) — Parsing ffmpeg's progress stream and EMA-smoothing the displayed speed/ETA in `progress.py`.
- [cli-prompt-flow](concepts/cli-prompt-flow.md) — How `main.py` orchestrates the other four modules into the interactive workflow.
- [repo-history](concepts/repo-history.md) — Commit-by-commit trace of the repo's evolution from a single script into the current 5-module structure.

## decisions

- [docstring-and-banner-conventions](decisions/docstring-and-banner-conventions.md) — Google-style docstrings plus the type-alias/string-constant banner sections, from `plans/main-refactoring-plan.md`.
- [no-argparse-interactive-cli](decisions/no-argparse-interactive-cli.md) — Why `main.py` is `input()`-driven with no flag parsing, and where that decision doesn't extend to.
- [ci-block-media-files](decisions/ci-block-media-files.md) — Why the sole CI workflow exists to fail builds that track video files, and how it complements `.gitignore`.
