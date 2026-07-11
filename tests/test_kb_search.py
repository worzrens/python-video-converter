import tempfile
import unittest
from pathlib import Path

from knowledge_base.tools import search


class ScoreLineTests(unittest.TestCase):
    def test_counts_case_insensitive_occurrences(self):
        self.assertEqual(search._score_line("Smooth ETA smoothing", ["smooth"]), 2)

    def test_counts_multiple_terms(self):
        self.assertEqual(search._score_line("audio track validation", ["audio", "track"]), 2)

    def test_no_match_scores_zero(self):
        self.assertEqual(search._score_line("nothing relevant here", ["ffmpeg"]), 0)


class SearchCorpusTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def _write(self, relative_path: str, content: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_finds_matching_line_with_location(self):
        self._write("wiki/concepts/progress.md", "line one\nSpeed is smoothed with an EMA\nline three")

        hits = search.search(self.root, "smoothed")

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].line_number, 2)
        self.assertEqual(hits[0].path, self.root / "wiki/concepts/progress.md")

    def test_ranks_higher_scoring_lines_first(self):
        self._write("a.md", "audio track audio")
        self._write("b.md", "audio only")

        hits = search.search(self.root, "audio")

        self.assertEqual(hits[0].path, self.root / "a.md")
        self.assertEqual(hits[0].score, 2)
        self.assertEqual(hits[1].score, 1)

    def test_respects_limit(self):
        self._write("many.md", "\n".join(f"match {i}" for i in range(10)))

        hits = search.search(self.root, "match", limit=3)

        self.assertEqual(len(hits), 3)

    def test_no_matches_returns_empty_list(self):
        self._write("a.md", "nothing here")

        self.assertEqual(search.search(self.root, "ffmpeg"), [])

    def test_blank_query_returns_empty_list(self):
        self._write("a.md", "some content")

        self.assertEqual(search.search(self.root, "   "), [])


if __name__ == "__main__":
    unittest.main()
