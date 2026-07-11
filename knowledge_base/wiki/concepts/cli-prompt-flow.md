# CLI prompt flow

> Sources: [[../../raw/2026-07-11-module-main/meta.md]], [[../../raw/2026-07-11-main-refactoring-plan/meta.md]]
> Status: established
> Last updated: 2026-07-11

`main.py` is the orchestrator: it wires `media.py`, `tracks.py`, `progress.py`, and `conversion.py` into the
single interactive workflow described in the README.

The flow, function by function: `_ensure_cli_dependencies()` checks ffmpeg/ffprobe are on PATH →
`_prompt_input_path()` reads and resolves the target path → `media.discover_targets()` +
`media.probe_media()` find and probe the files → `_print_media_overview()` prints the summary and, in folder
mode, calls `tracks.validate_folder_consistency()` (see [[track-validation]]) → `_select_stream_positions()`
resolves audio/subtitle choices, either globally (consistent folder) or per-file (inconsistent folder,
delegating to `tracks.resolve_folder_stream_positions()`) → `_prepare_batch_progress()` estimates total time
from summed durations (see [[progress-eta-parsing]]) → the user confirms via `tracks.prompt_yes_no()` →
`_run_conversion_batch()` calls `conversion.convert_file()` per file (see [[ffmpeg-pipeline]]), updating
progress after each.

This module is also the canonical example of two repo-wide conventions established by commit `7f87966`
(see [[../decisions/docstring-and-banner-conventions]]): the `# --- Type aliases ---` banner (defining
`_StreamPositions`, a 4-tuple type alias for the audio/subtitle position results) and the
`# --- User-facing string constants ---` banner (`_PROMPT_*`/`_MSG_*` constants using `.format()`, not
f-strings, since they're defined once at module level and applied later). See
[[../decisions/no-argparse-interactive-cli]] for why this whole flow is `input()`-driven rather than
flag-based.

## See also
- [[track-validation]]
- [[progress-eta-parsing]]
- [[../decisions/no-argparse-interactive-cli]]
- [[../decisions/docstring-and-banner-conventions]]
- [[repo-history]]
