---
name: add-service
description: Add or swap a service (info provider, downloader, subtitle source, chapter splitter) in the YouTube Downloader while preserving the SOLID layering. Use when introducing a new backend/implementation or a new capability behind an interface.
---

# add-service

This project inverts its dependencies: `ConsoleApp` (in `youtube_downloader/cli.py`)
depends only on the abstract interfaces in `youtube_downloader/interfaces.py`, and
the concrete implementations are chosen in **one place** — `build_app()` in `main.py`.
Follow these steps so that layering stays intact (SRP / OCP / DIP).

## Steps

1. **Pick the interface** in `youtube_downloader/interfaces.py`:
   - `InfoProvider` — fetch video/playlist metadata → returns `models.VideoInfo` / `PlaylistInfo`
   - `VideoDownloader` — download a video → returns `bool`
   - `SubtitleService` — list / download subtitles
   - `ChapterSplitter` — split a downloaded video + subtitles into chapters

   If your capability is a genuinely new concern that none of these cover, add a
   new ABC here first (keep it narrow — interface segregation).

2. **Write the concrete class** in the module that owns that concern:
   | Interface        | Module                              | Existing class                    |
   | ---------------- | ----------------------------------- | --------------------------------- |
   | `InfoProvider`   | `youtube_downloader/info_service.py`| `YtDlpInfoProvider`               |
   | `VideoDownloader`| `youtube_downloader/downloader.py`  | `YtDlpDownloader`                 |
   | `SubtitleService`| `youtube_downloader/subtitles.py`   | `TranscriptApiSubtitleService`    |
   | `ChapterSplitter`| `youtube_downloader/chapters.py`    | `FfmpegChapterSplitter`           |

   Subclass the ABC and implement every abstract method with the **exact signature**
   (LSP — it must be a drop-in substitute). For a new concern, create a new module.

3. **Wire it in `main.py` → `build_app()`** — the only place concrete classes are
   named. Swap or add the argument passed to `ConsoleApp(...)`.

4. **Never import concrete services into `cli.py`.** `ConsoleApp` receives its
   collaborators via `__init__` and uses only the interface types. If you find
   yourself importing a concrete class there, stop — pass it through `build_app()`.

5. **Match conventions** (see `CLAUDE.md`): typed dataclasses from `models.py` (not
   dicts), snake_case names, type hints, and keep all `input()`/`print()` in `cli.py`.

6. **Verify** with the `/verify` skill.

## Worked example — an alternate downloader

```python
# youtube_downloader/downloader.py
from .interfaces import VideoDownloader

class DryRunDownloader(VideoDownloader):
    """Logs what would be downloaded instead of downloading (useful for testing)."""
    def download(self, url: str, title: str, output_path: str = '.') -> bool:
        print(f"[dry-run] would download '{title}' from {url} -> {output_path}")
        return True
```

```python
# main.py  (inside build_app())
return ConsoleApp(
    info_provider=YtDlpInfoProvider(),
    downloader=DryRunDownloader(),          # <-- swapped, nothing else changes
    subtitle_service=TranscriptApiSubtitleService(),
    chapter_splitter=FfmpegChapterSplitter(),
)
```

`cli.py` is untouched — that is the point.
