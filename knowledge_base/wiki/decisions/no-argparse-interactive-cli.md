# decision: no argparse for the interactive CLI

> Sources: [[../../raw/2026-07-11-module-main/meta.md]], [[../../raw/2026-07-11-module-tracks/meta.md]], [[../../raw/2026-07-11-readme/meta.md]]
> Status: established — the "Why" section is inferred rather than sourced; see [[../QUESTIONS.md]]
> Last updated: 2026-07-11

**Decision:** the main `ffmpeg-converter` CLI (`main.py`) never uses `argparse`/`click`/any flag-parsing
library. Every input — the source path, audio/subtitle track choice, target height, proceed-or-cancel
confirmation — is gathered through a raw `input()` prompt loop (see `tracks.py`'s `choose_stream_position()`,
`choose_menu_option()`, `prompt_yes_no()`, `prompt_target_height()`, all documented in
[[../concepts/track-validation]]), each looping until valid input is given.

**Why (inferred, not stated anywhere explicitly):** the tool's whole interaction model is a guided,
one-shot session — probe the file, show what was found, ask a short sequence of questions with sensible
defaults, show an ETA, confirm, convert. There's no batch/scripting use case in the README's documented
workflow that would need flags (no `--audio-track 2 --height 720` invocation is described anywhere), so a
flag interface would just be unused surface area to maintain.

**Scope of the decision:** this applies to `main.py`'s interactive CLI specifically. It does **not** extend
to every future script in this repo — `knowledge_base/tools/search.py` is an explicit, documented exception,
because it's a headless query tool (invoked by a human running one command, or by Claude Code shelling out
to it mid-skill) where an `input()` loop would be actively wrong. See `knowledge_base/README.md` for that
exception's full rationale.

## See also
- [[../concepts/cli-prompt-flow]]
- [[../concepts/track-validation]]
