---
name: verify
description: Verify changes to the YouTube Downloader without hitting the network — byte-compile, import/wiring check, menu smoke test, and a fake-service flow test. Use after any change to main.py or the youtube_downloader/ package.
---

# verify

This repo has **no test suite** and every real run hits YouTube. Use this offline
recipe to confirm a change didn't break imports, wiring, or the display logic.

## Setup

Prefer the project venv if it exists, otherwise system Python 3:

```bash
PY=.venv/bin/python; [ -x "$PY" ] || PY=python3
```

Dependencies (from `requirements.txt`): `yt-dlp`, `youtube-transcript-api`,
`pysrt`, `flask`, plus external `ffmpeg`. If imports fail with `ModuleNotFoundError`,
create a venv and install: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

## Steps (run from the repo root)

1. **Byte-compile** — catches syntax errors in every module:
   ```bash
   $PY -m py_compile main.py youtube_downloader/*.py youtube_downloader/gui/*.py && echo "compile OK"
   ```

2. **Import / wiring / circular-import check:**
   ```bash
   $PY -c "import youtube_downloader, main; main.build_console_app(); print('wiring OK')"
   ```
   `build_console_app()` constructs every concrete service + the shared
   `DownloadWorkflows` and injects them into `ConsoleApp`, so this fails loudly if
   an ABC method is unimplemented.

3. **Menu smoke test** — banner/menu renders and Quit exits cleanly (code 0).
   Pass `--console-view`, because bare `main.py` now launches the web GUI:
   ```bash
   printf '3\n' | $PY main.py --console-view; echo "[exit $?]"
   ```
   Expect the "Welcome to Youtube Downloader V1.1.2" banner and the 1/2/3 menu.

4. **Fake-service flow test** — exercises the console display logic, the shared
   `DownloadWorkflows` (video + playlist orchestration), the pure helpers, and the
   Flask app (offline, via its test client) with **no network**:
   ```bash
   $PY .claude/skills/verify/smoke_test.py
   ```
   Must end with `ALL ASSERTIONS PASSED`. (The script adds the repo root to
   `sys.path` itself, so it runs from any directory with no `PYTHONPATH` needed.)

## Pass criteria

All four steps succeed. If step 2 or 4 fails, the change broke the interface
contract, the workflow logic, or the display logic — fix before proceeding. Steps
are fully offline; they never download anything.
