"""CLI entry point that orchestrates discovery, prompting, and conversion."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Sequence

from conversion import convert_file
from media import (
    MediaInfo,
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


def _ensure_cli_dependencies() -> bool:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("ffmpeg and ffprobe must be installed and available on PATH.", file=sys.stderr)
        return False
    return True


def _prompt_input_path() -> Path | None:
    raw_path = input("Enter path to a movie file or folder: ").strip()
    if not raw_path:
        print("No path provided.", file=sys.stderr)
        return None
    return Path(raw_path).expanduser().resolve()


def _print_media_overview(media_infos: Sequence[MediaInfo], is_folder_mode: bool) -> tuple[bool, bool]:
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
        return audio_consistent, subtitle_consistent

    print("\nSingle-file mode.")
    return True, True


def _prepare_batch_progress(media_infos: Sequence[MediaInfo]) -> BatchProgressState:
    estimated_duration = estimate_total_duration(media_infos)
    estimated_time = estimate_conversion_time(estimated_duration)
    print(
        f"Estimated conversion time (starting at {DEFAULT_ESTIMATED_ENCODE_SPEED:.1f}x): "
        f"{format_seconds(estimated_time)}"
    )
    return BatchProgressState(
        total_files=len(media_infos),
        completed_files=0,
        total_seconds=estimated_duration or 0.0,
        completed_seconds=0.0,
    )


def _select_stream_positions(
    media_infos: Sequence[MediaInfo],
    is_folder_mode: bool,
    audio_consistent: bool,
    subtitle_consistent: bool,
) -> tuple[list[int] | None, list[int] | None, int | None, int | None]:
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
        return audio_positions, subtitle_positions, None, None

    audio_position = choose_stream_position(media_infos[0].audio_streams, "audio")
    subtitle_position = choose_stream_position(media_infos[0].subtitle_streams, "subtitle", allow_none=True)
    return None, None, audio_position, subtitle_position


def _run_conversion_batch(
    media_infos: Sequence[MediaInfo],
    target_height: int,
    is_folder_mode: bool,
    output_root: Path | None,
    audio_positions: list[int] | None,
    subtitle_positions: list[int] | None,
    audio_position: int | None,
    subtitle_position: int | None,
    batch_progress: BatchProgressState,
    renderer: ProgressRenderer,
) -> None:
    for index, media in enumerate(media_infos, start=1):
        output_dimensions = calculate_output_dimensions(media, target_height)
        output = build_output_path(media.path, is_folder_mode, output_root, output_dimensions)
        output.parent.mkdir(parents=True, exist_ok=True)
        current_audio_position = audio_positions[index - 1] if audio_positions is not None else audio_position or 0
        current_subtitle_position = subtitle_positions[index - 1] if subtitle_positions is not None else subtitle_position
        convert_file(
            media.path,
            output,
            media,
            current_audio_position,
            current_subtitle_position,
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


def main(argv: Sequence[str] | None = None) -> int:
    if not _ensure_cli_dependencies():
        return 1

    try:
        input_path = _prompt_input_path()
        if input_path is None:
            return 1

        sources, is_folder_mode, output_root = discover_targets(input_path)
        media_infos = [probe_media(source) for source in sources]

        audio_consistent, subtitle_consistent = _print_media_overview(media_infos, is_folder_mode)
        target_height = prompt_target_height()
        batch_progress = _prepare_batch_progress(media_infos)
        audio_positions, subtitle_positions, audio_position, subtitle_position = _select_stream_positions(
            media_infos,
            is_folder_mode,
            audio_consistent,
            subtitle_consistent,
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

        _run_conversion_batch(
            media_infos,
            target_height,
            is_folder_mode,
            output_root,
            audio_positions,
            subtitle_positions,
            audio_position,
            subtitle_position,
            batch_progress,
            renderer,
        )
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
