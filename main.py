"""CLI entry point that orchestrates discovery, prompting, and conversion.

This module provides the interactive command-line interface for converting
video files using ffmpeg. It handles file discovery, metadata probing,
track selection, and batch conversion with live progress reporting.
"""

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

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

_StreamPositions = tuple[
    list[int] | None,  # audio_positions
    list[int] | None,  # subtitle_positions
    int | None,        # audio_position
    int | None,        # subtitle_position
]

# ---------------------------------------------------------------------------
# User-facing string constants
# ---------------------------------------------------------------------------

_PROMPT_INPUT_PATH = "Enter path to a movie file or folder: "
_PROMPT_PROCEED = "Proceed with conversion?"
_MSG_CANCELLED = "Cancelled."
_MSG_NO_PATH = "No path provided."
_MSG_DEPENDENCIES = "ffmpeg and ffprobe must be installed and available on PATH."
_MSG_CONVERTED = "Converted {completed}/{total} files."
_MSG_SINGLE_FILE_MODE = "Single-file mode."
_MSG_TRACKS_MATCH = "Tracks match across files."
_MSG_AUDIO_DIFFER = "Audio tracks differ across files."
_MSG_SUBTITLE_DIFFER = "Subtitle tracks differ across files."
_MSG_FOLDER_COUNT = "Folder contains {count} movie files."
_MSG_NO_MEDIA = "No media files to process."


def _ensure_cli_dependencies() -> bool:
    """Verify that ffmpeg and ffprobe are installed and available on PATH.

    Checks both tools using shutil.which(). Prints an error message to
    stderr if either is missing.

    Returns:
        True if both tools are found; False otherwise.
    """
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print(_MSG_DEPENDENCIES, file=sys.stderr)
        return False
    return True


def _prompt_input_path() -> Path | None:
    """Prompt the user for a file or folder path and resolve it.

    Reads from stdin, strips whitespace, and rejects empty input.
    Expands user home directory shortcuts (~) and resolves to an
    absolute path.

    Returns:
        A resolved Path object if the user provides input;
        None if the input is empty.
    """
    raw_path = input(_PROMPT_INPUT_PATH).strip()
    if not raw_path:
        print(_MSG_NO_PATH, file=sys.stderr)
        return None
    return Path(raw_path).expanduser().resolve()


def _print_media_overview(
    media_infos: Sequence[MediaInfo],
    is_folder_mode: bool,
) -> tuple[bool, bool]:
    """Display media metadata and, for folder mode, validate track consistency.

    Prints a formatted summary of the first file (format, size, resolution,
    tracks). In folder mode, also validates that all files have matching
    audio and subtitle track layouts.

    Args:
        media_infos: List of MediaInfo objects for the target files.
        is_folder_mode: True if processing multiple files from a folder.

    Returns:
        A tuple of (audio_consistent, subtitle_consistent) booleans.
        In single-file mode, always returns (True, True).
    """
    if not media_infos:
        print(_MSG_NO_MEDIA, file=sys.stderr)
        return False, False

    print()
    print(format_media_summary(media_infos[0], include_tracks=not is_folder_mode))
    if is_folder_mode:
        audio_consistent, subtitle_consistent = validate_folder_consistency(media_infos)
        print(f"\n{_MSG_FOLDER_COUNT.format(count=len(media_infos))}")
        if audio_consistent and subtitle_consistent:
            print(_MSG_TRACKS_MATCH)
        else:
            if not audio_consistent:
                print(_MSG_AUDIO_DIFFER)
            if not subtitle_consistent:
                print(_MSG_SUBTITLE_DIFFER)
        return audio_consistent, subtitle_consistent

    print(f"\n{_MSG_SINGLE_FILE_MODE}")
    return True, True


def _prepare_batch_progress(media_infos: Sequence[MediaInfo]) -> BatchProgressState:
    """Estimate total conversion time and initialize batch progress tracking.

    Sums the duration of all media files and calculates an estimated
    conversion time based on a default encode speed of 1.0x. Prints
    the estimate to stdout.

    Args:
        media_infos: List of MediaInfo objects whose durations are summed.

    Returns:
        A BatchProgressState initialized with total file count,
        zeroed completed counters, and the estimated total duration.
    """
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
) -> _StreamPositions:
    """Resolve audio and subtitle stream positions for all target files.

    In folder mode, delegates to resolve_folder_stream_positions() which
    handles common-track selection across files with potentially different
    stream indices. In single-file mode, prompts the user to select a
    single audio and subtitle track.

    Args:
        media_infos: List of MediaInfo objects for the target files.
        is_folder_mode: True if processing multiple files from a folder.
        audio_consistent: Whether audio track layouts match across files.
        subtitle_consistent: Whether subtitle track layouts match across files.

    Returns:
        A tuple of four values:
            - audio_positions: List of per-file audio stream indices (folder mode) or None.
            - subtitle_positions: List of per-file subtitle stream indices (folder mode) or None.
            - audio_position: Single audio stream index (single-file mode) or None.
            - subtitle_position: Single subtitle stream index (single-file mode) or None.
    """
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
    """Execute ffmpeg conversion for each media file in sequence.

    For each file, calculates the output dimensions, builds the output
    path, creates parent directories, and invokes convert_file(). Updates
    the batch progress state after each file completes.

    Args:
        media_infos: List of MediaInfo objects for the target files.
        target_height: Target output height in pixels.
        is_folder_mode: True if output should go into a sibling directory.
        output_root: Root directory for folder-mode output, or None.
        audio_positions: Per-file audio stream indices (folder mode).
        subtitle_positions: Per-file subtitle stream indices (folder mode).
        audio_position: Single audio stream index (single-file mode).
        subtitle_position: Single subtitle stream index (single-file mode).
        batch_progress: Shared progress state updated after each file.
        renderer: ProgressRenderer instance for terminal output.
    """
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
    print(_MSG_CONVERTED.format(
        completed=batch_progress.completed_files,
        total=batch_progress.total_files,
    ))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the interactive video conversion CLI.

    Orchestrates the full conversion workflow:
    1. Verify ffmpeg/ffprobe dependencies.
    2. Prompt for input path (file or folder).
    3. Discover target files and probe their metadata.
    4. Display media overview and validate track consistency.
    5. Prompt for target height, audio/subtitle track selection.
    6. Show estimated conversion time and request confirmation.
    7. Execute batch conversion with live progress updates.

    Args:
        argv: Optional command-line arguments (passed to subprocess calls).
              If None, uses default behavior.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
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

        if not prompt_yes_no(_PROMPT_PROCEED, default=True):
            print(_MSG_CANCELLED)
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
