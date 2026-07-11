# decision: docstring and banner conventions

> Sources: [[../../raw/2026-07-11-main-refactoring-plan/meta.md]], [[../../raw/2026-07-11-module-main/meta.md]]
> Status: established
> Last updated: 2026-07-11

**Decision:** every function gets a Google-style docstring (summary line, `Args:`, `Returns:`, `Raises:`
sections), and any module needing type aliases or user-facing string literals groups them under two
banner-comment sections near the top of the file:

```python
# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# User-facing string constants
# ---------------------------------------------------------------------------
```

**Origin:** `plans/main-refactoring-plan.md`, written to guide the refactor landed in commit `7f87966`. The
plan's stated motivations: docstrings compatible with Sphinx/mkdocs-style generators; string constants
extracted for easier future localization and to avoid repeating literals; a type alias
(`_StreamPositions`) to avoid repeating a verbose 4-tuple return type signature.

**Convention for string constants specifically:** use `.format()` placeholders, not f-strings — because
these are module-level constants defined once and interpolated later at the call site, where an f-string
wouldn't have its variables in scope. Naming: `_PROMPT_*` for input prompts, `_MSG_*` for status/error
output.

**Scope:** so far only fully applied in `main.py` (see [[../concepts/cli-prompt-flow]] for how it's used
there). New user-facing CLI code — including `knowledge_base/tools/search.py`'s argparse help strings —
should follow the same string-constant pattern where practical, even though `search.py` itself is otherwise
a deliberate exception to the *no-argparse* decision (see [[no-argparse-interactive-cli]]).

## See also
- [[../concepts/cli-prompt-flow]]
- [[../concepts/repo-history]]
