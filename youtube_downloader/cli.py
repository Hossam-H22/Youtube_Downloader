"""The interactive console application.

``ConsoleApp`` owns all user interaction (menu, prompts, printing) and
orchestrates the injected services. It depends only on the abstract interfaces,
never on the concrete yt-dlp / transcript-api / ffmpeg implementations.
"""

import os

from .filesystem import clear_console, create_text_file, ensure_dir, open_folder
from .interfaces import (
    ChapterSplitter,
    InfoProvider,
    SubtitleService,
    VideoDownloader,
)
from .models import Chapter, PlaylistInfo
from .utils import clean_filename, format_counter, format_video_length


class ConsoleApp:
    """Wires the download services together behind an interactive menu."""

    def __init__(
        self,
        info_provider: InfoProvider,
        downloader: VideoDownloader,
        subtitle_service: SubtitleService,
        chapter_splitter: ChapterSplitter,
    ) -> None:
        self.info_provider = info_provider
        self.downloader = downloader
        self.subtitle_service = subtitle_service
        self.chapter_splitter = chapter_splitter

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

            if create_video_folder == 'Y' or create_video_folder == 'y':
                create_video_folder = True
                folder_path = os.path.join(folder_path, info.title)
                ensure_dir(folder_path)
            else:
                create_video_folder = False

            print("\nStart Downloading ... \n")
            self.downloader.download(info.url, info.title, folder_path)
            subtitle_file_path = ""
            if len(info.transcript_list) > 0 and subtitle_choise <= len(info.transcript_list):
                subtitle_file_path = self.subtitle_service.download(
                    info.id, info.title, folder_path, info.transcript_list[subtitle_choise - 1]
                )

            if create_video_folder:
                text_file = [
                    "Video Url: \n",
                    info.url,
                    "\n\n\n\n\n\n\n\n\n\n",
                    f"Title: \n{info.title}\n\n",
                    "Description: \n",
                    info.description
                ]
                create_text_file(text_file, folder_path)
                video_path = os.path.join(folder_path, f"{info.title}.mp4")
                chapters = info.chapters
                if chapters:
                    chapters_folder_path = os.path.join(folder_path, 'Chapters')
                    ensure_dir(chapters_folder_path)
                    self.chapter_splitter.split_video(video_path, chapters, chapters_folder_path)
                    if len(subtitle_file_path) > 0:
                        self.chapter_splitter.split_subtitles(subtitle_file_path, chapters, chapters_folder_path)

            print("\nDownload Finished\n\n")
            open_folder(folder_path)

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
            if numerate_choice == 'y' or numerate_choice == 'Y': numerate_choice = True
            else: numerate_choice = False

            folder_path = input("\nPlease enter the path to the folder where you want to save: ")

            print("\nStart Downloading ... \n")
            folder_path = os.path.join(folder_path, info.title)
            ensure_dir(folder_path)

            text_file = ["Playlist Url: \n", info.url, "\n\n\n\n\n\n\n\n\n\n", "Videos Information: \n\n\n\n"]
            failed_videos = []
            for index, video in enumerate(info.videos_info):
                if numerate_choice: video_title = f"{format_counter(index+1, info.number_videos)}{video.title}"
                else: video_title = video.title

                text_file.append(f"Video #{index+1}\n")
                text_file.append("====================================\n")
                text_file.append(f"Title: {video_title}\n")
                text_file.append(f"Description: {video.description} \n")
                text_file.append("====================================\n\n\n\n\n\n\n")

                print(f"\n[{index+1}/{info.number_videos}] Downloading: {video_title}\n")
                if self.downloader.download(video.url, video_title, folder_path):
                    if len(info.transcript_list) > subtitle_choise-1:
                        self.subtitle_service.download(
                            video.id, video_title, folder_path, info.transcript_list[subtitle_choise - 1]
                        )
                else:
                    failed_videos.append(f"#{index+1} - {video_title}")

            create_text_file(text_file, folder_path)
            print("\nDownload Finished\n")
            if failed_videos:
                print(f"{len(failed_videos)} video(s) failed to download:")
                for failed in failed_videos:
                    print(f"    {failed}")
                print("Re-run the playlist to retry them (already-downloaded videos are skipped).\n")
            else:
                print("\n")
            open_folder(folder_path)

    # ------------------------------------------------------------------ #
    # Menu loop
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        while True:
            print("\nWelcome to Youtube Downloader V1.1.2 😊 developed by Eng.Hossam Hatem \n")
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
