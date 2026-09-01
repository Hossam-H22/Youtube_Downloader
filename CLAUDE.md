# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A YouTube downloader. Given a video or playlist URL it downloads the best-quality
MP4 (via yt-dlp + ffmpeg), optionally downloads subtitles as `.srt` (via
youtube-transcript-api), and can split a video and its subtitles into per-chapter
files. It has **two front-ends** over one shared engine: a **web GUI** (Flask +
browser, the default) and an interactive **console**. `python main.py` launches
the GUI; `python main.py --console-view` runs the console.

## Architecture

The code follows SOLID. `main.py` is a thin entry point; all logic lives in the
`youtube_downloader/` package, organized one responsibility per module. Both
front-ends depend on **abstract interfaces** and the shared `DownloadWorkflows`,
never on concrete libraries.

```
main.py                      # dispatch: GUI (default) or console (--console-view); build_services()
youtube_downloader/
  interfaces.py   # ABCs: InfoProvider, VideoDownloader, SubtitleService, ChapterSplitter
  models.py       # dataclasses: Chapter, VideoInfo, PlaylistInfo + *DownloadOptions/*Result
  utils.py        # pure helpers: clean_filename, format_video_length, format_counter, seconds_to_srt_time
  info_service.py # YtDlpInfoProvider(InfoProvider)      — metadata via yt-dlp
  downloader.py   # YtDlpDownloader(VideoDownloader)     — download via yt-dlp (optional progress_hook)
  subtitles.py    # TranscriptApiSubtitleService(SubtitleService)
  chapters.py     # FfmpegChapterSplitter(ChapterSplitter) — ffmpeg + pysrt
  filesystem.py   # side effects: open_folder, pick_folder, create_text_file, clear_console, ensure_dir
  metadata.py     # get_metadata()/get_version() — reads metadata.json (single source of truth)
  settings.py     # get_settings()/update_settings() — metadata.json defaults + writable settings.json
  ytdlp_support.py# base_ydl_opts() — shared yt-dlp options (player clients, nsig solver, cookies) + error classification
  logging_config.py # setup_logging() — always-on file log + optional console (see below)
  workflows.py    # DownloadWorkflows — shared download/subtitle/chapter orchestration (no UI)
  cli.py          # ConsoleApp — console menu + I/O, delegates to workflows
  gui/            # Flask web front-end (server.py, jobs.py, web/{index.html,style.css,app.js})
```

Dependency flow: `cli.py` and `gui/` → `workflows.py` + `interfaces.py` +
`models.py`. Concrete service modules implement `interfaces.py`. Only `main.py`
knows the concrete classes and does the wiring. The GUI reports progress via a
`progress_hook` passed into `download()` and streams it to the browser over SSE.

## Conventions to follow

- **Respect the layering.** The front-ends (`cli.py`, `gui/`) depend only on the
  interface types in `interfaces.py` and on `DownloadWorkflows`. To add or swap a
  capability (e.g. a different downloader), write a new class that implements the
  relevant ABC and wire it in `main.py`'s `build_services()` — do not import
  concrete services into `cli.py` or `gui/`.
- **Shared download logic lives in `workflows.py`.** `DownloadWorkflows` is
  UI-agnostic (no `input()`/`print()`); it reports progress through callbacks
  (`on_video`, `progress_hook`). Put new download/subtitle/chapter orchestration
  here so both front-ends get it — never duplicate it in a front-end.
- **One responsibility per module.** Fetching, downloading, subtitles, chapter
  splitting, filesystem side effects, and user I/O are separate. Keep console I/O
  (`input()`/`print()`) in `cli.py`; keep web I/O in `gui/`.
- **Data is typed.** Pass `VideoInfo` / `PlaylistInfo` / `Chapter` dataclasses
  (models.py), not dicts. Derived values like duration are dataclass properties.
- **Naming:** snake_case for functions and locals, PascalCase for classes. Add
  type hints on new functions/methods.
- **Logging is always on.** Every module has `logger = logging.getLogger(__name__)`
  and logs its steps (INFO for milestones, DEBUG for detail, WARNING/ERROR for
  problems). `main.py` calls `setup_logging()` once; logs always go to a rotating
  file (`logs/youtube_downloader.log`) and, in GUI mode, also to the terminal. When
  adding a step, log it. Don't `print()` for diagnostics — use the logger (a few
  legacy user-facing `print()`s in the console flow stay as UX).
- **Do not change user-facing behavior casually.** The console menu text, prompts,
  and printed output — and the GUI's labels/flow — are the product UX. Preserve
  wording and output format unless the user explicitly asks to change it.
- **Project metadata is single-sourced in `metadata.json`** (name, version,
  description, author, repository, ...). The banner reads it at runtime via
  `metadata.py`'s `get_metadata()` — never hardcode the name, version, or developer.
  Bump the version with the `/bump-version` skill.
- **Settings are layered, and only one layer is writable.** `metadata.json` holds the
  bundled *defaults*; user changes go to `settings.json` under `paths.writable_dir()`.
  Read them through `settings.get_settings()` — never `get_metadata()['settings']` —
  because `metadata.json` resolves into PyInstaller's `sys._MEIPASS` when frozen and
  is wiped on exit, so anything a user can change must live in the writable layer.
  `settings.py` also owns the valid values for a setting (e.g.
  `SUPPORTED_COOKIE_BROWSERS`) so front-ends can offer choices without importing
  service internals.
- **All yt-dlp options come from `ytdlp_support.base_ydl_opts()`.** The downloader and
  both info-provider methods spread it, so the player-client fallback list, the opt-in
  JS runtime, and cookies can never drift apart between metadata fetches and downloads.
  Add shared yt-dlp behavior there, not in one call site.
- **Opt-in JS runtime.** `settings.use_js_runtime` (default `true` in the shipped
  `metadata.json`). When on and a runtime (deno/node/bun) is on `PATH`,
  `ytdlp_support.js_runtime_opts()` enables it plus the remote EJS solver so yt-dlp
  solves YouTube's nsig challenge (all formats, no warning). It fetches a solver
  script from the yt-dlp GitHub, so it can be turned off. Downloads work either way
  (the downloader prefers H.264 formats that don't need nsig).
- **Cookies are how sign-in blocks get fixed.** YouTube's "Sign in to confirm you're
  not a bot" is cleared by `settings.cookies_from_browser` / `cookies_file`, turned
  into yt-dlp options by `ytdlp_support.cookie_opts()`. Classify such failures with
  `is_auth_error()` (never retry them — retrying repeats the block) and report them
  with `friendly_error()`, which is applied at the source (`info_service`,
  `downloader`) so neither front-end needs to know anything about yt-dlp.
- **Report download failures.** `DownloadOutcome` / `VideoDownloadResult.success` exist
  so a failed download is never presented as a success — check them in the workflows
  and surface the reason in both front-ends.
- **External dependencies:** `yt-dlp`, `youtube-transcript-api`, `pysrt`, `flask`
  (see `requirements.txt`), plus **ffmpeg** as an external runtime binary used for
  merging streams and chapter splitting.

## Running & verifying

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py                 # web GUI (opens the browser)
python main.py --console-view  # console menu: 1=Video, 2=Playlist, 3=Quit
```

`.venv/`, `__pycache__/`, `.idea/`, and `output/` are gitignored.

Prefer the **`/verify`** skill — it runs the full offline recipe below. To verify
changes without hitting the network:

1. `python3 -m py_compile main.py youtube_downloader/*.py youtube_downloader/gui/*.py` — catches syntax errors.
2. `python -c "import youtube_downloader, main; main.build_console_app()"` — catches import/wiring errors.
3. Drive the menu with piped input, e.g. `printf '3\n' | python main.py --console-view`,
   to confirm the banner/menu render and Quit exits cleanly (bare `main.py` opens the GUI).
4. For flow logic, inject **fake** services (classes implementing the ABCs) into
   `ConsoleApp`/`DownloadWorkflows` and monkeypatch `builtins.input`, capturing stdout,
   and test the Flask app offline with `app.test_client()` — this exercises
   `video_processes` / `playlist_processes` display logic without any download.

See `RUN.md` for the full end-to-end run manual.

## Git

- Default branch for PRs is `master`; active development branch is `DEV-Console-App`.
- Commit or push only when the user asks.
