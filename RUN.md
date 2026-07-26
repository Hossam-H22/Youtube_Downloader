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

## Notes & troubleshooting

- **Output format:** best MP4 video + M4A audio, merged by ffmpeg.
- **Subtitles** are saved as `.srt` files alongside the video.
- **Resuming:** partial downloads resume automatically; network errors retry up to 10 times.
- **`ffmpeg not found`** — install ffmpeg (see Prerequisites) and make sure it's on your `PATH`.
- **`Could not open folder`** — harmless; the download still completed, only the auto-open step failed.
- **Subtitle / video-info errors** — usually a private, region-locked, or age-restricted video, or a temporary YouTube rate limit; retry later.

