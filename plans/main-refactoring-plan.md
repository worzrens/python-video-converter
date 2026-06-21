# main.py Refactoring Plan

## Objective

Improve code quality and add comprehensive docstrings to every function in [`main.py`](../main.py).

---

## Current State Analysis

The file currently has **8 functions** (1 public `main`, 7 private helpers). None have docstrings beyond the module-level docstring. The code is functional but lacks documentation that explains the purpose, parameters, return values, and side effects of each function.

---

## Docstring Standard

All docstrings will follow the **Google style** convention, which is widely used in the Python ecosystem and compatible with most documentation generators (Sphinx, mkdocs, etc.).

Format:

```python
def function_name(param1: Type, param2: Type) -> ReturnType:
    """One-line summary of what the function does.

    Longer description explaining the purpose, behavior, and any
    notable edge cases or side effects.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of the return value.

    Raises:
        ExceptionType: When this exception may be raised.
    """
```

---

## Changes by Function

### 1. Module Docstring (Line 1)

**Current:**
```python
"""CLI entry point that orchestrates discovery, prompting, and conversion."""
```

**Change:** Expand to describe the overall purpose, the modules it depends on, and the entry point pattern.

---

### 2. `_ensure_cli_dependencies()` (Lines 37-41)

**Current:** No docstring.

**Add:**
```python
def _ensure_cli_dependencies() -> bool:
    """Verify that ffmpeg and ffprobe are installed and available on PATH.

    Checks both tools using shutil.which(). Prints an error message to
    stderr if either is missing.

    Returns:
        True if both tools are found; False otherwise.
    """
```

---

### 3. `_prompt_input_path()` (Lines 44-49)

**Current:** No docstring.

**Add:**
```python
def _prompt_input_path() -> Path | None:
    """Prompt the user for a file or folder path and resolve it.

    Reads from stdin, strips whitespace, and rejects empty input.
    Expands user home directory shortcuts (~) and resolves to an
    absolute path.

    Returns:
        A resolved Path object if the user provides input;
        None if the input is empty.
    """
```

---

### 4. `_print_media_overview()` (Lines 52-68)

**Current:** No docstring.

**Add:**
```python
def _print_media_overview(
    media_infos: Sequence[MediaInfo],
    is_folder_mode: bool,
) -> tuple[bool, bool]:
    """Display media metadata and, for folder mode, validate track consistency.

    Prints a formatted summary of the first file (format, size, resolution,
    tracks). In folder mode, also validates that all files have matching
    audio and subtitle track layouts.

    Args:
        media_infos: List of MediaInfo objects for the target files.
        is_folder_mode: True if processing multiple files from a folder.

    Returns:
        A tuple of (audio_consistent, subtitle_consistent) booleans.
        In single-file mode, always returns (True, True).
    """
```

---

### 5. `_prepare_batch_progress()` (Lines 71-83)

**Current:** No docstring.

**Add:**
```python
def _prepare_batch_progress(media_infos: Sequence[MediaInfo]) -> BatchProgressState:
    """Estimate total conversion time and initialize batch progress tracking.

    Sums the duration of all media files and calculates an estimated
    conversion time based on a default encode speed of 1.0x. Prints
    the estimate to stdout.

    Args:
        media_infos: List of MediaInfo objects whose durations are summed.

    Returns:
        A BatchProgressState initialized with total file count,
        zeroed completed counters, and the estimated total duration.
    """
```

---

### 6. `_select_stream_positions()` (Lines 86-110)

**Current:** No docstring.

**Add:**
```python
def _select_stream_positions(
    media_infos: Sequence[MediaInfo],
    is_folder_mode: bool,
    audio_consistent: bool,
    subtitle_consistent: bool,
) -> tuple[list[int] | None, list[int] | None, int | None, int | None]:
    """Resolve audio and subtitle stream positions for all target files.

    In folder mode, delegates to resolve_folder_stream_positions() which
    handles common-track selection across files with potentially different
    stream indices. In single-file mode, prompts the user to select a
    single audio and subtitle track.

    Args:
        media_infos: List of MediaInfo objects for the target files.
        is_folder_mode: True if processing multiple files from a folder.
        audio_consistent: Whether audio track layouts match across files.
        subtitle_consistent: Whether subtitle track layouts match across files.

    Returns:
        A tuple of four values:
            - audio_positions: List of per-file audio stream indices (folder mode) or None.
            - subtitle_positions: List of per-file subtitle stream indices (folder mode) or None.
            - audio_position: Single audio stream index (single-file mode) or None.
            - subtitle_position: Single subtitle stream index (single-file mode) or None.
    """
```

---

### 7. `_run_conversion_batch()` (Lines 113-147)

**Current:** No docstring.

**Add:**
```python
def _run_conversion_batch(
    media_infos: Sequence[MediaInfo],
    target_height: int,
    is_folder_mode: bool,
    output_root: Path | None,
    audio_positions: list[int] | None,
    subtitle_positions: list[int] | None,
    audio_position: int | None,
    subtitle_position: int | None,
    batch_progress: BatchProgressState,
    renderer: ProgressRenderer,
) -> None:
    """Execute ffmpeg conversion for each media file in sequence.

    For each file, calculates the output dimensions, builds the output
    path, creates parent directories, and invokes convert_file(). Updates
    the batch progress state after each file completes.

    Args:
        media_infos: List of MediaInfo objects for the target files.
        target_height: Target output height in pixels.
        is_folder_mode: True if output should go into a sibling directory.
        output_root: Root directory for folder-mode output, or None.
        audio_positions: Per-file audio stream indices (folder mode).
        subtitle_positions: Per-file subtitle stream indices (folder mode).
        audio_position: Single audio stream index (single-file mode).
        subtitle_position: Single subtitle stream index (single-file mode).
        batch_progress: Shared progress state updated after each file.
        renderer: ProgressRenderer instance for terminal output.
    """
```

---

### 8. `main()` (Lines 150-204)

**Current:** No docstring.

**Add:**
```python
def main(argv: Sequence[str] | None = None) -> int:
    """Run the interactive video conversion CLI.

    Orchestrates the full conversion workflow:
    1. Verify ffmpeg/ffprobe dependencies.
    2. Prompt for input path (file or folder).
    3. Discover target files and probe their metadata.
    4. Display media overview and validate track consistency.
    5. Prompt for target height, audio/subtitle track selection.
    6. Show estimated conversion time and request confirmation.
    7. Execute batch conversion with live progress updates.

    Args:
        argv: Optional command-line arguments (passed to subprocess calls).
              If None, uses default behavior.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
```

---

## Additional Code Quality Improvements

### 9. Import Organization

**Current:** Imports are grouped but not sorted.

**Change:** Organize imports using the **BLK/isort** convention:
1. Standard library imports (`shutil`, `sys`, `pathlib`, `typing`)
2. Third-party imports (none currently)
3. Local application imports (`conversion`, `media`, `progress`, `tracks`)

Add a blank line between each group.

### 10. Magic Number / String Extraction

**Current (Line 173):**
```python
if not prompt_yes_no("Proceed with conversion?", default=True):
```

**Change:** Extract user-facing strings to module-level constants for easier localization:

```python
_PROMPT_INPUT_PATH = "Enter path to a movie file or folder: "
_PROMPT_PROCEED = "Proceed with conversion?"
_MSG_CANCELLED = "Cancelled."
_MSG_NO_PATH = "No path provided."
_MSG_DEPENDENCIES = "ffmpeg and ffprobe must be installed and available on PATH."
_MSG_CONVERTED = "Converted {completed}/{total} files."
_MSG_SINGLE_FILE_MODE = "Single-file mode."
_MSG_TRACKS_MATCH = "Tracks match across files."
_MSG_AUDIO_DIFFER = "Audio tracks differ across files."
_MSG_SUBTITLE_DIFFER = "Subtitle tracks differ across files."
_MSG_FOLDER_COUNT = "Folder contains {count} movie files."
```

### 11. Error Handling in `_print_media_overview()`

**Current:** Accesses `media_infos[0]` without checking for empty sequence.

**Change:** Add a guard clause:

```python
def _print_media_overview(
    media_infos: Sequence[MediaInfo],
    is_folder_mode: bool,
) -> tuple[bool, bool]:
    if not media_infos:
        print("No media files to process.", file=sys.stderr)
        return False, False
    # ... rest of function
```

### 12. Type Alias for Return Type

**Current:** The return type `tuple[list[int] | None, list[int] | None, int | None, int | None]` is repeated and verbose.

**Change:** Define a type alias at module level:

```python
_StreamPositions = tuple[
    list[int] | None,  # audio_positions
    list[int] | None,  # subtitle_positions
    int | None,        # audio_position
    int | None,        # subtitle_position
]
```

Then use in the function signature:

```python
def _select_stream_positions(...) -> _StreamPositions:
```

---

## Summary of Changes

| # | Function | Docstring | Code Quality Change |
|---|----------|-----------|---------------------|
| 1 | Module | Expanded | Import organization |
| 2 | `_ensure_cli_dependencies()` | Added | None |
| 3 | `_prompt_input_path()` | Added | Extract prompt string to constant |
| 4 | `_print_media_overview()` | Added | Add empty sequence guard |
| 5 | `_prepare_batch_progress()` | Added | Extract format string to constant |
| 6 | `_select_stream_positions()` | Added | Add type alias for return type |
| 7 | `_run_conversion_batch()` | Added | Extract success message to constant |
| 8 | `main()` | Added | Extract prompt/message strings to constants |

---

## Implementation Order

1. Add type alias `_StreamPositions` at module level
2. Add module-level string constants
3. Add docstrings to helper functions (2-7) in order
4. Add docstring to `main()`
5. Refactor hardcoded strings to use constants
6. Reorganize imports
7. Add empty sequence guard to `_print_media_overview()`
