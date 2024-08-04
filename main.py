from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import SRTFormatter
from pysrt import SubRipFile, SubRipItem, SubRipTime
from pytube import Playlist, YouTube
import subprocess
import yt_dlp
import pysrt
import time
import re
import os


def clean_filename(filename):
    pattern = r'[<>:"/\\|?*\x00-\x1F]'
    return re.sub(pattern, '', filename)

def get_youtube_video_info(video_url):
    ydl_opts = {
        'quiet': True  # Suppress output
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return info

def download_youtube_videos(playlist_url, noplaylist = True, output_path='.', numerate=False):
    ydl_opts = {
        'outtmpl': f'{output_path}/%(playlist_index)s. %(title)s.%(ext)s' if not noplaylist and numerate else f'{output_path}/%(title)s.%(ext)s',
        # 'format': 'best',  # Download the best quality
        # 'format': 'bestvideo+bestaudio/best',  # Download the best quality
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',  # Download the best quality
        'noplaylist': noplaylist,  # Only download single video, not the whole playlist
        'progress_hooks': [lambda d: clean_filename(d['filename'])]  # Hook to sanitize filename
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])

def download_subtitles(video_url, output_path='.', language_code='en', video_index=""):
    try:
        video_id = video_url.split('v=')[1] # Extract video ID from the URL
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id) # Get the transcript for the video
        transcript = transcript_list.find_transcript([language_code]) # Find the transcript in the desired language
        transcript_data = transcript.fetch() # Fetch the transcript

        # Format the transcript into SRT format
        formatter = SRTFormatter()
        srt_text = formatter.format_transcript(transcript_data)

        # Save the subtitle as SRT file
        yt = YouTube(video_url)
        title = clean_filename(yt.title)
        filename = f'{output_path}/{title}.srt' if len(video_index)==0 else f'{video_index}{output_path}/{title}.srt'
        with open(filename, "w", encoding="utf-8") as file:
            file.write(srt_text)
        print(f"Subtitle saved as {filename}")
        return filename
    except Exception as e:
        print(f"An error occurred: {e} \n")
        return ""

def get_available_subtitles(video_id):
    try:
        # Retrieve the list of available transcripts
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        subtitle_languages = []
        for transcript in transcripts:
            subtitle_languages.append(transcript.language_code) # Collect available languages

        return subtitle_languages
    except Exception as e:
        print(f"An error occurred: {e} \n")
        return ["Error"]

def format_video_length(seconds):
    hours = seconds // 3600  # Calculate the number of hours
    minutes = (seconds % 3600) // 60  # Calculate the remaining minutes
    remaining_seconds = seconds % 60  # Calculate the remaining seconds
    msg=""
    if hours>0:
        msg += f"{hours} hours"
    if minutes>0:
        if hours > 0:
            msg += f" and "
        msg += f"{minutes} minutes"
    if remaining_seconds>0:
        if hours>0 or minutes>0:
            msg += f" and "
        msg += f"{remaining_seconds} seconds"
    return msg

def print_subtitles(transcript_list):
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

def get_totlal_length_playlist(playlist_urls):
    total_length = 0
    for video_url in playlist_urls:
        yt = YouTube(video_url)
        total_length += yt.length
    return total_length

def clear_console():
    # Clear command for Windows
    if os.name == 'nt':
        os.system('cls')
    # Clear command for Unix/Linux/Mac
    else:
        os.system('clear')

def format_counter(counter, length):
    total_digit_len = len(str(abs(length)))
    digit_len = len(str(abs(counter)))
    return f"{'0' * (total_digit_len - digit_len)}{counter}. "

def seconds_to_srt_time(seconds):
    return SubRipTime.from_ordinal(int(seconds * 1000))

def split_subtitles_into_chapters(subtitle_path, chapters, output_path):
    subs = SubRipFile.open(subtitle_path)
    index = 1
    for chapter in chapters:
        chapter_title = clean_filename(chapter['title'])
        start_time = seconds_to_srt_time(chapter['start_time'])
        end_time = seconds_to_srt_time(chapter['end_time'])
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

def split_video_into_chapters(video_path, chapters, output_path):
    index = 1
    for chapter in chapters:
        start_time = chapter['start_time']
        end_time = chapter['end_time']
        chapter_title = clean_filename(chapter['title'])
        video_index = format_counter(index, len(chapters))
        chapter_file = os.path.join(output_path, f"{video_index}{chapter_title}.mp4")
        command = [
            'ffmpeg', '-i', video_path,
            '-ss', str(start_time), '-to', str(end_time),
            '-c', 'copy', chapter_file
        ]
        subprocess.run(command)
        index += 1

def create_text_file(text, path):
    os.makedirs(path, exist_ok=True) # Ensure the directory exists
    file_path = os.path.join(path, 'Link.txt') # Define the file path

    # Write the description to the file
    with open(file_path, 'w') as file:
        file.write(text)



def video_processes(video_url):
    yt = YouTube(video_url)
    video_title = yt.title
    video_length = format_video_length(yt.length)
    transcript_list = get_available_subtitles(video_url.split('v=')[1])
    if transcript_list[0] == "Error": transcript_list = []

    print('           ', end='\r')

    print(f'\nVideo Information:')
    print(f'Title: {video_title}')
    print(f'Duration: {video_length}')
    if len(transcript_list) > 0:
        print(f'Video have subtitles: {transcript_list}')
    else:
        print(f"Video doesn't have subtitles")

    downloadChoice = input("\nDownload Video: Y or N ?  ")
    if downloadChoice == 'Y' or downloadChoice == 'y':
        subtitle_choise = print_subtitles(transcript_list)
        folder_path = input("\nPlease enter the path to the folder where you want to save: ")
        createVideoFolder = input("\nWrap video with a folder: Y or N ?  ")
        if createVideoFolder == 'Y' or createVideoFolder == 'y':
            createVideoFolder = True
            folder_path = os.path.join(folder_path, clean_filename(video_title))
            os.makedirs(folder_path, exist_ok=True)
        else:
            createVideoFolder = False

        print("\nStart Downloading ... \n")
        download_youtube_videos(video_url, True, folder_path)
        subtitleFilePath = ""
        if len(transcript_list) > 0 and subtitle_choise <= len(transcript_list):
            subtitleFilePath = download_subtitles(video_url, folder_path, transcript_list[subtitle_choise - 1])

        if createVideoFolder:
            # txt = f"{video_url} \n\n\n\n\n\n\n{video_description}"
            create_text_file(video_url, folder_path)
            info = get_youtube_video_info(video_url)
            title = clean_filename(info['title'])
            chapters = info.get('chapters', [])
            if chapters:
                video_path = os.path.join(folder_path, f"{title}.mp4")
                Chapters_folder_path = os.path.join(folder_path, 'Chapters')
                os.makedirs(Chapters_folder_path, exist_ok=True)
                split_video_into_chapters(video_path, chapters, Chapters_folder_path)
                if len(subtitleFilePath) > 0:
                    split_subtitles_into_chapters(subtitleFilePath, chapters, Chapters_folder_path)

        print("\nDownload Finished\n\n")
        os.startfile(folder_path)
        # time.sleep(5)
    # else: time.sleep(1)

def playlist_processes(playlist_url):
    playlist = Playlist(playlist_url)
    playlist_title = playlist.title
    playlist_urls = playlist.video_urls
    playlist_length = format_video_length(get_totlal_length_playlist(playlist_urls))
    transcript_list = []
    # transcript_list = get_available_subtitles(playlist_urls[0].split('v=')[1])
    for video_url in playlist_urls:
        list = get_available_subtitles(video_url.split('v=')[1])
        if list[0] != "Error":
            transcript_list = list
            break

    print('           ', end='\r')

    print(f'Playlist Information:')
    print(f'Title: {playlist_title}')
    print(f'Number of Videos: {len(playlist_urls)}')
    print(f'Total Duration: {playlist_length}')
    if len(transcript_list) > 0:
        print(f'Playlist has subtitles: {transcript_list}')

    downloadChoice = input("\nDownload Playlist: Y or N ?  ")
    if downloadChoice == 'Y' or downloadChoice == 'y':
        subtitle_choise = print_subtitles(transcript_list)

        numerateChoice = input("\nNumerated Playlist: Y or N ?  ")
        if numerateChoice == 'y' or numerateChoice == 'Y':
            numerateChoice = True
        else:
            numerateChoice = False

        folder_path = input("\nPlease enter the path to the folder where you want to save: ")

        print("\nStart Downloading ... \n")
        folder_path = os.path.join(folder_path, playlist_title)
        os.makedirs(folder_path, exist_ok=True)

        download_youtube_videos(playlist_url, False, folder_path, numerateChoice)
        index = 1
        for video_url in playlist_urls:
            video_index = ""
            if numerateChoice: video_index = format_counter(index, len(playlist_urls))
            download_subtitles(video_url, folder_path, transcript_list[subtitle_choise - 1], video_index)
            index += 1

        create_text_file(playlist_url, folder_path)
        print("\nDownload Finished\n\n")
        os.startfile(folder_path)
        # time.sleep(5)
    # else: time.sleep(1)

def start_program():
    while True:
        print("\nWelcome to Youtube Downloader 😊 \n")

        dwonloadType = int(input("Please choose number: \n1 - Video \n2 - Playlist \n3 - Quit 👋\nYou choice is: "))

        if dwonloadType == 1:
            video_url = input("\nPlease enter the link of youtube video: ")
        elif dwonloadType == 2:
            playlist_url = input("\nPlease enter the link of youtube playlist: ")
        else:
            break

        print('\n')
        print('Waiting ...', end='\r')

        if dwonloadType == 1:
            video_processes(video_url)
        else:
            playlist_processes(playlist_url)

        z = input("\n\n\nPress any key to continue .. \n")
        clear_console()



def split_downloaded_video_and_subtitle_into_chapters():
    url = input("video url: ")
    chapters = get_youtube_video_info(url).get('chapters', [])
    if chapters:
        print(f"Num of chapters: {len(chapters)} \n")
        folder_path = input("folder path: ")
        if folder_path.startswith('"'): folder_path = folder_path[1:]
        if folder_path.endswith('"'): folder_path = folder_path[:-1]
        video_path = input("video path: ")
        if video_path.startswith('"'): video_path = video_path[1:]
        if video_path.endswith('"'): video_path = video_path[:-1]
        subtitleFilePath = input("subtitle path: ")
        if subtitleFilePath.startswith('"'): subtitleFilePath = subtitleFilePath[1:]
        if subtitleFilePath.endswith('"'): subtitleFilePath = subtitleFilePath[:-1]
        Chapters_folder_path = os.path.join(folder_path, 'Chapters')
        os.makedirs(Chapters_folder_path, exist_ok=True)
        split_video_into_chapters(video_path, chapters, Chapters_folder_path)
        if len(subtitleFilePath) > 0:
            split_subtitles_into_chapters(subtitleFilePath, chapters, Chapters_folder_path)


if __name__ == '__main__':
    start_program()

    # split_downloaded_video_and_subtitle_into_chapters()








