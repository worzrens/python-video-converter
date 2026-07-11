# CLAUDE.md

## What this repo is

`ffmpeg-converter`: an interactive Python CLI that converts movie files with `ffmpeg`/`ffprobe`. See
[README.md](README.md) for behavior and workflow.

## Code conventions

- `from __future__ import annotations` first in every module, followed by a module-level docstring.
- Modern union syntax (`X | None`), not `Optional`.
- `@dataclass` for structured data (see `media.py`, `progress.py`).
- Google-style docstrings: summary line, blank line, `Args:`/`Returns:` sections.
- Private helpers prefixed `_`.
- `main.py` uses two banner-comment sections — `# --- Type aliases ---` (private `_CamelCase` tuple type
  aliases) and `# --- User-facing string constants ---` (`_PROMPT_*`/`_MSG_*` SCREAMING_SNAKE constants,
  using `.format()` not f-strings) — follow this pattern for any new user-facing CLI text.
- **No argparse/click** for the main interactive CLI — it's driven entirely by `input()` prompts with
  defaults and confirmations. (`knowledge_base/tools/search.py` is a deliberate, documented exception — see
  `knowledge_base/README.md` — because it's a headless query tool, not an interactive one.)
- Errors print via `print(..., file=sys.stderr)`; `main()` returns an int exit code; entry point is
  `if __name__ == "__main__": raise SystemExit(main())`.

## Tests

- `tests/test_main.py` uses `unittest.TestCase`, grouped into `<Thing>Tests` classes with `test_*` methods,
  mocking `subprocess.run` via `unittest.mock.patch`. Follow this pattern for new test files rather than
  introducing pytest.
- There is no lint/test CI currently — `.github/workflows/block-media-files.yml` is the only workflow, and it
  only blocks committing tracked video files.

## Dependencies

- `uv` is the dependency manager (`uv.lock`). `dependencies = []` in `pyproject.toml` — keep it that way;
  prefer the standard library over adding a new dependency.

## knowledge_base/

This repo also has a self-documenting knowledge base at [knowledge_base/](knowledge_base/) — source material
about this project's own design gets ingested into `knowledge_base/raw/` (untracked, local-only) and
compiled into a linked markdown wiki at `knowledge_base/wiki/` (tracked). It's maintained via the
`/kb-ingest`, `/kb-compile`, `/kb-ask`, and `/kb-lint` skills. See
[knowledge_base/README.md](knowledge_base/README.md) for the full rules and templates before touching
anything under `knowledge_base/`.
