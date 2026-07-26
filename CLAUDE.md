# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A console YouTube downloader. Given a video or playlist URL it downloads the
best-quality MP4 (via yt-dlp + ffmpeg), optionally downloads subtitles as `.srt`
(via youtube-transcript-api), and can split a video and its subtitles into
per-chapter files. It is an interactive terminal app driven by numbered menu
prompts — there are no command-line arguments.

## Architecture

The code follows SOLID. `main.py` is a thin entry point; all logic lives in the
`youtube_downloader/` package, organized one responsibility per module. The CLI
depends on **abstract interfaces**, never on concrete libraries.

```
main.py                      # build_app() wires concrete services, then .run()
youtube_downloader/
  interfaces.py   # ABCs: InfoProvider, VideoDownloader, SubtitleService, ChapterSplitter
  models.py       # dataclasses: Chapter, VideoInfo, PlaylistInfo
  utils.py        # pure helpers: clean_filename, format_video_length, format_counter, seconds_to_srt_time
  info_service.py # YtDlpInfoProvider(InfoProvider)      — metadata via yt-dlp
  downloader.py   # YtDlpDownloader(VideoDownloader)     — download via yt-dlp
  subtitles.py    # TranscriptApiSubtitleService(SubtitleService)
  chapters.py     # FfmpegChapterSplitter(ChapterSplitter) — ffmpeg + pysrt
  filesystem.py   # side effects: open_folder, create_text_file, clear_console, ensure_dir
  cli.py          # ConsoleApp — menu + all user I/O, orchestrates injected services
```

Dependency flow: `cli.py` → `interfaces.py` + `models.py` + `utils.py`. Concrete
service modules also implement `interfaces.py`. Only `main.py` knows the concrete
classes and does the wiring.

## Conventions to follow

- **Respect the layering.** `ConsoleApp` must depend only on the interface types
  in `interfaces.py`. To add or swap a capability (e.g. a different downloader),
  write a new class that implements the relevant ABC and wire it in `main.py`'s
  `build_app()` — do not import concrete services into `cli.py`.
- **One responsibility per module.** Fetching, downloading, subtitles, chapter
  splitting, filesystem side effects, and user I/O are separate. Keep new code in
  the module that owns that concern; keep all `input()`/`print()` in `cli.py`.
- **Data is typed.** Pass `VideoInfo` / `PlaylistInfo` / `Chapter` dataclasses
  (models.py), not dicts. Derived values like duration are dataclass properties.
- **Naming:** snake_case for functions and locals, PascalCase for classes. Add
  type hints on new functions/methods.
- **Do not change user-facing behavior casually.** The menu text, prompts, and
  printed output are the product UX (currently "V1.1.2"). Preserve wording and
  output format unless the user explicitly asks to change it.
- **External dependencies:** `yt-dlp`, `youtube-transcript-api`, `pysrt` (see
  `requirements.txt`), plus **ffmpeg** as an external runtime binary used for
  merging streams and chapter splitting.

## Running & verifying

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py            # interactive menu: 1=Video, 2=Playlist, 3=Quit
```

`.venv/`, `__pycache__/`, `.idea/`, and `output/` are gitignored.

There is no test suite. To verify changes without hitting the network:

1. `python3 -m py_compile main.py youtube_downloader/*.py` — catches syntax errors.
2. `python -c "import youtube_downloader, main"` — catches import/wiring errors.
3. Drive the menu with piped input, e.g. `printf '3\n' | python main.py`, to
   confirm the banner/menu render and Quit exits cleanly.
4. For flow logic, inject **fake** services (classes implementing the ABCs) into
   `ConsoleApp` and monkeypatch `builtins.input`, capturing stdout — this exercises
   `video_processes` / `playlist_processes` display logic without any download.

See `RUN.md` for the full end-to-end run manual.

## Git

- Default branch for PRs is `master`; active development branch is `DEV-Console-App`.
- Commit or push only when the user asks.
