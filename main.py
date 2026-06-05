from __future__ import annotations

import json
import shutil
import subprocess
import sys
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


def build_output_path(source: Path, is_folder_mode: bool, output_root: Path | None) -> Path:
    """Build the destination path for a converted movie."""
    if is_folder_mode:
        if output_root is None:
            raise ValueError("output_root is required in folder mode")
        return _unique_path(output_root / f"{source.stem}.mp4")
    return _unique_path(source.with_name(f"{source.stem}-COMPRESSED.mp4"))


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


def parse_progress_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds = float(rest)
    return int(hours) * 3600 + int(minutes) * 60 + seconds


def render_progress_bar(percent: float, width: int = 28) -> str:
    percent = max(0.0, min(percent, 1.0))
    filled = int(round(width * percent))
    return f"[{('#' * filled).ljust(width, '-')}] {percent * 100:5.1f}%"


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
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a",
    ]

    if default_subtitle_position is not None:
        selected_subtitle = media.subtitle_streams[default_subtitle_position]
        if not is_text_subtitle(selected_subtitle.codec_name):
            raise ValueError(
                f"Selected subtitle track {default_subtitle_position + 1} uses {selected_subtitle.codec_name or 'unknown'} and cannot be embedded in MP4"
            )
        command.extend(["-map", f"0:s:{default_subtitle_position}", "-c:s", DEFAULT_SUBTITLE_CODEC])

    target_width = calculate_target_width(media, target_height)
    if target_width is not None:
        command.extend(["-vf", f"scale={target_width}:{target_height}"])

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

    print(f"\nAvailable {label} tracks:")
    for index, stream in enumerate(streams, start=1):
        print(f"  {index}) {stream.label()}")

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
) -> None:
    """Run ffmpeg to convert one source file into the requested output."""
    command = build_ffmpeg_command(source, output, media, audio_position, subtitle_position, target_height)
    command = command[:-1] + ["-progress", "pipe:1", "-nostats", command[-1]]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert process.stdout is not None
    total_duration = media.duration_seconds
    last_render = ""
    current_seconds = 0.0

    for raw_line in process.stdout:
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == "out_time":
            current_seconds = parse_progress_time(value)
            if total_duration and total_duration > 0:
                percent = current_seconds / total_duration
                remaining = max(0.0, total_duration - current_seconds)
                last_render = f"{render_progress_bar(percent)} ETA {format_seconds(remaining)}"
            else:
                last_render = f"Processed {format_seconds(current_seconds)}"
            sys.stdout.write(f"\r{last_render}")
            sys.stdout.flush()
        elif key == "progress" and value == "end":
            break

    return_code = process.wait()
    if last_render:
        sys.stdout.write("\n")
        sys.stdout.flush()
    if return_code != 0:
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
        print(f"Estimated conversion time: {format_seconds(estimated_duration)}")

        audio_position = choose_stream_position(media_infos[0].audio_streams, "audio")
        subtitle_position = choose_stream_position(media_infos[0].subtitle_streams, "subtitle", allow_none=True)

        if not prompt_yes_no("Proceed with conversion?", default=True):
            print("Cancelled.")
            return 0

        for media in media_infos:
            output = build_output_path(media.path, is_folder_mode, output_root)
            output.parent.mkdir(parents=True, exist_ok=True)
            convert_file(media.path, output, media, audio_position or 0, subtitle_position, target_height)
            print(f"Converted: {media.path.name} -> {output}")

        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
