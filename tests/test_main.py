import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class ProbeMediaTests(unittest.TestCase):
    def test_probe_media_parses_streams(self):
        payload = {
            "format": {"format_name": "matroska,webm", "size": "123456", "duration": "12.5"},
            "streams": [
                {"index": 0, "codec_type": "video", "codec_name": "h264", "width": 3840, "height": 2160},
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
            info = main.probe_media(Path("/tmp/movie.mkv"))

        self.assertEqual(info.format_name, "matroska,webm")
        self.assertEqual(info.duration_seconds, 12.5)
        self.assertEqual(info.size_bytes, 123456)
        self.assertEqual(info.width, 3840)
        self.assertEqual(info.height, 2160)
        self.assertEqual(info.audio_streams[0].language, "eng")
        self.assertEqual(info.subtitle_streams[0].title, "English")
        run.assert_called_once()


class PathAndNamingTests(unittest.TestCase):
    def test_output_path_for_single_file_uses_compressed_suffix(self):
        result = main.build_output_path(Path("/movies/film.avi"), is_folder_mode=False, output_root=None)
        self.assertEqual(result, Path("/movies/film-COMPRESSED.mp4"))

    def test_output_path_for_folder_mode_uses_sibling_directory(self):
        result = main.build_output_path(
            Path("/movies/film.avi"),
            is_folder_mode=True,
            output_root=Path("/movies/collection-COMPRESSED"),
        )
        self.assertEqual(result, Path("/movies/collection-COMPRESSED/film.mp4"))


class ConsistencyAndCommandTests(unittest.TestCase):
    def test_prompt_yes_no_defaults_to_yes_on_blank(self):
        with patch("builtins.input", side_effect=[""]):
            self.assertTrue(main.prompt_yes_no("Proceed with conversion?", default=True))

    def test_format_seconds_and_estimate_total_duration(self):
        self.assertEqual(main.format_seconds(None), "unknown")
        self.assertEqual(main.format_seconds(65), "01:05")

        infos = [
            main.MediaInfo(Path("a.mkv"), "matroska", 10.0, 1, 1, 1, [], []),
            main.MediaInfo(Path("b.mkv"), "matroska", 20.0, 1, 1, 1, [], []),
        ]
        self.assertEqual(main.estimate_total_duration(infos), 30.0)

    def test_prompt_target_height_defaults_when_blank(self):
        with patch("builtins.input", side_effect=[""]):
            self.assertEqual(main.prompt_target_height(), 1080)

    def test_prompt_target_height_accepts_custom_value(self):
        with patch("builtins.input", side_effect=["720"]):
            self.assertEqual(main.prompt_target_height(), 720)

    def test_calculate_target_width_only_downscales_above_target_height(self):
        small = main.MediaInfo(
            path=Path("small.mkv"),
            format_name="matroska",
            duration_seconds=10.0,
            size_bytes=1,
            width=640,
            height=480,
            audio_streams=[],
            subtitle_streams=[],
        )
        large = main.MediaInfo(
            path=Path("large.mkv"),
            format_name="matroska",
            duration_seconds=20.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[],
            subtitle_streams=[],
        )

        self.assertIsNone(main.calculate_target_width(small, 1080))
        self.assertEqual(main.calculate_target_width(large, 1080), 1920)
        self.assertEqual(main.calculate_target_width(large, 720), 1280)

    def test_folder_track_signatures_must_match(self):
        first = main.MediaInfo(
            path=Path("one.mkv"),
            format_name="matroska",
            duration_seconds=10.0,
            size_bytes=1,
            width=1920,
            height=1080,
            audio_streams=[main.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[main.MediaStream(2, "subtitle", "subrip", "eng", "English", False)],
        )
        second = main.MediaInfo(
            path=Path("two.mkv"),
            format_name="matroska",
            duration_seconds=10.0,
            size_bytes=1,
            width=1920,
            height=1080,
            audio_streams=[main.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[main.MediaStream(2, "subtitle", "subrip", "eng", "English", False)],
        )
        main.validate_folder_consistency([first, second])

    def test_build_ffmpeg_command_sets_scale_and_default_tracks(self):
        info = main.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=30.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[
                main.MediaStream(1, "audio", "aac", "eng", "Stereo", True),
                main.MediaStream(2, "audio", "aac", "jpn", "Japanese", False),
            ],
            subtitle_streams=[main.MediaStream(3, "subtitle", "subrip", "eng", "English", False)],
        )
        command = main.build_ffmpeg_command(
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

    def test_build_ffmpeg_command_skips_scaling_for_1080p_or_lower(self):
        info = main.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=30.0,
            size_bytes=1,
            width=640,
            height=480,
            audio_streams=[main.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[],
        )
        command = main.build_ffmpeg_command(
            source=Path("movie.mkv"),
            output=Path("movie-COMPRESSED.mp4"),
            media=info,
            default_audio_position=0,
            default_subtitle_position=None,
            target_height=1080,
        )

        self.assertNotIn("-vf", command)

    def test_build_ffmpeg_command_uses_custom_target_height(self):
        info = main.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=30.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[main.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[],
        )
        command = main.build_ffmpeg_command(
            source=Path("movie.mkv"),
            output=Path("movie-COMPRESSED.mp4"),
            media=info,
            default_audio_position=0,
            default_subtitle_position=None,
            target_height=720,
        )

        self.assertIn("scale=1280:720", " ".join(command))

    def test_build_ffmpeg_command_rejects_bitmap_subtitles(self):
        info = main.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=30.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[main.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[main.MediaStream(2, "subtitle", "hdmv_pgs_subtitle", "eng", "PGS", False)],
        )

        with self.assertRaises(ValueError):
            main.build_ffmpeg_command(
                source=Path("movie.mkv"),
                output=Path("movie-COMPRESSED.mp4"),
                media=info,
                default_audio_position=0,
                default_subtitle_position=0,
                target_height=1080,
            )

    def test_convert_file_writes_progress_output(self):
        info = main.MediaInfo(
            path=Path("movie.mkv"),
            format_name="matroska",
            duration_seconds=20.0,
            size_bytes=1,
            width=3840,
            height=2160,
            audio_streams=[main.MediaStream(1, "audio", "aac", "eng", "Stereo", True)],
            subtitle_streams=[],
        )

        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO("out_time=00:00:10.00\nprogress=continue\nout_time=00:00:20.00\nprogress=end\n")

            def wait(self):
                return 0

        with patch("subprocess.Popen", return_value=FakeProcess()), patch.object(main.sys, "stdout", new=io.StringIO()) as fake_stdout:
            main.convert_file(
                source=Path("movie.mkv"),
                output=Path("movie-COMPRESSED.mp4"),
                media=info,
                audio_position=0,
                subtitle_position=None,
                target_height=1080,
            )

        output = fake_stdout.getvalue()
        self.assertIn("ETA", output)
        self.assertIn("100.0%", output)


if __name__ == "__main__":
    unittest.main()
