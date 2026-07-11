# What are the CLI's interactive prompt defaults?

- Asked: 2026-07-11
- Sources consulted: `tracks.py`, `main.py`, `progress.py` (direct source read — not yet in the wiki, see
  `wiki/QUESTIONS.md`)

## Question

What is the default parameters of script? (Narrowed to the interactive prompt defaults specifically — the
fixed ffmpeg encode defaults are already covered in
[wiki/concepts/ffmpeg-pipeline.md](../../wiki/concepts/ffmpeg-pipeline.md).)

## Answer

**Answer source:** repo source (wiki didn't cover this)

Every interactive prompt in `main.py`'s CLI flow has a default that pressing enter accepts, defined in
`tracks.py`, `main.py`, and `progress.py`:

| Prompt | Default | Where |
|---|---|---|
| Target height | **1080** | `tracks.prompt_target_height(default_height=1080)` |
| "Proceed with conversion?" confirmation | **Yes** | `tracks.prompt_yes_no(_PROMPT_PROCEED, default=True)` in `main.py` |
| Menu-style selections (audio/subtitle track, common-track choice) | **first option** (`default_index=0`) | `tracks.choose_menu_option()` |
| Initial estimated encode speed (before any real `speed=` sample) | **1.0x** | `progress.DEFAULT_ESTIMATED_ENCODE_SPEED = 1.0` |

Mechanics: `choose_menu_option()` prints `[1-N] [<default+1>]` and returns `default_index` on empty input;
`prompt_yes_no()` prints `[Y/n]` or `[y/N]` depending on which way `default` leans and returns that `bool` on
empty input; `prompt_target_height()` prints `Target height [1080]` and returns `1080` on empty input.

For contrast, the *fixed* (non-prompted) encode defaults in `conversion.py` are: `libx264` video at CRF 20 /
preset `medium`, `aac` audio at 192k, `mov_text` for embedded subtitles — these are never prompted, only the
copy-path optimization can bypass them entirely.

## Gap this surfaced

None of this — the concrete default values (1080, Yes, first-option, 1.0x) — is written down in
`wiki/concepts/cli-prompt-flow.md` or `wiki/concepts/track-validation.md`; both describe the *flow* through
these prompts without stating what pressing enter actually does. Logged in `wiki/QUESTIONS.md` under
"Coverage gaps" pointing back at this file, so a future `/kb-compile` pass can fold these values into the
wiki proper.
