from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


VIDEO_EXTENSIONS = {".avi", ".mkv", ".mp4", ".mov", ".m4v", ".webm"}
TARGET_HEIGHT = 1080
DEFAULT_VIDEO_CODEC = "libx264"
DEFAULT_VIDEO_CRF = "20"
DEFAULT_VIDEO_PRESET = "medium"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_AUDIO_BITRATE = "192k"
DEFAULT_SUBTITLE_CODEC = "mov_text"
SUPPORTED_SUBTITLE_CODECS = {"subrip", "ass", "ssa", "webvtt", "mov_text", "text"}
DEFAULT_ESTIMATED_ENCODE_SPEED = 1.0
PROGRESS_STATS_PERIOD = "0.25"
SPEED_EMA_ALPHA = 0.024
SPEED_MAX_CHANGE_RATIO = 0.30
SPEED_SAMPLE_MIN_INTERVAL = 0.20
SPEED_SAMPLE_MIN_PROGRESS_SECONDS = 0.50


@dataclass(frozen=True)
class MediaStream:
    index: int
    stream_type: str
    codec_name: str | None
    language: str | None
    title: str | None
    default: bool

    def label(self) -> str:
        """Return a human-readable label for the stream."""
        pieces = []
        if self.language:
            pieces.append(self.language)
        if self.title:
            pieces.append(self.title)
        if not pieces:
            pieces.append("unnamed")
        suffix = " [default]" if self.default else ""
        codec = f" ({self.codec_name})" if self.codec_name else ""
        return f"{' / '.join(pieces)}{codec}{suffix}"


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    format_name: str | None
    duration_seconds: float | None
    size_bytes: int | None
    width: int | None
    height: int | None
    audio_streams: list[MediaStream]
    subtitle_streams: list[MediaStream]
    frame_rate: float | None = None


def parse_frame_rate(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        try:
            num = float(numerator)
            den = float(denominator)
        except ValueError:
            return None
        if den == 0:
            return None
        rate = num / den
        return rate if rate > 0 else None
    try:
        rate = float(value)
    except ValueError:
        return None
    return rate if rate > 0 else None


def probe_media(path: Path) -> MediaInfo:
    """Read ffprobe metadata and normalize it into a MediaInfo object."""
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"ffprobe failed for {path}")

    payload = json.loads(completed.stdout)
    format_info = payload.get("format", {})
    streams = payload.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})

    return MediaInfo(
        path=path,
        format_name=format_info.get("format_name"),
        duration_seconds=float(format_info["duration"]) if format_info.get("duration") and format_info.get("duration") != "N/A" else None,
        size_bytes=int(format_info["size"]) if format_info.get("size") else None,
        width=video_stream.get("width"),
        height=video_stream.get("height"),
        audio_streams=[_parse_stream(stream, "audio") for stream in streams if stream.get("codec_type") == "audio"],
        subtitle_streams=[_parse_stream(stream, "subtitle") for stream in streams if stream.get("codec_type") == "subtitle"],
        frame_rate=parse_frame_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")),
    )


def _parse_stream(stream: dict, stream_type: str) -> MediaStream:
    """Convert a raw ffprobe stream dict into a MediaStream instance."""
    tags = stream.get("tags") or {}
    disposition = stream.get("disposition") or {}
    return MediaStream(
        index=int(stream["index"]),
        stream_type=stream_type,
        codec_name=stream.get("codec_name"),
        language=tags.get("language"),
        title=tags.get("title"),
        default=bool(disposition.get("default")),
    )


def discover_targets(input_path: Path) -> tuple[list[Path], bool, Path | None]:
    """Resolve the input path into movie files and output mode details."""
    if input_path.is_file():
        if input_path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {input_path.suffix}")
        return [input_path], False, None

    if input_path.is_dir():
        files = [
            child
            for child in sorted(input_path.iterdir())
            if child.is_file() and child.suffix.lower() in VIDEO_EXTENSIONS
        ]
        if not files:
            raise ValueError("No supported movie files found in folder")
        return files, True, input_path.with_name(f"{input_path.name}-COMPRESSED")

    raise FileNotFoundError(input_path)


def build_output_path(
    source: Path,
    is_folder_mode: bool,
    output_root: Path | None,
    output_dimensions: tuple[int, int],
) -> Path:
    """Build the destination path for a converted movie."""
    suffix = f"_{output_dimensions[0]}x{output_dimensions[1]}.mp4"
    if is_folder_mode:
        if output_root is None:
            raise ValueError("output_root is required in folder mode")
        return _unique_path(output_root / f"{source.stem}{suffix}")
    return _unique_path(source.with_name(f"{source.stem}{suffix}"))


def _unique_path(path: Path) -> Path:
    """Return a non-colliding path by appending a numeric suffix if needed."""
    if not path.exists():
        return path
    suffix = path.suffix
    stem = path.stem
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def media_signature(streams: list[MediaStream]) -> list[tuple[str | None, str | None, str | None]]:
    """Summarize stream identity fields for folder consistency checks."""
    return [(stream.codec_name, stream.language, stream.title) for stream in streams]


def calculate_target_width(media: MediaInfo, target_height: int) -> int | None:
    if not media.width or not media.height:
        raise ValueError(f"Missing source dimensions for {media.path}")
    if media.height <= target_height:
        return None
    width = round(target_height * (media.width / media.height))
    return max(2, (width // 2) * 2)


def calculate_output_dimensions(media: MediaInfo, target_height: int) -> tuple[int, int]:
    if not media.width or not media.height:
        raise ValueError(f"Missing source dimensions for {media.path}")
    target_width = calculate_target_width(media, target_height)
    if target_width is None:
        return media.width, media.height
    return target_width, target_height


def format_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def estimate_total_duration(media_infos: list[MediaInfo]) -> float | None:
    durations = [media.duration_seconds for media in media_infos]
    if any(duration is None for duration in durations):
        return None
    return float(sum(duration for duration in durations if duration is not None))


def estimate_conversion_time(duration_seconds: float | None, encode_speed: float | None = DEFAULT_ESTIMATED_ENCODE_SPEED) -> float | None:
    if duration_seconds is None or encode_speed is None or encode_speed <= 0:
        return None
    return duration_seconds / encode_speed


def parse_progress_time(
    value: str,
    key: str | None = None,
    total_duration: float | None = None,
    current_seconds: float | None = None,
) -> float | None:
    value = value.strip()
    if value in {"N/A", ""}:
        return None
    if ":" not in value:
        numeric = float(value)
        if key == "out_time_us":
            return numeric / 1_000_000
        if key == "out_time_ms":
            milliseconds_seconds = numeric / 1_000
            microseconds_seconds = numeric / 1_000_000
            if total_duration and total_duration > 0:
                upper_bound = max(total_duration * 1.5, 60.0)
                ms_plausible = 0 <= milliseconds_seconds <= upper_bound
                us_plausible = 0 <= microseconds_seconds <= upper_bound
                if ms_plausible and not us_plausible:
                    return milliseconds_seconds
                if us_plausible and not ms_plausible:
                    return microseconds_seconds
                if ms_plausible and us_plausible:
                    if current_seconds is not None:
                        forward_candidates = [
                            candidate
                            for candidate in (milliseconds_seconds, microseconds_seconds)
                            if candidate >= current_seconds - 0.5
                        ]
                        if forward_candidates:
                            return max(forward_candidates)
                    return max(milliseconds_seconds, microseconds_seconds)
            return microseconds_seconds if numeric >= 10_000_000 else milliseconds_seconds
        return numeric / 1_000_000
    hours, minutes, rest = value.split(":")
    seconds = float(rest)
    return int(hours) * 3600 + int(minutes) * 60 + seconds


def parse_progress_speed(value: str) -> float | None:
    cleaned = value.strip().rstrip("x")
    if cleaned in {"N/A", "0", "0.0", ""}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def smooth_metric(previous: float | None, value: float | None, alpha: float) -> float | None:
    if value is None:
        return previous
    if previous is None:
        return value
    return previous + alpha * (value - previous)


def clamp_relative_change(previous: float | None, value: float, max_change_ratio: float = SPEED_MAX_CHANGE_RATIO) -> float:
    if previous is None or previous <= 0:
        return value
    lower = previous * (1.0 - max_change_ratio)
    upper = previous * (1.0 + max_change_ratio)
    return max(lower, min(upper, value))


def render_progress_bar(percent: float, width: int = 28, use_color: bool = False) -> str:
    percent = max(0.0, min(percent, 1.0))
    filled = int(round(width * percent))
    bar = f"[{('█' * filled).ljust(width, '░')}] {percent * 100:5.1f}%"
    return f"\033[32m{bar}\033[0m" if use_color else bar


def format_speed(speed: float | None) -> str:
    if speed is None or speed <= 0:
        return "unknown"
    return f"{speed:.2f}x"


def format_progress_line(current_seconds: float, total_duration: float | None, speed: float | None) -> str:
    if total_duration is None or total_duration <= 0:
        return f"Processed {format_seconds(current_seconds)} speed {format_speed(speed)}"

    percent = current_seconds / total_duration
    remaining = max(0.0, total_duration - current_seconds)
    eta_seconds = remaining / speed if speed and speed > 0 else remaining
    return (
        f"{render_progress_bar(percent)} | "
        f"Converted {format_seconds(current_seconds)} / {format_seconds(total_duration)} | "
        f"speed {format_speed(speed)} ETA {format_seconds(eta_seconds)}"
    )


def format_batch_progress_line(
    completed_seconds: float,
    total_seconds: float | None,
    completed_files: int,
    total_files: int,
    current_file_number: int | None,
    current_speed: float | None,
    use_color: bool = False,
) -> str:
    file_display = current_file_number if current_file_number is not None else completed_files
    if total_seconds is None or total_seconds <= 0:
        return (
            f"files {file_display}/{total_files} | "
            f"{render_progress_bar(0.0, use_color=use_color)} | "
            f"Global Converted {format_seconds(completed_seconds)} | "
            f"speed {format_speed(current_speed)} ETA unknown"
        )

    percent = completed_seconds / total_seconds
    remaining = max(0.0, total_seconds - completed_seconds)
    eta_seconds = remaining / current_speed if current_speed and current_speed > 0 else remaining
    return (
        f"files {file_display}/{total_files} | "
        f"{render_progress_bar(percent, use_color=use_color)} | "
        f"Global Converted {format_seconds(completed_seconds)} / {format_seconds(total_seconds)} | "
        f"speed {format_speed(current_speed)} ETA {format_seconds(eta_seconds)}"
    )


@dataclass
class BatchProgressState:
    total_files: int
    completed_files: int
    total_seconds: float
    completed_seconds: float = 0.0


class ProgressRenderer:
    def __init__(self, interactive: bool | None = None):
        if interactive is not None:
            self.interactive = interactive
        else:
            plain_env = os.getenv("FFCONV_PLAIN_PROGRESS", "").strip().lower()
            self.interactive = plain_env not in {"1", "true", "yes", "on"}
        self.initialized = False
        self.last_length = 0

    def render(self, line: str) -> None:
        self.render_line(line)

    def render_line(self, line: str) -> None:
        if self.interactive:
            padding = max(0, self.last_length - len(line))
            sys.stdout.write(f"\r{line}{' ' * padding}")
            self.initialized = True
            self.last_length = len(line)
        else:
            sys.stdout.write(f"{line}\n")
        sys.stdout.flush()

    def finish(self) -> None:
        if self.interactive and self.initialized:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self.last_length = 0


def is_text_subtitle(codec_name: str | None) -> bool:
    return (codec_name or "").lower() in SUPPORTED_SUBTITLE_CODECS


def validate_folder_consistency(media_infos: list[MediaInfo]) -> None:
    """Ensure every file in a folder has matching audio and subtitle layouts."""
    if not media_infos:
        return
    audio_signature = media_signature(media_infos[0].audio_streams)
    subtitle_signature = media_signature(media_infos[0].subtitle_streams)
    for media in media_infos[1:]:
        if media_signature(media.audio_streams) != audio_signature:
            raise ValueError(f"Audio tracks differ for {media.path.name}")
        if media_signature(media.subtitle_streams) != subtitle_signature:
            raise ValueError(f"Subtitle tracks differ for {media.path.name}")


def build_ffmpeg_command(
    source: Path,
    output: Path,
    media: MediaInfo,
    default_audio_position: int,
    default_subtitle_position: int | None,
    target_height: int,
) -> list[str]:
    """Assemble the ffmpeg command used to convert one movie."""
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


def format_media_summary(media: MediaInfo) -> str:
    """Format the discovered metadata for display to the user."""
    size = f"{media.size_bytes / (1024 * 1024):.2f} MB" if media.size_bytes else "unknown"
    resolution = f"{media.width}x{media.height}" if media.width and media.height else "unknown"
    lines = [
        f"File: {media.path}",
        f"Format: {media.format_name or 'unknown'}",
        f"Size: {size}",
        f"Resolution: {resolution}",
        "Audio tracks:",
    ]
    for index, stream in enumerate(media.audio_streams, start=1):
        lines.append(f"  {index}) {stream.label()}")
    lines.append("Subtitle tracks:")
    if media.subtitle_streams:
        for index, stream in enumerate(media.subtitle_streams, start=1):
            lines.append(f"  {index}) {stream.label()}")
    else:
        lines.append("  none")
    return "\n".join(lines)


def choose_stream_position(streams: list[MediaStream], label: str, allow_none: bool = False) -> int | None:
    """Prompt the user to pick a stream position from a list."""
    if not streams:
        if allow_none:
            return None
        raise ValueError(f"No {label} tracks found")

    while True:
        raw = input(f"Select default {label} track [1-{len(streams)}]{' or none' if allow_none else ''}: ").strip().lower()
        if allow_none and raw in {"none", "n", ""}:
            return None
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(streams):
                return choice - 1
        print("Invalid selection, try again.")


def prompt_yes_no(message: str, default: bool = False) -> bool:
    """Ask the user a yes/no question and return the selected answer."""
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        raw = input(f"{message} {suffix} ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def prompt_target_height(default_height: int = TARGET_HEIGHT) -> int:
    while True:
        raw = input(f"Target height [{default_height}]: ").strip()
        if not raw:
            return default_height
        if raw.isdigit():
            height = int(raw)
            if height > 0:
                return height
        print("Please enter a positive whole number or leave blank.")


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
    """Run ffmpeg to convert one source file into the requested output."""
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
            if delta_wall >= SPEED_SAMPLE_MIN_INTERVAL and delta_seconds >= SPEED_SAMPLE_MIN_PROGRESS_SECONDS:
                estimated_speed = delta_seconds / delta_wall
        last_speed_sample_seconds = current_seconds
        last_speed_sample_at = now

    def display_speed() -> float | None:
        nonlocal displayed_speed
        raw_speed = current_speed if current_speed is not None and current_speed > 0 else estimated_speed
        if raw_speed is None or raw_speed <= 0:
            return displayed_speed
        bounded_speed = clamp_relative_change(displayed_speed, raw_speed)
        displayed_speed = smooth_metric(displayed_speed, bounded_speed, SPEED_EMA_ALPHA)
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
    """Run the interactive CLI entrypoint for the converter."""
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
        print(format_media_summary(media_infos[0]))
        if is_folder_mode:
            validate_folder_consistency(media_infos)
            print(f"\nFolder contains {len(media_infos)} compatible movie files.")
        else:
            print("\nSingle-file mode.")

        target_height = prompt_target_height()
        estimated_duration = estimate_total_duration(media_infos)
        estimated_time = estimate_conversion_time(estimated_duration)
        print(f"Estimated conversion time (starting at {DEFAULT_ESTIMATED_ENCODE_SPEED:.1f}x): {format_seconds(estimated_time)}")

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
