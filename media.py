"""Media metadata parsing, file discovery, and output path helpers."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


VIDEO_EXTENSIONS = {".avi", ".mkv", ".mp4", ".mov", ".m4v", ".webm"}


@dataclass(frozen=True)
class MediaStream:
    index: int
    stream_type: str
    codec_name: str | None
    language: str | None
    title: str | None
    default: bool

    def label(self) -> str:
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
    suffix = f"_{output_dimensions[0]}x{output_dimensions[1]}.mp4"
    if is_folder_mode:
        if output_root is None:
            raise ValueError("output_root is required in folder mode")
        return _unique_path(output_root / f"{source.stem}{suffix}")
    return _unique_path(source.with_name(f"{source.stem}{suffix}"))


def _unique_path(path: Path) -> Path:
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


def format_media_summary(media: MediaInfo, include_tracks: bool = True) -> str:
    size = f"{media.size_bytes / (1024 * 1024):.2f} MB" if media.size_bytes else "unknown"
    resolution = f"{media.width}x{media.height}" if media.width and media.height else "unknown"
    lines = [
        f"File: {media.path}",
        f"Format: {media.format_name or 'unknown'}",
        f"Size: {size}",
        f"Resolution: {resolution}",
    ]
    if include_tracks:
        lines.append("Audio tracks:")
        for index, stream in enumerate(media.audio_streams, start=1):
            lines.append(f"  {index}) {stream.label()}")
        lines.append("Subtitle tracks:")
        if media.subtitle_streams:
            for index, stream in enumerate(media.subtitle_streams, start=1):
                lines.append(f"  {index}) {stream.label()}")
        else:
            lines.append("  none")
    return "\n".join(lines)
