# ffmpeg-converter

Interactive Python CLI for converting movie files with `ffmpeg`.

## What it does

- Accepts either a single movie file or a folder of movie files.
- Reads metadata with `ffprobe` before converting.
- Shows file format, size, resolution, audio tracks, and subtitle tracks.
- Lets you choose the default audio track.
- Lets you choose one subtitle track to embed, or skip subtitles.
- Lets you choose the target output height, with `1080` as the default.
- Shows an estimated conversion time before you confirm, starting from a 1.0x encode-speed baseline.
- Displays live progress while ffmpeg is converting, with ETA updated from ffmpeg's reported speed.
- Checks that all files in a folder have matching audio and subtitle track layouts.
- Converts to `.mp4` using `ffmpeg`.
- Preserves aspect ratio during resize.
- Only downscales when the source is above 1080p.
- Leaves resolution unchanged for 1080p or smaller sources.
- Writes single-file output as `<original_name>-COMPRESSED.mp4` in the same folder.
- Writes folder output into a sibling folder named `<original_name>-COMPRESSED`.

## Current conversion rules

- Target height: user-selected, defaulting to `1080` when left blank.
- If the source video height is greater than 1080, the script calculates a new width from the source aspect ratio and scales down to `1080p`.
- If the source video is already at or below the chosen target height, the resolution is left untouched.
- Audio is encoded with `aac`.
- Video is encoded with `libx264`.
- Subtitle tracks are converted to `mov_text` when present.
- Bitmap subtitles such as PGS are not embedded into MP4.

## Workflow

1. Start the script.
2. Enter a path to either one file or one folder.
3. The script probes media metadata.
4. If a folder was selected, it verifies track consistency across all files.
5. Choose the default audio track.
6. Choose one subtitle track to embed, or choose none.
7. Choose the target output height, or press Enter to use 1080.
8. See the estimated conversion time.
9. Confirm conversion with Enter accepted as yes.
10. The script runs `ffmpeg` and writes the converted file(s) with live progress.

## Internal functions

- `probe_media()` — reads `ffprobe` JSON metadata and normalizes it.
- `discover_targets()` — resolves whether the input is a file or folder.
- `validate_folder_consistency()` — checks that track layouts match across a folder.
- `calculate_target_width()` — computes the output width only when downscaling is needed.
- `build_ffmpeg_command()` — assembles the final `ffmpeg` command.
- `convert_file()` — executes the conversion.
- `main()` — runs the interactive CLI.

## Requirements

- Python 3.13+
- `ffmpeg` available on `PATH`
- `ffprobe` available on `PATH`

## Notes

- The script currently scans only the top level of a folder.
- Output name collisions are handled by appending a numeric suffix.
- A 2-minute test clip lives in `tests/Severance.S01E01.1080.2min.mkv` for local smoke tests.
