"""CLI entry point that orchestrates discovery, prompting, and conversion."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Sequence

from conversion import build_ffmpeg_command, convert_file
from media import (
    build_output_path,
    calculate_output_dimensions,
    discover_targets,
    format_media_summary,
    probe_media,
)
from progress import (
    BatchProgressState,
    DEFAULT_ESTIMATED_ENCODE_SPEED,
    ProgressRenderer,
    estimate_conversion_time,
    estimate_total_duration,
    format_batch_progress_line,
    format_seconds,
)
from tracks import (
    choose_stream_position,
    prompt_target_height,
    prompt_yes_no,
    resolve_folder_stream_positions,
    validate_folder_consistency,
)


def main(argv: Sequence[str] | None = None) -> int:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("ffmpeg and ffprobe must be installed and available on PATH.", file=sys.stderr)
        return 1

    raw_path = input("Enter path to a movie file or folder: ").strip()
    if not raw_path:
        print("No path provided.", file=sys.stderr)
        return 1

    try:
        input_path = Path(raw_path).expanduser().resolve()
        sources, is_folder_mode, output_root = discover_targets(input_path)
        media_infos = [probe_media(source) for source in sources]

        print()
        print(format_media_summary(media_infos[0], include_tracks=not is_folder_mode))
        if is_folder_mode:
            audio_consistent, subtitle_consistent = validate_folder_consistency(media_infos)
            print(f"\nFolder contains {len(media_infos)} movie files.")
            if audio_consistent and subtitle_consistent:
                print("Tracks match across files.")
            else:
                if not audio_consistent:
                    print("Audio tracks differ across files.")
                if not subtitle_consistent:
                    print("Subtitle tracks differ across files.")
        else:
            print("\nSingle-file mode.")

        target_height = prompt_target_height()
        estimated_duration = estimate_total_duration(media_infos)
        estimated_time = estimate_conversion_time(estimated_duration)
        print(f"Estimated conversion time (starting at {DEFAULT_ESTIMATED_ENCODE_SPEED:.1f}x): {format_seconds(estimated_time)}")

        if is_folder_mode:
            audio_positions = resolve_folder_stream_positions(
                media_infos,
                "audio_streams",
                "audio",
                consistent=audio_consistent,
            )
            subtitle_positions = resolve_folder_stream_positions(
                media_infos,
                "subtitle_streams",
                "subtitle",
                consistent=subtitle_consistent,
                allow_none=True,
            )
        else:
            audio_position = choose_stream_position(media_infos[0].audio_streams, "audio")
            subtitle_position = choose_stream_position(media_infos[0].subtitle_streams, "subtitle", allow_none=True)

        total_duration = estimated_duration or 0.0
        batch_progress = BatchProgressState(
            total_files=len(media_infos),
            completed_files=0,
            total_seconds=total_duration,
            completed_seconds=0.0,
        )
        renderer = ProgressRenderer()

        if not prompt_yes_no("Proceed with conversion?", default=True):
            print("Cancelled.")
            return 0

        renderer.render(
            format_batch_progress_line(
                completed_seconds=batch_progress.completed_seconds,
                total_seconds=batch_progress.total_seconds,
                completed_files=batch_progress.completed_files,
                total_files=batch_progress.total_files,
                current_file_number=1,
                current_speed=None,
                use_color=renderer.interactive,
            )
        )

        for index, media in enumerate(media_infos, start=1):
            output_dimensions = calculate_output_dimensions(media, target_height)
            output = build_output_path(media.path, is_folder_mode, output_root, output_dimensions)
            output.parent.mkdir(parents=True, exist_ok=True)
            if is_folder_mode:
                audio_position = audio_positions[index - 1]
                subtitle_position = subtitle_positions[index - 1]
            convert_file(
                media.path,
                output,
                media,
                audio_position or 0,
                subtitle_position,
                target_height,
                batch_progress=batch_progress,
                renderer=renderer,
                current_file_number=index,
            )
            if media.duration_seconds is not None:
                batch_progress.completed_seconds += media.duration_seconds
            batch_progress.completed_files = index

        renderer.finish()
        print(f"Converted {batch_progress.completed_files}/{batch_progress.total_files} files.")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
