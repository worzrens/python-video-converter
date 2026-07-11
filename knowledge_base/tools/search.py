"""Naive keyword search engine over the knowledge_base/ markdown corpus.

This is a deliberate exception to the rest of this repo's no-argparse convention: unlike main.py's
interactive CLI, this tool is invoked headlessly (directly by a human, or by Claude Code shelling out to
it mid-skill), so argparse is the right fit here. See knowledge_base/README.md for the full rationale.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

_SearchResults = list["SearchHit"]

# ---------------------------------------------------------------------------
# User-facing string constants
# ---------------------------------------------------------------------------

_ARG_QUERY_HELP = "Keyword(s) to search for across knowledge_base/."
_ARG_ROOT_HELP = "Root directory to search (default: the knowledge_base/ directory containing this file)."
_ARG_LIMIT_HELP = "Maximum number of hits to print (default: 20)."
_MSG_NO_RESULTS = "No matches found for {query!r}."
_MSG_HIT_LINE = "{path}:{line_number}: {line_text}"


@dataclass(frozen=True)
class SearchHit:
    """A single scored line match.

    Args:
        path: Path to the markdown file containing the match, relative to the search root.
        line_number: 1-indexed line number of the match within the file.
        line_text: The matching line's text, stripped of surrounding whitespace.
        score: Number of query-term hits found on this line.
    """

    path: Path
    line_number: int
    line_text: str
    score: int


def _iter_markdown_files(root: Path) -> list[Path]:
    """Return every ``.md`` file under root, sorted for stable output.

    Args:
        root: Directory to search recursively.

    Returns:
        Sorted list of markdown file paths.
    """
    return sorted(root.rglob("*.md"))


def _score_line(line: str, terms: list[str]) -> int:
    """Count case-insensitive occurrences of any query term in a line.

    Args:
        line: The line of text to score.
        terms: Lowercased query terms to match against.

    Returns:
        Total number of term occurrences found in the line.
    """
    lowered = line.lower()
    return sum(lowered.count(term) for term in terms)


def search(root: Path, query: str, limit: int = 20) -> _SearchResults:
    """Search every markdown file under root for lines matching query.

    Args:
        root: Directory to search recursively.
        query: Whitespace-separated keywords to match, case-insensitively.
        limit: Maximum number of hits to return, highest-scoring first.

    Returns:
        Matching hits sorted by descending score, then by path and line number.
    """
    terms = [term for term in query.lower().split() if term]
    if not terms:
        return []

    hits: _SearchResults = []
    for path in _iter_markdown_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            score = _score_line(line, terms)
            if score > 0:
                hits.append(SearchHit(path=path, line_number=line_number, line_text=line.strip(), score=score))

    hits.sort(key=lambda hit: (-hit.score, str(hit.path), hit.line_number))
    return hits[:limit]


def _format_hit(hit: SearchHit) -> str:
    """Format a single hit as a grep-style ``path:line: text`` string.

    Args:
        hit: The hit to format.

    Returns:
        The formatted line.
    """
    return _MSG_HIT_LINE.format(path=hit.path, line_number=hit.line_number, line_text=hit.line_text)


def main(argv: list[str] | None = None) -> int:
    """Run the search CLI.

    Args:
        argv: Command-line arguments, excluding the program name. Defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code: 0 on success (matches found or not), non-zero on error.
    """
    default_root = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--query", "-q", required=True, help=_ARG_QUERY_HELP)
    parser.add_argument("--root", type=Path, default=default_root, help=_ARG_ROOT_HELP)
    parser.add_argument("--limit", type=int, default=20, help=_ARG_LIMIT_HELP)
    args = parser.parse_args(argv)

    hits = search(args.root, args.query, args.limit)
    if not hits:
        print(_MSG_NO_RESULTS.format(query=args.query))
        return 0

    for hit in hits:
        print(_format_hit(hit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
