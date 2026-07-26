"""The interactive console application.

``ConsoleApp`` owns all user interaction (menu, prompts, printing) and delegates
the actual downloading to the shared :class:`DownloadWorkflows`. It depends only
on abstractions, never on the concrete yt-dlp / transcript-api / ffmpeg classes.
"""

from .filesystem import clear_console, open_folder
from .interfaces import InfoProvider, SubtitleService
from .metadata import get_metadata
from .models import Chapter, PlaylistDownloadOptions, PlaylistInfo, VideoDownloadOptions
from .utils import clean_filename, format_video_length
from .workflows import DownloadWorkflows


class ConsoleApp:
    """Drives the download workflows behind an interactive menu."""

    def __init__(
        self,
        info_provider: InfoProvider,
        subtitle_service: SubtitleService,
        workflows: DownloadWorkflows,
    ) -> None:
        self.info_provider = info_provider
        self.subtitle_service = subtitle_service
        self.workflows = workflows

    # ------------------------------------------------------------------ #
    # Presentation helpers
    # ------------------------------------------------------------------ #
    def print_subtitles(self, transcript_list: list[str]) -> int:
        subtitle_choise = 10000000000
        if len(transcript_list) > 0:
            print('Choose Subtitle language number: ')
            index = 1
            for transcript in transcript_list:
                print(f'{index} - {transcript}')
                index += 1
            print(f'{index} - None')
            subtitle_choise = int(input("Your Choice = "))
            if subtitle_choise < 1 or subtitle_choise > index:
                subtitle_choise = 1
        return subtitle_choise

    def print_chapters_information(self, chapters: list[Chapter]) -> None:
        print("Video Chapters: ")
        for index, chapter in enumerate(chapters):
            chapter_title = clean_filename(chapter.title)
            duration = format_video_length(int(chapter.end_time - chapter.start_time))
            print(f"    {index+1}. {chapter_title}  =>  {duration}")

    def _language_for_choice(self, transcript_list: list[str], subtitle_choise: int) -> "str | None":
        """Map a numeric subtitle menu choice to a language code (or None)."""
        if transcript_list and 1 <= subtitle_choise <= len(transcript_list):
            return transcript_list[subtitle_choise - 1]
        return None

    # ------------------------------------------------------------------ #
    # Video flow
    # ------------------------------------------------------------------ #
    def video_processes(self, video_url: str) -> None:
        info = self.info_provider.get_video_info(video_url)
        info.transcript_list = self.subtitle_service.list_available(info.id)

        print('           ', end='\r')
        clear_console()
        print('\nVideo Information:')
        print(f"Title: {info.title}")
        print(f"Duration: {info.length}")
        if len(info.transcript_list) > 0:
            print(f"Video have subtitles: {info.transcript_list}")
        else:
            print("Video doesn't have subtitles")
        if len(info.chapters):
            self.print_chapters_information(info.chapters)

        download_choice = input("\nDownload Video: Y or N ?  ")
        if download_choice == 'Y' or download_choice == 'y':
            subtitle_choise = self.print_subtitles(info.transcript_list)
            folder_path = input("\nPlease enter the path to the folder where you want to save: ")

            create_video_folder = input("\nSplit video to chapters if exist: Y or N ?  ")
            split_chapters = create_video_folder in ('Y', 'y')

            print("\nStart Downloading ... \n")
            options = VideoDownloadOptions(
                save_path=folder_path,
                subtitle_language=self._language_for_choice(info.transcript_list, subtitle_choise),
                split_chapters=split_chapters,
            )
            result = self.workflows.download_video(info, options)

            print("\nDownload Finished\n\n")
            open_folder(result.output_path)

    # ------------------------------------------------------------------ #
    # Playlist flow
    # ------------------------------------------------------------------ #
    def _resolve_playlist_subtitles(self, info: PlaylistInfo) -> list[str]:
        """Return the subtitle languages of the first video that has any."""
        for video in info.videos_info:
            list_lang = self.subtitle_service.list_available(video.id)
            if list_lang:
                return list_lang
        return []

    def playlist_processes(self, playlist_url: str) -> None:
        info = self.info_provider.get_playlist_info(playlist_url)
        info.transcript_list = self._resolve_playlist_subtitles(info)

        print('           ', end='\r')
        clear_console()
        print('Playlist Information:')
        print(f"Title: {info.title}")
        print(f"Number of Videos: {info.number_videos}")
        print(f"Total Duration: {info.length}")
        if len(info.transcript_list) > 0: print(f"Playlist has subtitles: {info.transcript_list}")

        download_choice = input("\nDownload Playlist: Y or N ?  ")
        if download_choice == 'Y' or download_choice == 'y':
            subtitle_choise = self.print_subtitles(info.transcript_list)

            numerate_choice = input("\nNumerated Playlist: Y or N ?  ")
            numerate = numerate_choice in ('y', 'Y')

            folder_path = input("\nPlease enter the path to the folder where you want to save: ")

            print("\nStart Downloading ... \n")

            options = PlaylistDownloadOptions(
                save_path=folder_path,
                subtitle_language=self._language_for_choice(info.transcript_list, subtitle_choise),
                numerate=numerate,
            )

            def on_video(index: int, total: int, title: str) -> None:
                print(f"\n[{index}/{total}] Downloading: {title}\n")

            result = self.workflows.download_playlist(info, options, on_video=on_video)

            print("\nDownload Finished\n")
            if result.failed_videos:
                print(f"{len(result.failed_videos)} video(s) failed to download:")
                for failed in result.failed_videos:
                    print(f"    {failed}")
                print("Re-run the playlist to retry them (already-downloaded videos are skipped).\n")
            else:
                print("\n")
            open_folder(result.output_path)

    # ------------------------------------------------------------------ #
    # Menu loop
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        while True:
            meta = get_metadata()
            developer = meta.get('author', {}).get('name', '')
            print(f"\nWelcome to {meta.get('name', 'Youtube Downloader')} V{meta.get('version', '0.0.0')} 😊 developed by {developer} \n")
            download_type = int(input("Please choose number: \n1 - Video \n2 - Playlist \n3 - Quit 👋\nYou choice is: "))
            if download_type == 1:
                video_url = input("\nPlease enter the link of youtube video: ")
                print('\n')
                print('Waiting ...', end='\r')
                self.video_processes(video_url)
            elif download_type == 2:
                playlist_url = input("\nPlease enter the link of youtube playlist: ")
                print('\n')
                print('Waiting ...', end='\r')
                self.playlist_processes(playlist_url)
            else:
                break

            input("\n\n\nPress any key to continue .. \n")
            clear_console()
