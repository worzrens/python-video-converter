# Why does folder mode require consistent audio and subtitle tracks across all files?

- Asked: 2026-07-11
- Sources consulted: [[../../wiki/concepts/track-validation.md]]

## Question
Why does folder mode require consistent audio and subtitle tracks across all files?

## Answer
**Answer source:** wiki

It's not that folder mode strictly *requires* consistency — `validate_folder_consistency()` in `tracks.py`
just checks it and reports the result to the user via `main.py`'s `_print_media_overview()`. The real reason
it matters is the track-selection UX: `main.py` wants to let the user pick a track once and apply it across
the whole batch. If every file has the same tracks, that's trivial. If they don't, the naive fallback
(matching by stream index) breaks, because the same logical track (e.g. English audio) can sit at a
different index in different files. `build_common_track_choices()` solves this by normalizing and
intersecting tracks by content (codec/language/title via `track_key()`) to find a track present in every
file, offering it as a single "select once, apply everywhere" choice, and only falling back to per-file
selection when no common track exists at all.
