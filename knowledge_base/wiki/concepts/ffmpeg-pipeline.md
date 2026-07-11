# ffmpeg pipeline

> Sources: [[../../raw/2026-07-11-module-conversion/meta.md]], [[../../raw/2026-07-11-module-media/meta.md]], [[../../raw/2026-07-11-module-tracks/meta.md]]
> Status: established
> Last updated: 2026-07-11

`conversion.py` is where the actual encode happens. It defines fixed defaults — `libx264` video at CRF 20 /
preset `medium`, `aac` audio at 192k, `mov_text` for embedded subtitles — and two key decisions before
building the ffmpeg command:

**The copy path.** `_should_use_copy_path()` decides whether ffmpeg can stream-copy video and audio instead
of re-encoding, which is a large speed win since `libx264` encoding is the expensive part. It requires three
things simultaneously: the output dimensions must equal the source (via `media.calculate_output_dimensions()`
— see [[media-probing]]), every audio stream's codec must already be in `COPY_SAFE_AUDIO_CODECS` (`aac`,
`ac3`, `eac3`, `mp3`), and if a subtitle track is selected it must be text-based (`tracks.is_text_subtitle()`
— see [[track-validation]]).

**Subtitle validation.** `build_ffmpeg_command()` raises `ValueError` if the user selected a bitmap subtitle
track (e.g. PGS) — MP4/`mov_text` can't embed bitmap subtitles, so this is caught at command-build time
rather than failing inside ffmpeg. This is the code-level enforcement of the README's "bitmap subtitles are
not embedded" rule.

`convert_file()` runs the assembled command with `-progress pipe:1 -nostats`, and parses ffmpeg's key=value
progress stream (`frame=`, `out_time*=`, `speed=`, `progress=end`) to drive the live ETA display — see
[[progress-eta-parsing]] for how that parsing and smoothing works.

## See also
- [[media-probing]]
- [[track-validation]]
- [[progress-eta-parsing]]
