"""Splitting a downloaded video and its subtitles into per-chapter files."""

import os
import subprocess

from pysrt import SubRipFile, SubRipItem

from .interfaces import ChapterSplitter
from .models import Chapter
from .utils import clean_filename, format_counter, seconds_to_srt_time


class FfmpegChapterSplitter(ChapterSplitter):
    """Splits video with ffmpeg and subtitles with pysrt, one file per chapter."""

    def split_video(
        self, video_path: str, chapters: list[Chapter], output_path: str
    ) -> None:
        index = 1
        for chapter in chapters:
            start_time = chapter.start_time
            end_time = chapter.end_time
            chapter_title = clean_filename(chapter.title)
            video_index = format_counter(index, len(chapters))
            chapter_file = os.path.join(output_path, f"{video_index}{chapter_title}.mp4")
            command = [
                'ffmpeg', '-i', video_path,
                '-ss', str(start_time), '-to', str(end_time),
                '-c', 'copy', chapter_file
            ]
            subprocess.run(command)
            index += 1

    def split_subtitles(
        self, subtitle_path: str, chapters: list[Chapter], output_path: str
    ) -> None:
        subs = SubRipFile.open(subtitle_path)
        index = 1
        for chapter in chapters:
            chapter_title = clean_filename(chapter.title)
            start_time = seconds_to_srt_time(chapter.start_time)
            end_time = seconds_to_srt_time(chapter.end_time)
            chapter_subs = SubRipFile()
            for sub in subs:
                if start_time <= sub.start.ordinal <= end_time:
                    adjusted_sub = SubRipItem(
                        index=sub.index,
                        start=sub.start - start_time,
                        end=sub.end - start_time,
                        text=sub.text
                    )
                    chapter_subs.append(adjusted_sub)
            video_index = format_counter(index, len(chapters))
            chapter_sub_path = os.path.join(output_path, f"{video_index}{chapter_title}.srt")
            chapter_subs.save(chapter_sub_path, encoding='utf-8')
            print(f'{chapter_sub_path}  Saved Successfully')
            index += 1
