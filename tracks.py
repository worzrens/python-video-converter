from __future__ import annotations

from media import MediaInfo, MediaStream


SUPPORTED_SUBTITLE_CODECS = {"subrip", "ass", "ssa", "webvtt", "mov_text", "text"}


def is_text_subtitle(codec_name: str | None) -> bool:
    return (codec_name or "").lower() in SUPPORTED_SUBTITLE_CODECS


def media_signature(streams: list[MediaStream]) -> list[tuple[str | None, str | None, str | None]]:
    return [(stream.codec_name, stream.language, stream.title) for stream in streams]


def track_key(stream: MediaStream) -> tuple[str | None, str | None, str | None]:
    def normalize(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split()).strip()
        return cleaned.casefold() if cleaned else None

    return normalize(stream.codec_name), normalize(stream.language), normalize(stream.title)


def validate_folder_consistency(media_infos: list[MediaInfo]) -> tuple[bool, bool]:
    if not media_infos:
        return True, True
    audio_signature = media_signature(media_infos[0].audio_streams)
    subtitle_signature = media_signature(media_infos[0].subtitle_streams)
    audio_consistent = True
    subtitle_consistent = True
    for media in media_infos[1:]:
        if audio_consistent and media_signature(media.audio_streams) != audio_signature:
            audio_consistent = False
        if subtitle_consistent and media_signature(media.subtitle_streams) != subtitle_signature:
            subtitle_consistent = False
    return audio_consistent, subtitle_consistent


def build_common_track_choices(media_infos: list[MediaInfo], stream_attr: str) -> list[tuple[MediaStream, list[int]]]:
    if not media_infos:
        return []

    per_file_maps: list[dict[tuple[str | None, str | None, str | None], int]] = []
    for media in media_infos:
        mapping: dict[tuple[str | None, str | None, str | None], int] = {}
        for position, stream in enumerate(getattr(media, stream_attr)):
            mapping.setdefault(track_key(stream), position)
        per_file_maps.append(mapping)

    common_keys = set(per_file_maps[0])
    for mapping in per_file_maps[1:]:
        common_keys &= set(mapping)

    choices: list[tuple[MediaStream, list[int]]] = []
    for stream in getattr(media_infos[0], stream_attr):
        key = track_key(stream)
        if key in common_keys:
            positions = [mapping[key] for mapping in per_file_maps]
            choices.append((stream, positions))
    return choices


def choose_menu_option(message: str, option_count: int, default_index: int = 0) -> int:
    while True:
        raw = input(f"{message} [1-{option_count}] [{default_index + 1}]: ").strip().lower()
        if not raw:
            return default_index
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= option_count:
                return choice - 1
        print("Invalid selection, try again.")


def format_common_track_positions(media_infos: list[MediaInfo], positions: list[int | None]) -> str:
    pieces = []
    for media, position in zip(media_infos, positions):
        if position is None:
            pieces.append(f"{media.path.name}:none")
        else:
            pieces.append(f"{media.path.name}:{position + 1}")
    return ", ".join(pieces)


def print_streams_for_selection(media: MediaInfo, stream_attr: str, label: str) -> None:
    print(f"{label.capitalize()} tracks for {media.path.name}:")
    streams = getattr(media, stream_attr)
    for index, stream in enumerate(streams, start=1):
        print(f"  {index}) {stream.label()}")


def choose_stream_position(streams: list[MediaStream], label: str, allow_none: bool = False) -> int | None:
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


def resolve_folder_track_positions(
    media_infos: list[MediaInfo],
    stream_attr: str,
    label: str,
    consistent: bool,
    allow_none: bool = False,
) -> list[int | None]:
    if not media_infos:
        return []

    if consistent:
        selected = choose_stream_position(getattr(media_infos[0], stream_attr), label, allow_none=allow_none)
        return [selected for _ in media_infos]

    mode = choose_menu_option(
        f"{label.capitalize()} tracks differ across files. Use common tracks for all files or select each video separately?",
        2,
        default_index=0,
    )

    if mode == 0:
        choices = build_common_track_choices(media_infos, stream_attr)
        if choices:
            print(f"Common {label} tracks:")
            for index, (stream, positions) in enumerate(choices, start=1):
                print(f"  {index}) {stream.label()} [{format_common_track_positions(media_infos, positions)}]")
            selected_index = choose_menu_option(f"Select common {label} track", len(choices), default_index=0)
            return choices[selected_index][1]
        print(f"No common {label} tracks found; selecting each video separately.")

    positions: list[int | None] = []
    for media in media_infos:
        print_streams_for_selection(media, stream_attr, label)
        positions.append(
            choose_stream_position(getattr(media, stream_attr), f"{label} track for {media.path.name}", allow_none=allow_none)
        )
    return positions


def resolve_folder_stream_positions(
    media_infos: list[MediaInfo],
    stream_attr: str,
    label: str,
    consistent: bool,
    allow_none: bool = False,
) -> list[int | None]:
    return resolve_folder_track_positions(media_infos, stream_attr, label, consistent, allow_none=allow_none)


def prompt_yes_no(message: str, default: bool = False) -> bool:
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


def prompt_target_height(default_height: int = 1080) -> int:
    while True:
        raw = input(f"Target height [{default_height}]: ").strip()
        if not raw:
            return default_height
        if raw.isdigit():
            height = int(raw)
            if height > 0:
                return height
        print("Please enter a positive whole number or leave blank.")
