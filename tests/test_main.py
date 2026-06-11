import io
import json
import os
import subprocess
import tempfile
import unittest
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import conversion
import main
import media
import progress
import tracks


class ProbeMediaTests(unittest.TestCase):
    def test_probe_media_parses_streams(self):
        payload = {
            "format": {"format_name": "matroska,webm", "size": "123456", "duration": "12.5"},
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 3840,
                    "height": 2160,
                    "avg_frame_rate": "24000/1001",
                },
                {
                    "index": 1,
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "tags": {"language": "eng", "title": "Stereo"},
                    "disposition": {"default": 1},
                },
                {
                    "index": 2,
                    "codec_type": "subtitle",
                    "codec_name": "subrip",
                    "tags": {"language": "eng", "title": "English"},
                    "disposition": {"default": 0},
                },
            ],
        }

        completed = type("Completed", (), {"returncode": 0, "stdout": json.dumps(payload), "stderr": ""})()
        with patch("subprocess.run", return_value=completed) as run:
            info = media.probe_media(Path("/tmp/movie.mkv"))

        self.assertEqual(info.format_name, "matroska,webm")
        self.assertEqual(info.duration_seconds, 12.5)
        self.assertEqual(info.size_bytes, 123456)
        self.assertEqual(info.width, 3840)
        self.assertEqual(info.height, 2160)
        self.assertAlmostEqual(info.frame_rate or 0.0, 24000 / 1001, places=3)
        self.assertEqual(info.audio_streams[0].language, "eng")
        self.assertEqual(info.subtitle_streams[0].title, "English")
        run.assert_called_once()


    def test_probe_media_repairs_cyrillic_mojibake_titles(self):
        payload = {
            "format": {"format_name": "matroska,webm", "size": "123456", "duration": "12.5"},
            "streams": [
                {
                    "index": 0,
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "tags": {"language": "rus", "title": "РќРµРІР°С„РёР»СЊРј"},
                    "disposition": {"default": 1},
                },
                {
                    "index": 1,
                    "codec_type": "subtitle",
                    "codec_name": "subrip",
                    "tags": {"language": "rus", "title": "РќРµРІР°С„РёР»СЊРј"},
                    "disposition": {"default": 0},
                },
            ],
        }

        completed = type("Completed", (), {"returncode": 0, "stdout": json.dumps(payload), "stderr": ""})()
        with patch("subprocess.run", return_value=completed):
            info = media.probe_media(Path("/tmp/movie.mkv"))

        self.assertEqual(info.audio_streams[0].title, "Невафильм")
        self.assertEqual(info.subtitle_streams[0].title, "Невафильм")
        self.assertEqual(info.audio_streams[0].language, "rus")


class PathAndNamingTests(unittest.TestCase):
    def test_output_path_for_single_file_uses_resolution_suffix(self):
        result = media.build_output_path(
            Path("/movies/film.avi"),
            is_folder_mode=False,
            output_root=None,
            output_dimensions=(1920, 1080),
        )
        self.assertEqual(result, Path("/movies/film_1920x1080.mp4"))

    def test_output_path_for_folder_mode_uses_sibling_directory(self):
        result = media.build_output_path(
            Path("/movies/film.avi"),
            is_folder_mode=True,
            output_root=Path("/movies/collection-COMPRESSED"),
            output_dimensions=(1920, 1080),
        )
        self.assertEqual(result, Path("/movies/collection-COMPRESSED/film_1920x1080.mp4"))


class AssetProbeTests(unittest.TestCase):
    def _copy_asset(self) -> Path:
        asset = Path(__file__).with_name("Severance.S01E01.1080.2min_copy.mkv")
        self.assertTrue(asset.exists())
        if asset.stat().st_size == 0:
            self.skipTest("copy fixture is empty in this checkout")
        return asset

    def test_two_minute_cut_asset_can_be_probed(self):
        asset = Path(__file__).with_name("Severance.S01E01.1080.2min.mkv")
        self.assertTrue(asset.exists())

        info = media.probe_media(asset)
        self.assertEqual(info.width, 1920)
        self.assertEqual(info.height, 1080)
        self.assertGreaterEqual(info.duration_seconds or 0, 119.0)
        self.assertLessEqual(info.duration_seconds or 0, 121.0)

    def test_folder_summary_can_omit_tracks(self):
        asset = Path(__file__).with_name("Severance.S01E01.1080.2min.mkv")
        info = media.probe_media(asset)

        summary = media.format_media_summary(info, include_tracks=False)
        self.assertIn("File:", summary)
        self.assertIn("Format:", summary)
        self.assertNotIn("Audio tracks:", summary)
        self.assertNotIn("Subtitle tracks:", summary)

    def test_copy_asset_has_reordered_default_tracks(self):
        asset = self._copy_asset()

        info = media.probe_media(asset)
        self.assertEqual(info.audio_streams[0].title, "DTS-HD MA 5.1")
        self.assertEqual(info.subtitle_streams[0].title, "SDH")
        self.assertTrue(info.audio_streams[0].default)
        self.assertTrue(info.subtitle_streams[0].default)

    def test_real_assets_resolve_common_tracks_independent_of_order(self):
        base_asset = Path(__file__).with_name("Severance.S01E01.1080.2min.mkv")
        copy_asset = self._copy_asset()

        base = media.probe_media(base_asset)
        copy = media.probe_media(copy_asset)

        with patch("builtins.input", side_effect=["", "1"]):
            audio_positions = tracks.resolve_folder_stream_positions([base, copy], "audio_streams", "audio", consistent=False)

        with patch("builtins.input", side_effect=["", "1"]):
            subtitle_positions = tracks.resolve_folder_stream_positions([base, copy], "subtitle_streams", "subtitle", consistent=False, allow_none=True)

        self.assertEqual(audio_positions, [0, 6])
        self.assertEqual(subtitle_positions, [0, 3])

    def test_per_file_selection_prints_track_list_before_each_prompt(self):
        base_asset = Path(__file__).with_name("Severance.S01E01.1080.2min.mkv")
        copy_asset = self._copy_asset()

        base = media.probe_media(base_asset)
        copy = media.probe_media(copy_asset)

        fake_stdout = io.StringIO()
        responses = iter(["2", "1", "2"])

        def fake_input(prompt: str = "") -> str:
            print(prompt, end="")
            return next(responses)

        with patch("builtins.input", new=fake_input), patch.object(sys, "stdout", new=fake_stdout):
            positions = tracks.resolve_folder_stream_positions([base, copy], "subtitle_streams", "subtitle", consistent=False, allow_none=True)

        output = fake_stdout.getvalue()
        self.assertEqual(positions, [0, 1])
        self.assertIn("Subtitle tracks for Severance.S01E01.1080.2min.mkv:", output)
        self.assertIn("Subtitle tracks for Severance.S01E01.1080.2min_copy.mkv:", output)
        self.assertLess(output.index("Subtitle tracks for Severance.S01E01.1080.2min.mkv:"), output.index("Select default subtitle track for Severance.S01E01.1080.2min.mkv"))
        self.assertLess(output.index("Subtitle tracks for Severance.S01E01.1080.2min_copy.mkv:"), output.index("Select default subtitle track for Severance.S01E01.1080.2min_copy.mkv"))


class ConsistencyAndCommandTests(unittest.TestCase):
    def test_prompt_yes_no_defaults_to_yes_on_blank(self):
        with patch("builtins.input", side_effect=[""]):
            self.assertTrue(tracks.prompt_yes_no("Proceed with conversion?", default=True))

    def test_format_seconds_and_estimate_total_duration(self):
        self.assertEqual(progress.format_seconds(None), "unknown")
        self.assertEqual(progress.format_seconds(65), "01:05")
        self.assertAlmostEqual(media.parse_frame_rate("24000/1001") or 0.0, 24000 / 1001, places=3)
        self.assertEqual(media.parse_frame_rate("30"), 30.0)
        self.assertIsNone(media.parse_frame_rate("0/0"))
        self.assertIsNone(media.parse_frame_rate("N/A"))
        self.assertEqual(progress.parse_progress_time("2500000"), 2.5)
        self.assertEqual(progress.parse_progress_time("00:00:02.50"), 2.5)
        self.assertEqual(
            progress.parse_progress_time("2500", key="out_time_ms", total_duration=120.0, current_seconds=2.0),
            2.5,
        )
        self.assertEqual(
            progress.parse_progress_time("2500000", key="out_time_ms", total_duration=120.0, current_seconds=2.0),
            2.5,
        )
        self.assertEqual(progress.parse_progress_time("2500000", key="out_time_us"), 2.5)
        self.assertIsNone(progress.parse_progress_time("N/A"))
        self.assertEqual(progress.parse_progress_speed("1.5x"), 1.5)
        self.assertEqual(progress.parse_progress_speed(" 1.5x"), 1.5)
        self.assertIsNone(progress.parse_progress_speed("N/A"))
        self.assertAlmostEqual(progress.smooth_metric(2.0, 4.0, 0.25) or 0.0, 2.5)
        self.assertEqual(progress.smooth_metric(None, 3.0, 0.25), 3.0)
        self.assertEqual(progress.clamp_relative_change(2.0, 4.0, max_change_ratio=0.25), 2.5)
        self.assertEqual(progress.clamp_relative_change(2.0, 1.0, max_change_ratio=0.25), 1.5)

        infos = [
            media.MediaInfo(Path("a.mkv"), "matroska", 10.0, 1, 1, 1, [], []),
            media.MediaInfo(Path("b.mkv"), "matroska", 20.0, 1, 1, 1, [], []),
        ]
        self.assertEqual(progress.estimate_total_duration(infos), 30.0)
        self.assertEqual(progress.estimate_conversion_time(30.0, 2.0), 15.0)

    def test_format_batch_progress_line_shows_global_progress(self):
        line = progress.format_batch_progress_line(
            completed_seconds=120.0,
            total_seconds=300.0,
            completed_files=0,
            total_files=3,
            current_file_number=1,
            current_speed=2.0,
            use_color=True,
        )

        self.assertIn("\x1b[32m", line)
        self.assertTrue(line.startswith("files 1/3 | \x1b[32m["))
        self.assertIn("Converted 02:00 / 05:00", line)
        self.assertIn("ETA 01:30", line)
        self.assertIn("Global Converted 02:00 / 05:00", line)

    def test_choose_stream_position_does_not_repeat_track_list(self):
        streams = [
            media.MediaStream(1, "audio", "aac", "eng", "Stereo", True),
            media.MediaStream(2, "audio", "aac", "jpn", "Japanese", False),
        ]

        with patch("builtins.input", side_effect=["1"]), patch.object(sys, "stdout", new=io.StringIO()) as fake_stdout:
            self.assertEqual(tracks.choose_stream_position(streams, "audio"), 0)

        output = fake_stdout.getvalue()
        self.assertNotIn("Available audio tracks", output)
        self.assertNotIn("  1)", output)

    def test_prompt_target_height_defaults_when_blank(self):
        with patch("builtins.input", side_effect=[""]):
            self.assertEqual(tracks.prompt_target_height(), 1080)

    def test_prompt_target_height_accepts_custom_value(self):
        with patch("builtins.input", side_effect=["720"]):
            self.assertEqual(tracks.prompt_target_height(), 720)

    def test_calculate_target_width_only_downscales_above_target_height(self):
        small = media.MediaInfo(
            path=Path("small.mkv"),
            format_name="matroska",
            duration_seconds=10.0,
            size_bytes=1,
            width=640,
            height=480,
            audio_streams=[],
            subtitle_streams=[],
        )
        large = media.MediaInfo(
            path=Path("large.mkv"),
            format_name="matroska",
            duration_seconds=20.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[],
            subtitle_streams=[],
        )

        self.assertIsNone(media.calculate_target_width(small, 1080))
        self.assertEqual(media.calculate_target_width(large, 1080), 1920)
        self.assertEqual(media.calculate_target_width(large, 720), 1280)

    def test_validate_folder_consistency_reports_audio_and_subtitle_independently(self):
        first = media.MediaInfo(
            path=Path("one.mkv"),
            format_name="matroska",
            duration_seconds=10.0,
            size_bytes=1,
            width=1920,
            height=1080,
            audio_streams=[media.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[media.MediaStream(2, "subtitle", "subrip", "eng", "English", False)],
        )
        second = media.MediaInfo(
            path=Path("two.mkv"),
            format_name="matroska",
            duration_seconds=10.0,
            size_bytes=1,
            width=1920,
            height=1080,
            audio_streams=[media.MediaStream(1, "audio", "ac3", "eng", "Stereo", True)],
            subtitle_streams=[media.MediaStream(2, "subtitle", "subrip", "eng", "English", False)],
        )

        audio_consistent, subtitle_consistent = tracks.validate_folder_consistency([first, second])
        self.assertFalse(audio_consistent)
        self.assertTrue(subtitle_consistent)

    def test_resolve_folder_stream_positions_can_use_common_tracks(self):
        first = media.MediaInfo(
            path=Path("one.mkv"),
            format_name="matroska",
            duration_seconds=10.0,
            size_bytes=1,
            width=1920,
            height=1080,
            audio_streams=[
                media.MediaStream(1, "audio", "aac", "eng", "Stereo", True),
                media.MediaStream(2, "audio", "aac", "jpn", "Japanese", False),
            ],
            subtitle_streams=[],
        )
        second = media.MediaInfo(
            path=Path("two.mkv"),
            format_name="matroska",
            duration_seconds=10.0,
            size_bytes=1,
            width=1920,
            height=1080,
            audio_streams=[
                media.MediaStream(2, "audio", "aac", "jpn", "Japanese", False),
                media.MediaStream(1, "audio", "aac", "eng", "Stereo", True),
            ],
            subtitle_streams=[],
        )

        with patch("builtins.input", side_effect=["", "1"]):
            positions = tracks.resolve_folder_stream_positions([first, second], "audio_streams", "audio", consistent=False)

        self.assertEqual(positions, [0, 1])

    def test_resolve_folder_stream_positions_can_select_each_file_separately(self):
        first = media.MediaInfo(
            path=Path("one.mkv"),
            format_name="matroska",
            duration_seconds=10.0,
            size_bytes=1,
            width=1920,
            height=1080,
            audio_streams=[],
            subtitle_streams=[
                media.MediaStream(1, "subtitle", "subrip", "eng", "English", False),
                media.MediaStream(2, "subtitle", "subrip", "jpn", "Japanese", False),
            ],
        )
        second = media.MediaInfo(
            path=Path("two.mkv"),
            format_name="matroska",
            duration_seconds=10.0,
            size_bytes=1,
            width=1920,
            height=1080,
            audio_streams=[],
            subtitle_streams=[
                media.MediaStream(2, "subtitle", "subrip", "jpn", "Japanese", False),
                media.MediaStream(1, "subtitle", "subrip", "eng", "English", False),
            ],
        )

        with patch("builtins.input", side_effect=["2", "2", "1"]):
            positions = tracks.resolve_folder_stream_positions([first, second], "subtitle_streams", "subtitle", consistent=False, allow_none=True)

        self.assertEqual(positions, [1, 0])

    def test_build_ffmpeg_command_sets_scale_and_default_tracks(self):
        info = media.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=30.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[
                media.MediaStream(1, "audio", "aac", "eng", "Stereo", True),
                media.MediaStream(2, "audio", "aac", "jpn", "Japanese", False),
            ],
            subtitle_streams=[media.MediaStream(3, "subtitle", "subrip", "eng", "English", False)],
        )
        command = conversion.build_ffmpeg_command(
            source=Path("movie.mkv"),
            output=Path("movie-COMPRESSED.mp4"),
            media=info,
            default_audio_position=1,
            default_subtitle_position=0,
            target_height=1080,
        )

        joined = " ".join(command)
        self.assertIn("scale=1920:1080", joined)
        self.assertIn("-map 0:s:0", joined)
        self.assertIn("-c:s mov_text", joined)
        self.assertIn("-disposition:a:0 0", joined)
        self.assertIn("-disposition:a:1 default", joined)
        self.assertIn("-disposition:s:0 default", joined)
        self.assertIn("-stats_period", joined)

    def test_build_ffmpeg_command_skips_scaling_for_1080p_or_lower(self):
        info = media.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=30.0,
            size_bytes=1,
            width=640,
            height=480,
            audio_streams=[media.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[],
        )
        command = conversion.build_ffmpeg_command(
            source=Path("movie.mkv"),
            output=Path("movie-COMPRESSED.mp4"),
            media=info,
            default_audio_position=0,
            default_subtitle_position=None,
            target_height=1080,
        )

        self.assertNotIn("-vf", command)

    def test_build_ffmpeg_command_uses_copy_when_source_is_already_low_res_and_streams_are_compatible(self):
        info = media.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=30.0,
            size_bytes=1,
            width=1280,
            height=720,
            audio_streams=[media.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[media.MediaStream(2, "subtitle", "subrip", "eng", "English", False)],
        )
        command = conversion.build_ffmpeg_command(
            source=Path("movie.mkv"),
            output=Path("movie-COMPRESSED.mp4"),
            media=info,
            default_audio_position=0,
            default_subtitle_position=0,
            target_height=1080,
        )

        joined = " ".join(command)
        self.assertIn("-c:v copy", joined)
        self.assertIn("-c:a copy", joined)
        self.assertNotIn("-vf", joined)

    def test_build_ffmpeg_command_uses_custom_target_height(self):
        info = media.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=30.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[media.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[],
        )
        command = conversion.build_ffmpeg_command(
            source=Path("movie.mkv"),
            output=Path("movie-COMPRESSED.mp4"),
            media=info,
            default_audio_position=0,
            default_subtitle_position=None,
            target_height=720,
        )

        self.assertIn("scale=1280:720", " ".join(command))

    def test_build_ffmpeg_command_rejects_bitmap_subtitles(self):
        info = media.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=30.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[media.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[media.MediaStream(2, "subtitle", "hdmv_pgs_subtitle", "eng", "PGS", False)],
        )

        with self.assertRaises(ValueError):
            conversion.build_ffmpeg_command(
                source=Path("movie.mkv"),
                output=Path("movie-COMPRESSED.mp4"),
                media=info,
                default_audio_position=0,
                default_subtitle_position=0,
                target_height=1080,
            )

    def test_convert_file_writes_batch_progress_output(self):
        info = media.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=20.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[media.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[],
        )

        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO(
                    "out_time_ms=10000000\nspeed=2.0x\nprogress=continue\nout_time_ms=20000000\nspeed=2.0x\nprogress=end\n"
                )

            def wait(self):
                return 0

        with patch("subprocess.Popen", return_value=FakeProcess()), patch.object(sys, "stdout", new=io.StringIO()) as fake_stdout:
            conversion.convert_file(
                source=Path("movie.mkv"),
                output=Path("movie-COMPRESSED.mp4"),
                media=info,
                audio_position=0,
                subtitle_position=None,
                target_height=1080,
                batch_progress=progress.BatchProgressState(total_files=2, completed_files=1, total_seconds=40.0, completed_seconds=10.0),
                current_file_number=1,
            )

        output = fake_stdout.getvalue()
        self.assertIn("ETA", output)
        self.assertIn("ETA 00:05", output)
        self.assertIn("files 1/2", output)
        self.assertIn("speed 2.00x", output)

    def test_convert_file_does_not_finish_shared_batch_renderer(self):
        info = media.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=20.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[media.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[],
        )

        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO("out_time_ms=10000000\nspeed=2.0x\nprogress=end\n")

            def wait(self):
                return 0

        class SpyRenderer:
            def __init__(self):
                self.interactive = True
                self.lines: list[str] = []
                self.finish_calls = 0

            def render(self, line: str) -> None:
                self.lines.append(line)

            def render_line(self, line: str) -> None:
                self.lines.append(line)

            def finish(self) -> None:
                self.finish_calls += 1

        renderer = SpyRenderer()
        with patch("subprocess.Popen", return_value=FakeProcess()), patch("conversion.time.monotonic", side_effect=[0.0, 0.25, 0.5, 0.75, 1.0]):
            conversion.convert_file(
                source=Path("movie.mkv"),
                output=Path("movie-COMPRESSED.mp4"),
                media=info,
                audio_position=0,
                subtitle_position=None,
                target_height=1080,
                batch_progress=progress.BatchProgressState(total_files=2, completed_files=0, total_seconds=40.0, completed_seconds=0.0),
                renderer=renderer,
                current_file_number=1,
            )

        self.assertGreater(len(renderer.lines), 0)
        self.assertEqual(renderer.finish_calls, 0)

    def test_convert_file_uses_line_buffered_progress_stream(self):
        info = media.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=20.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[media.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[],
        )

        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO("out_time_ms=10000000\nprogress=end\n")

            def wait(self):
                return 0

        with patch("subprocess.Popen", return_value=FakeProcess()) as popen:
            conversion.convert_file(
                source=Path("movie.mkv"),
                output=Path("movie-COMPRESSED.mp4"),
                media=info,
                audio_position=0,
                subtitle_position=None,
                target_height=1080,
            )

        self.assertEqual(popen.call_args.kwargs.get("bufsize"), 1)

    def test_progress_renderer_defaults_to_interactive_without_plain_env(self):
        with patch.dict(os.environ, {}, clear=True):
            renderer = progress.ProgressRenderer()

        self.assertTrue(renderer.interactive)

    def test_progress_renderer_can_be_forced_to_plain_mode_by_env(self):
        with patch.dict(os.environ, {"FFCONV_PLAIN_PROGRESS": "1"}, clear=True):
            renderer = progress.ProgressRenderer()

        self.assertFalse(renderer.interactive)

    def test_convert_file_writes_incremental_lines_in_non_interactive_mode(self):
        info = media.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=20.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[media.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[],
        )

        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO(
                    "out_time_ms=2000000\n"
                    "speed=1.0x\n"
                    "out_time_ms=4000000\n"
                    "speed=1.5x\n"
                    "out_time_ms=6000000\n"
                    "speed=2.0x\n"
                    "progress=end\n"
                )

            def wait(self):
                return 0

        class FakeStdout(io.StringIO):
            def isatty(self):
                return False

        fake_stdout = FakeStdout()
        with patch("subprocess.Popen", return_value=FakeProcess()), patch.object(sys, "stdout", new=fake_stdout):
            conversion.convert_file(
                source=Path("movie.mkv"),
                output=Path("movie-COMPRESSED.mp4"),
                media=info,
                audio_position=0,
                subtitle_position=None,
                target_height=1080,
                batch_progress=progress.BatchProgressState(total_files=2, completed_files=0, total_seconds=40.0, completed_seconds=0.0),
                current_file_number=1,
            )

        lines = [line for line in fake_stdout.getvalue().splitlines() if line.strip()]
        progress_lines = [line for line in lines if line.startswith("files 1/2 |")]
        self.assertGreaterEqual(len(progress_lines), 3)

    def test_convert_file_uses_frame_fallback_when_out_time_is_na(self):
        info = media.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=20.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[media.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[],
            frame_rate=20.0,
        )

        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO(
                    "frame=20\nout_time=N/A\nprogress=continue\n"
                    "frame=100\nout_time=N/A\nprogress=continue\n"
                    "frame=200\nout_time=N/A\nprogress=end\n"
                )

            def wait(self):
                return 0

        class SpyRenderer:
            def __init__(self):
                self.interactive = False
                self.lines: list[str] = []

            def render(self, line: str) -> None:
                self.lines.append(line)

            def render_line(self, line: str) -> None:
                self.lines.append(line)

            def finish(self) -> None:
                return None

        renderer = SpyRenderer()
        with patch("subprocess.Popen", return_value=FakeProcess()), patch("conversion.time.monotonic", side_effect=[0.0, 0.25, 0.5, 0.75, 1.0]):
            conversion.convert_file(
                source=Path("movie.mkv"),
                output=Path("movie-COMPRESSED.mp4"),
                media=info,
                audio_position=0,
                subtitle_position=None,
                target_height=1080,
                batch_progress=progress.BatchProgressState(total_files=2, completed_files=0, total_seconds=40.0, completed_seconds=0.0),
                renderer=renderer,
                current_file_number=1,
            )

        self.assertGreaterEqual(len(renderer.lines), 2)
        self.assertTrue(any("files 1/2" in line for line in renderer.lines))
        self.assertTrue(any("25.0%" in line or " 50.0%" in line for line in renderer.lines))

    def test_convert_file_derives_speed_when_ffmpeg_reports_na(self):
        info = media.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=20.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[media.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[],
            frame_rate=20.0,
        )

        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO(
                    "frame=20\nout_time=N/A\nspeed=N/A\nprogress=continue\n"
                    "frame=100\nout_time=N/A\nspeed=N/A\nprogress=end\n"
                )

            def wait(self):
                return 0

        class SpyRenderer:
            def __init__(self):
                self.interactive = True
                self.lines: list[str] = []

            def render(self, line: str) -> None:
                self.lines.append(line)

            def render_line(self, line: str) -> None:
                self.lines.append(line)

            def finish(self) -> None:
                return None

        renderer = SpyRenderer()
        with patch("subprocess.Popen", return_value=FakeProcess()), patch("conversion.time.monotonic", side_effect=[0.0, 0.25, 0.5, 0.75, 1.0]):
            conversion.convert_file(
                source=Path("movie.mkv"),
                output=Path("movie-COMPRESSED.mp4"),
                media=info,
                audio_position=0,
                subtitle_position=None,
                target_height=1080,
                batch_progress=progress.BatchProgressState(total_files=2, completed_files=0, total_seconds=40.0, completed_seconds=0.0),
                renderer=renderer,
                current_file_number=1,
            )

        self.assertTrue(any("speed unknown" not in line for line in renderer.lines))


class MainFlowTests(unittest.TestCase):
    def test_main_exits_when_cli_dependencies_missing(self):
        with patch("main.shutil.which", return_value=None):
            self.assertEqual(main.main(), 1)

    def test_main_orchestrates_happy_path(self):
        media_info = SimpleNamespace(
            path=Path("/tmp/movie.mkv"),
            duration_seconds=12.5,
            audio_streams=[],
            subtitle_streams=[],
        )
        batch_progress = SimpleNamespace(
            total_files=1,
            total_seconds=12.5,
            completed_files=0,
            completed_seconds=0.0,
        )

        with patch("main._ensure_cli_dependencies", return_value=True), patch(
            "main._prompt_input_path", return_value=Path("/tmp/movie.mkv")
        ), patch("main.discover_targets", return_value=([Path("/tmp/movie.mkv")], False, None)), patch(
            "main.probe_media", return_value=media_info
        ) as probe_media, patch("main._print_media_overview", return_value=(True, True)) as print_overview, patch(
            "main.prompt_target_height", return_value=720
        ) as prompt_height, patch("main._prepare_batch_progress", return_value=batch_progress) as prepare_progress, patch(
            "main._select_stream_positions", return_value=(None, None, 0, None)
        ) as select_positions, patch("main.ProgressRenderer") as renderer_cls, patch(
            "main.prompt_yes_no", return_value=True
        ) as prompt_yes_no, patch("main._run_conversion_batch") as run_batch:
            renderer = renderer_cls.return_value
            renderer.interactive = True
            self.assertEqual(main.main(), 0)

        probe_media.assert_called_once_with(Path("/tmp/movie.mkv"))
        print_overview.assert_called_once_with([media_info], False)
        prompt_height.assert_called_once_with()
        prepare_progress.assert_called_once_with([media_info])
        select_positions.assert_called_once_with([media_info], False, True, True)
        prompt_yes_no.assert_called_once_with("Proceed with conversion?", default=True)
        renderer.render.assert_called_once()
        run_batch.assert_called_once()



class RepositoryPolicyTests(unittest.TestCase):
    def test_no_tracked_media_files(self):
        result = subprocess.run(
            ["git", "ls-files", "--", "*.mp4", "*.mkv"],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
