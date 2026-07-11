# track validation

> Sources: [[../../raw/2026-07-11-module-tracks/meta.md]], [[../../raw/2026-07-11-module-main/meta.md]]
> Status: established
> Last updated: 2026-07-11

`tracks.py` handles two related but distinct problems: validating and matching tracks.

**Folder consistency.** `validate_folder_consistency()` compares every file's audio/subtitle stream
signature (codec, language, title — not stream index) against the first file's, returning independent
`(audio_consistent, subtitle_consistent)` booleans. `main.py`'s `_print_media_overview()` calls this in
folder mode and prints "Tracks match across files" or the mismatch warning accordingly.

**Common-track matching across a mismatched folder.** When tracks *aren't* consistent, the naive approach
(match by stream index) breaks, because the same logical track (e.g. English audio) can sit at position 1 in
one file and position 2 in another. `track_key()` solves this by normalizing (casefold + whitespace-collapse)
codec/language/title into a comparable tuple, and `build_common_track_choices()` intersects these keys across
every file's stream list to find tracks present in all of them — regardless of index. The user is then
offered a single "select once, apply everywhere" choice when a common track exists, falling back to
per-file selection otherwise.

All the actual `input()`-driven selection primitives (`choose_stream_position`, `choose_menu_option`,
`prompt_yes_no`, `prompt_target_height`) also live in this module — see
[[../decisions/no-argparse-interactive-cli|the no-argparse decision]] for why this repo uses raw prompts
instead of a flag-parsing library.

## See also
- [[ffmpeg-pipeline]]
- [[media-probing]]
- [[cli-prompt-flow]]
- [[../decisions/no-argparse-interactive-cli]]
