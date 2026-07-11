# media probing

> Sources: [[../../raw/2026-07-11-module-media/meta.md]]
> Status: established
> Last updated: 2026-07-11

`media.py` is the boundary between ffprobe's JSON output and the rest of the codebase. `probe_media()` shells
out to `ffprobe -show_format -show_streams` and parses the result into a frozen `MediaInfo` dataclass (path,
format, duration, size, dimensions, frame rate) with lists of `MediaStream` (index, codec, language, title,
default flag) for audio and subtitle tracks.

Two details worth knowing:

- **Cyrillic mojibake repair.** `_repair_metadata_text()` (added in commit `25757c5`) fixes track
  titles/languages that ffprobe/the terminal mangle — it re-encodes the string as `cp1251` then decodes as
  UTF-8, which recovers the original Cyrillic text. This exists because real-world files hit this in
  practice, not as a preemptive fix.
- **Even-dimension rounding.** `calculate_target_width()` implements "only downscale, never upscale":
  if the source is already at or below the target height, no resize happens at all (this is also what makes
  the [[ffmpeg-pipeline|copy path]] possible for already-1080p-or-smaller sources). When it does downscale,
  the computed width is rounded down to the nearest even number (`max(2, (width // 2) * 2)`), because
  `yuv420p` output requires even dimensions.

`discover_targets()` also lives here: it resolves a user path into either a single file or a **top-level-only**
folder scan restricted to `VIDEO_EXTENSIONS`, and computes the folder-mode output root
(`<name>-COMPRESSED`).

## See also
- [[ffmpeg-pipeline]]
- [[track-validation]]
- [[repo-history]]
