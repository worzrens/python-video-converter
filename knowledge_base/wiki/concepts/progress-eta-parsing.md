# progress and ETA parsing

> Sources: [[../../raw/2026-07-11-module-progress/meta.md]], [[../../raw/2026-07-11-module-conversion/meta.md]]
> Status: established
> Last updated: 2026-07-11

`progress.py` turns ffmpeg's noisy `-progress` key=value stream into a stable, human-readable ETA. Two
parsing quirks and one smoothing technique are worth knowing:

**`out_time_ms` is ambiguous.** ffmpeg's `out_time_ms` field is sometimes actually microseconds in practice.
`parse_progress_time()` disambiguates using plausibility bounds against `total_duration`
(`0 <= value <= max(total_duration * 1.5, 60.0)`) and prefers whichever candidate doesn't move backwards
relative to `current_seconds` if both interpretations are plausible.

**Speed smoothing.** Raw `speed=` samples from ffmpeg are jittery. `smooth_metric()` applies an exponential
moving average (`SPEED_EMA_ALPHA = 0.024`) and `clamp_relative_change()` bounds how far the displayed speed
can move between samples (`SPEED_MAX_CHANGE_RATIO = 0.30`), so the ETA doesn't visibly jump around.
`conversion.py`'s `convert_file()` also maintains its own speed *estimate* (`update_estimated_speed()`,
derived from wall-clock time vs. reported `out_time` deltas) as a fallback for when ffmpeg hasn't emitted a
`speed=` sample yet — see [[ffmpeg-pipeline]] for where this feeds into the conversion loop.

**Interactive vs. plain rendering.** `ProgressRenderer` auto-detects whether to use carriage-return in-place
updates or one-line-per-update plain output, based on the `FFCONV_PLAIN_PROGRESS` env var — useful for piping
output to a log file without carriage-return noise.

## See also
- [[ffmpeg-pipeline]]
- [[cli-prompt-flow]]
