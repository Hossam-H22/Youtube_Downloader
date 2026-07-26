#  <img src="https://github.com/user-attachments/assets/9b47385d-6c97-4627-b7c1-7d34dcd1afce" width=38 /> Youtube Downloader 


Video Downloader is a powerful and easy-to-use application designed to help you download entire playlists or specific videos from YouTube with ease with the ability to choose subtitle language and split the video into chapters. Whether you want to save your favorite videos for offline viewing, create a personal video library, or download educational content, Video Downloader has you covered. [Try it now](https://github.com/Hossam-H22/Youtube_Downloader/releases)

## Download & run (no install)

Grab the ready-to-run app for your operating system from the
**[Releases page](https://github.com/Hossam-H22/Youtube_Downloader/releases)** —
no Python, no ffmpeg, nothing to install. Each build is a single self-contained
file (ffmpeg is bundled inside):

| OS | File | How to run |
| --- | --- | --- |
| Windows | `Youtube-Downloader-windows.exe` | Double-click it. |
| macOS | `Youtube-Downloader-macos` | Right-click → **Open** (first launch only). |
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
