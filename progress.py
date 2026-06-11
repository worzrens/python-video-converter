"""Progress parsing, smoothing, formatting, and terminal rendering helpers."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


DEFAULT_ESTIMATED_ENCODE_SPEED = 1.0
PROGRESS_STATS_PERIOD = "0.25"
SPEED_EMA_ALPHA = 0.024
SPEED_MAX_CHANGE_RATIO = 0.30
SPEED_SAMPLE_MIN_INTERVAL = 0.20
SPEED_SAMPLE_MIN_PROGRESS_SECONDS = 0.50


def format_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def estimate_conversion_time(duration_seconds: float | None, encode_speed: float | None = DEFAULT_ESTIMATED_ENCODE_SPEED) -> float | None:
    if duration_seconds is None or encode_speed is None or encode_speed <= 0:
        return None
    return duration_seconds / encode_speed


def estimate_total_duration(media_infos) -> float | None:
    durations = [media.duration_seconds for media in media_infos]
    if any(duration is None for duration in durations):
        return None
    return float(sum(duration for duration in durations if duration is not None))


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
