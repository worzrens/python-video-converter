from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

from media import (
    MediaInfo,
    MediaStream,
    build_output_path,
    calculate_output_dimensions,
    calculate_target_width,
    discover_targets,
    format_media_summary,
    parse_frame_rate,
    probe_media,
)
from progress import (
    BatchProgressState,
    DEFAULT_ESTIMATED_ENCODE_SPEED,
    PROGRESS_STATS_PERIOD,
    ProgressRenderer,
    clamp_relative_change,
    estimate_conversion_time,
    estimate_total_duration,
    format_batch_progress_line,
    format_progress_line,
    format_seconds,
    format_speed,
    parse_progress_speed,
    parse_progress_time,
    smooth_metric,
)
from tracks import (
    SUPPORTED_SUBTITLE_CODECS,
    build_common_track_choices,
    choose_menu_option,
    choose_stream_position,
    format_common_track_positions,
    is_text_subtitle,
    media_signature,
    prompt_target_height,
    prompt_yes_no,
    resolve_folder_stream_positions,
    resolve_folder_track_positions,
    track_key,
    validate_folder_consistency,
)


DEFAULT_VIDEO_CODEC = "libx264"
DEFAULT_VIDEO_CRF = "20"
DEFAULT_VIDEO_PRESET = "medium"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_AUDIO_BITRATE = "192k"
DEFAULT_SUBTITLE_CODEC = "mov_text"
COPY_SAFE_AUDIO_CODECS = {"aac", "ac3", "eac3", "mp3"}


def _can_copy_audio_tracks(media: MediaInfo) -> bool:
    return all((stream.codec_name or "").lower() in COPY_SAFE_AUDIO_CODECS for stream in media.audio_streams)


def _should_use_copy_path(media: MediaInfo, target_height: int, subtitle_position: int | None) -> bool:
    output_width, output_height = calculate_output_dimensions(media, target_height)
    if (output_width, output_height) != (media.width, media.height):
        return False
    if not _can_copy_audio_tracks(media):
        return False
    if subtitle_position is None:
        return True
    selected_subtitle = media.subtitle_streams[subtitle_position]
    return is_text_subtitle(selected_subtitle.codec_name)


def build_ffmpeg_command(
    source: Path,
    output: Path,
    media: MediaInfo,
    default_audio_position: int,
    default_subtitle_position: int | None,
    target_height: int,
) -> list[str]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-stats_period",
        PROGRESS_STATS_PERIOD,
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a",
    ]

    output_width, output_height = calculate_output_dimensions(media, target_height)

    if default_subtitle_position is not None:
        selected_subtitle = media.subtitle_streams[default_subtitle_position]
        if not is_text_subtitle(selected_subtitle.codec_name):
            raise ValueError(
                f"Selected subtitle track {default_subtitle_position + 1} uses {selected_subtitle.codec_name or 'unknown'} and cannot be embedded in MP4"
            )
        command.extend(["-map", f"0:s:{default_subtitle_position}", "-c:s", DEFAULT_SUBTITLE_CODEC])

    if _should_use_copy_path(media, target_height, default_subtitle_position):
        command.extend(["-c:v", "copy", "-c:a", "copy"])
    else:
        if (output_width, output_height) != (media.width, media.height):
            command.extend(["-vf", f"scale={output_width}:{output_height}"])
        command.extend(
            [
                "-c:v",
                DEFAULT_VIDEO_CODEC,
                "-crf",
                DEFAULT_VIDEO_CRF,
                "-preset",
                DEFAULT_VIDEO_PRESET,
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                DEFAULT_AUDIO_CODEC,
                "-b:a",
                DEFAULT_AUDIO_BITRATE,
            ]
        )

    for index in range(len(media.audio_streams)):
        if index != default_audio_position:
            command.extend([f"-disposition:a:{index}", "0"])
    command.extend([f"-disposition:a:{default_audio_position}", "default"])

    if default_subtitle_position is not None:
        command.extend(["-disposition:s:0", "default"])

    command.append(str(output))
    return command


def convert_file(
    source: Path,
    output: Path,
    media: MediaInfo,
    audio_position: int,
    subtitle_position: int | None,
    target_height: int,
    batch_progress: BatchProgressState | None = None,
    renderer: ProgressRenderer | None = None,
    current_file_number: int | None = None,
) -> None:
    command = build_ffmpeg_command(source, output, media, audio_position, subtitle_position, target_height)
    command = command[:-1] + ["-progress", "pipe:1", "-nostats", command[-1]]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    assert process.stdout is not None
    total_duration = media.duration_seconds
    last_render = ""
    current_seconds: float | None = None
    current_speed: float | None = None
    current_frame: int | None = None
    has_valid_out_time = False
    last_speed_sample_seconds: float | None = None
    last_speed_sample_at: float | None = None
    estimated_speed: float | None = None
    displayed_speed: float | None = None
    renderer = renderer or ProgressRenderer()

    def update_estimated_speed() -> None:
        nonlocal last_speed_sample_seconds, last_speed_sample_at, estimated_speed
        if current_seconds is None or current_seconds < 0:
            return
        now = time.monotonic()
        if (
            last_speed_sample_seconds is not None
            and last_speed_sample_at is not None
            and current_seconds > last_speed_sample_seconds
            and now > last_speed_sample_at
        ):
            delta_seconds = current_seconds - last_speed_sample_seconds
            delta_wall = now - last_speed_sample_at
            if delta_wall >= 0.20 and delta_seconds >= 0.50:
                estimated_speed = delta_seconds / delta_wall
        last_speed_sample_seconds = current_seconds
        last_speed_sample_at = now

    def display_speed() -> float | None:
        nonlocal displayed_speed
        raw_speed = current_speed if current_speed is not None and current_speed > 0 else estimated_speed
        if raw_speed is None or raw_speed <= 0:
            return displayed_speed
        bounded_speed = clamp_relative_change(displayed_speed, raw_speed)
        displayed_speed = smooth_metric(displayed_speed, bounded_speed, 0.024)
        return displayed_speed

    for raw_line in process.stdout:
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == "frame":
            if value.isdigit():
                current_frame = int(value)
                if not has_valid_out_time and media.frame_rate and media.frame_rate > 0:
                    derived_seconds = current_frame / media.frame_rate
                    if current_seconds is None:
                        current_seconds = derived_seconds
                    else:
                        current_seconds = max(current_seconds, derived_seconds)
                    update_estimated_speed()
                    speed_for_render = display_speed()
                    if batch_progress is not None:
                        global_seconds = batch_progress.completed_seconds + current_seconds
                        global_line = format_batch_progress_line(
                            completed_seconds=global_seconds,
                            total_seconds=batch_progress.total_seconds,
                            completed_files=batch_progress.completed_files,
                            total_files=batch_progress.total_files,
                            current_file_number=current_file_number,
                            current_speed=speed_for_render,
                            use_color=renderer.interactive,
                        )
                        renderer.render(global_line)
                    else:
                        renderer.render_line(format_progress_line(current_seconds, total_duration, speed_for_render))
        elif key in {"out_time", "out_time_ms", "out_time_us"}:
            parsed_seconds = parse_progress_time(
                value,
                key=key,
                total_duration=total_duration,
                current_seconds=current_seconds,
            )
            if parsed_seconds is None:
                continue
            has_valid_out_time = True
            current_seconds = parsed_seconds
            update_estimated_speed()
            speed_for_render = display_speed()
            last_render = format_progress_line(current_seconds, total_duration, speed_for_render)
            if batch_progress is not None:
                global_seconds = batch_progress.completed_seconds + current_seconds
                global_line = format_batch_progress_line(
                    completed_seconds=global_seconds,
                    total_seconds=batch_progress.total_seconds,
                    completed_files=batch_progress.completed_files,
                    total_files=batch_progress.total_files,
                    current_file_number=current_file_number,
                    current_speed=speed_for_render,
                    use_color=renderer.interactive,
                )
                renderer.render(global_line)
            else:
                renderer.render_line(last_render)
        elif key == "speed":
            parsed_speed = parse_progress_speed(value)
            if parsed_speed is not None:
                current_speed = parsed_speed
            speed_for_render = display_speed()
            if total_duration and total_duration > 0 and current_seconds is not None:
                last_render = format_progress_line(current_seconds, total_duration, speed_for_render)
                if batch_progress is not None:
                    global_seconds = batch_progress.completed_seconds + current_seconds
                    global_line = format_batch_progress_line(
                        completed_seconds=global_seconds,
                        total_seconds=batch_progress.total_seconds,
                        completed_files=batch_progress.completed_files,
                        total_files=batch_progress.total_files,
                        current_file_number=current_file_number,
                        current_speed=speed_for_render,
                        use_color=renderer.interactive,
                    )
                    renderer.render(global_line)
                else:
                    renderer.render_line(last_render)
        elif key == "progress" and value == "end":
            break

    return_code = process.wait()
    if batch_progress is None and last_render:
        sys.stdout.write("\n")
        sys.stdout.flush()
    if return_code != 0:
        if batch_progress is not None:
            renderer.finish()
        raise RuntimeError(f"ffmpeg failed for {source}")


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
            audio_positions = resolve_folder_track_positions(
                media_infos,
                "audio_streams",
                "audio",
                consistent=audio_consistent,
            )
            subtitle_positions = resolve_folder_track_positions(
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
