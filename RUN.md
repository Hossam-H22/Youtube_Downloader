# Run Manual — YouTube Downloader

How to set up and run the console application (`main.py`).

## Prerequisites

- **Python 3.8+** — check with `python3 --version`
- **ffmpeg** — required to merge best video/audio streams and to split videos into chapters.
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: download from [ffmpeg.org](https://ffmpeg.org/download.html) and add it to your `PATH`

## Setup

1. Clone the repo and enter it:
   ```bash
   git clone https://github.com/Hossam-H22/Youtube_Downloader.git
   cd Youtube_Downloader
   ```

2. Create and activate a virtual environment:
   ```bash
   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Run

The app has two front-ends that share the same download engine.

### Web GUI (default)

```bash
python main.py
```

This starts a small local web server and opens the app in your default browser
(a URL like `http://127.0.0.1:<port>/` is also printed in the terminal). Use the
**Video** / **Playlist** tabs: paste a URL, click **Fetch**, choose a subtitle
language and options, pick a folder, and click **Download** — a progress bar shows
live status and an **Open output folder** button appears when it finishes. Press
`Ctrl+C` in the terminal to stop the server.

### Console mode

```bash
python main.py --console-view
```

You'll see the interactive menu:

```
Please choose number:
1 - Video
2 - Playlist
3 - Quit
```

### Download a single video (option 1, console)

1. Paste the YouTube video URL.
2. The app shows the title, duration, available subtitles, and chapters.
3. Answer the prompts:
   - **Download Video: Y or N?**
   - **Subtitle language** — pick a number from the listed languages, or the last option for *None*.
   - **Save folder path** — an existing folder where files are saved.
   - **Split video to chapters if exist: Y or N?** — when `Y`, the video is wrapped in a folder named after the title, a `Link.txt` (URL + description) is written, and the video/subtitles are split into a `Chapters/` subfolder (requires chapters + ffmpeg).
4. When finished, the output folder opens automatically.

### Download a playlist (option 2, console)

1. Paste the YouTube playlist URL.
2. The app shows the title, video count, total duration, and available subtitles.
3. Answer the prompts:
   - **Download Playlist: Y or N?**
   - **Subtitle language**
   - **Numerated Playlist: Y or N?** — prefixes each file with its position (e.g. `01. `, `02. `).
   - **Save folder path**
4. Each video downloads into a folder named after the playlist. Failed videos are listed at the end — re-run the same playlist to retry them (already-downloaded videos are skipped).

## Settings

App settings live in two layers:

* **Defaults** ship in `metadata.json` → `"settings"` (read-only in a packaged build).
* **Your changes** are saved to `settings.json` next to the app — the repo root in a
  source checkout, beside the executable in a packaged build. This file wins over the
  defaults, and it's the only one a packaged build can write.

Edit them in the web GUI via the **Settings** button in the header, or by hand in
`settings.json`. Keys:

| Key | Default | What it does |
| --- | --- | --- |
| `cookies_from_browser` | `""` | Read YouTube cookies from a browser: `brave`, `chrome`, `chromium`, `edge`, `firefox`, `opera`, `safari`, `vivaldi`, `whale`. Empty = anonymous. |
| `cookies_file` | `""` | Path to a Netscape-format `cookies.txt` export. Use this when reading the browser store is blocked. |
| `use_js_runtime` | `true` | Let yt-dlp solve YouTube's nsig challenge with a JS runtime + the remote EJS solver. |
| `log_level` | `INFO` | Logging verbosity. |
| `check_for_updates` | `true` | Check GitHub for a newer version on startup. |

### Signing in (cookies)

YouTube sometimes refuses anonymous requests with **"Sign in to confirm you're not
a bot"**. Sending cookies from a browser where you're signed in clears it:

1. Sign in to YouTube in your browser.
2. Open **Settings** in the app and pick that browser under *Cookies from browser*.
3. Fetch the video again.

Platform notes:

* **macOS Safari** needs Full Disk Access for the app (or your terminal), otherwise
  cookie extraction fails with `Operation not permitted`.
* **Chrome/Chromium/Brave/Edge** prompt for Keychain access the first time.
* If neither works, export a `cookies.txt` with a browser extension and set
  `cookies_file` instead.

Cookies are read from your settings on every request, so you set them once — nothing
is attached per download. Treat `cookies.txt` as a credential: it grants access to
your signed-in session.

## Logs

Every step is logged. Logs always go to a rotating file at
`logs/youtube_downloader.log` (kept across runs, up to ~4 files). In **GUI mode**
they also stream to the terminal running the server. In **console mode** the log
is file-only (so it doesn't clutter the interactive menu) — watch it live with:

```bash
tail -f logs/youtube_downloader.log
```

Set the level in `settings.json` → `{ "log_level": "DEBUG" }` for more detail
(default `INFO`); the bundled default lives in `metadata.json` → `"settings"`.

## Building standalone executables

End users don't need any of the above — they can download a one-file build from the
[Releases page](https://github.com/Hossam-H22/Youtube_Downloader/releases). Those
builds are produced by **PyInstaller** and bundle Python, all packages, and a static
**ffmpeg** (via the `imageio-ffmpeg` dependency), so nothing needs to be installed.

### Running the downloaded macOS build

The macOS binary isn't code-signed, so Gatekeeper blocks it on first launch. After
downloading `Youtube-Downloader`, from its folder run:

```bash
chmod +x Youtube-Downloader          # make it executable
xattr -d com.apple.quarantine Youtube-Downloader   # clear the "unidentified developer" block
./Youtube-Downloader                 # launch it
```

Alternatively, right-click the file in Finder → **Open** → **Open** to allow it once.

To build one locally for your current OS:

```bash
pip install -r requirements.txt -r requirements-build.txt
pyinstaller youtube_downloader.spec
```

The executable lands in `dist/` (`Youtube-Downloader` / `Youtube-Downloader.exe`).
PyInstaller **cannot cross-compile** — a macOS binary must be built on macOS,
Windows on Windows, Linux on Linux. All three are built automatically by the
GitHub Actions workflow (`.github/workflows/build.yml`) and attached to the release
when a `vX.Y.Z` tag is pushed. The build settings live in `youtube_downloader.spec`.

## Notes & troubleshooting

- **Output format:** best MP4 video + M4A audio, merged by ffmpeg.
- **Subtitles** are saved as `.srt` files alongside the video.
- **Resuming:** partial downloads resume automatically; network errors retry up to 10 times.
- **`ffmpeg not found`** — install ffmpeg (see Prerequisites) and make sure it's on your `PATH`.
- **`Could not open folder`** — harmless; the download still completed, only the auto-open step failed.
- **`Sign in to confirm you're not a bot`** — YouTube didn't trust the request. Open
  **Settings** and set *Cookies from browser* to a browser where you're signed in (or
  point `cookies_file` at a `cookies.txt`), then try again. See
  [Signing in (cookies)](#signing-in-cookies) for the platform caveats. This block is
  not retried, because retrying the same anonymous request just repeats it.
- **Subtitle / video-info errors** — usually a private, region-locked, or age-restricted video, or a temporary YouTube rate limit; retry later.
- **`No supported JavaScript runtime` warning** — harmless. Downloads still work
  because the app prefers H.264 formats that don't need YouTube's signature
  challenge. To silence it and unlock all formats (e.g. AV1): install a JS runtime
  (`brew install deno`, or have Node.js installed). `use_js_runtime` is on by
  default; when enabled, the app lets yt-dlp fetch its EJS solver script from the
  yt-dlp GitHub. Set it to `false` in `settings.json` if you'd rather it never
  fetched that script.

