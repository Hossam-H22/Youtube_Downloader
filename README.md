#  <img src="https://github.com/user-attachments/assets/9b47385d-6c97-4627-b7c1-7d34dcd1afce" width=38 /> Youtube Downloader 


Video Downloader is a powerful and easy-to-use application designed to help you download entire playlists or specific videos from YouTube with ease with the ability to choose subtitle language and split the video into chapters. Whether you want to save your favorite videos for offline viewing, create a personal video library, or download educational content, Video Downloader has you covered. [Try it now](https://github.com/Hossam-H22/Youtube_Downloader/releases)

## Features

- **Download videos & playlists** — grab a single video or a whole playlist as best-quality MP4 (video + audio merged with ffmpeg).
- **Pick specific playlist videos** — in the web app, select exactly which videos to download with per-video checkboxes and a "Select all" toggle.
- **Subtitles** — choose a subtitle language and save it as an `.srt` file alongside the video.
- **Split into chapters** — for videos with chapters, split the video *and* its subtitles into per-chapter files inside a `Chapters/` folder.
- **Numbered playlist files** — optionally prefix each downloaded file with its position (`01.`, `02.`, …).
- **Live progress** — real-time progress bar with download speed and ETA (web app).
- **Retry failed downloads** — failed playlist videos are listed with a one-click retry; re-running a playlist skips what's already downloaded.
- **Update notifications** — the app checks GitHub on startup and lets you know when a newer version is available.
- **Built-in log viewer** — view, refresh, auto-refresh, and clear the app logs without leaving the window (web app).
- **Folder picker** — browse to a save folder and open the output folder when a download finishes.

## Download & run (no install)

Grab the ready-to-run app for your operating system from the
**[Releases page](https://github.com/Hossam-H22/Youtube_Downloader/releases)** —
no Python, no ffmpeg, nothing to install. Each build is a single self-contained
file (ffmpeg is bundled inside):

| OS | File | How to run |
| --- | --- | --- |
| Windows | `Youtube-Downloader-windows.exe` | Double-click it. |
| macOS | `Youtube-Downloader-macos` | `chmod +x Youtube-Downloader-macos && xattr -d com.apple.quarantine Youtube-Downloader-macos && ./Youtube-Downloader-macos` (or right-click → **Open** on first launch). |
| Linux | `Youtube-Downloader-linux` | `chmod +x Youtube-Downloader-linux && ./Youtube-Downloader-linux` |

The app opens in your web browser. Logs are written to a `logs/` folder next to
the executable and can also be viewed live via the **Logs** button in the app.

> **First-launch warnings are expected.** The binaries are not code-signed, so:
> - **macOS** may say the app "cannot be opened because the developer cannot be
>   verified." Right-click the file → **Open** → **Open**, or run
>   `xattr -d com.apple.quarantine Youtube-Downloader-macos` once.
> - **Windows** SmartScreen may show a blue prompt — click **More info → Run anyway**.
> - **Linux** folder picker needs `zenity` installed; without it you can still type
>   the destination path manually.

## Running from source

Two ways to run it, sharing the same download engine:

- **Web GUI (default):** `python main.py` — opens a local web app in your browser.
- **Console:** `python main.py --console-view` — the interactive terminal menu.

See **[RUN.md](RUN.md)** for step-by-step instructions on installing the prerequisites, setting up a virtual environment, and running either mode.


















<!-- ![youtube-dl](https://github.com/user-attachments/assets/9b47385d-6c97-4627-b7c1-7d34dcd1afce) -->
