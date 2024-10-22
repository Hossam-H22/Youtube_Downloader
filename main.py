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

def get_youtube_video_info(url):
    ydl_opts = {
        'quiet': True  # Suppress output
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    video_information = {
        "url": url,
        "id": info["id"],
        "title": clean_filename(info["title"]),
        "length": format_video_length(info["duration"]),
        "length_seconds": info["duration"],
        "description": info["description"],
        "chapters": info.get('chapters', [])
    }
    return video_information

def get_youtube_playlist_info(url):
    playlist = Playlist(url)
    video_urls = playlist.video_urls
    playlist_information = {
        'url': url,
        'id': playlist.playlist_id,
        'title': clean_filename(playlist.title),
        'number_videos': playlist.length,
        'length': '',
        # 'description': playlist.description,
        'transcript_list': [],
        'videos_urls': video_urls,
        'videos_info': [],
    }

    for video_url in video_urls:
        playlist_information['videos_info'].append(get_youtube_video_info(video_url))

    total_length_in_seconds = get_total_length_playlist(playlist_information['videos_info'])
    playlist_information['length'] = format_video_length(total_length_in_seconds)
    return playlist_information

def download_youtube_videos(url, title, output_path='.'):
    ydl_opts = {
        'outtmpl': f'{output_path}/{title}.%(ext)s',
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',  # Download the best quality
        'noplaylist': True,  # Only download single video, not the whole playlist
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def download_subtitles(video_id, title, output_path='.', language_code='en'):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id) # Get the transcript for the video
        transcript = transcript_list.find_transcript([language_code]) # Find the transcript in the desired language
        transcript_data = transcript.fetch() # Fetch the transcript

        # Format the transcript into SRT format
        formatter = SRTFormatter()
        srt_text = formatter.format_transcript(transcript_data)

        # Save the subtitle as SRT file
        filename = f'{output_path}/{title}.srt'
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
        # print(f"An error occurred: {e} \n")
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

def print_chapters_information(chapters):
    print("Video Chapters: ")
    for index, chapter in enumerate(chapters):
        chapter_title = clean_filename(chapter['title'])
        duration = format_video_length(int(chapter['end_time'] - chapter['start_time']))
        print(f"    {index+1}. {chapter_title}  =>  {duration}")

def get_total_length_playlist(videos_info):
    total_length = 0
    for video in videos_info:
        total_length += video['length_seconds']
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

def create_text_file(list, path):
    os.makedirs(path, exist_ok=True) # Ensure the directory exists
    file_path = os.path.join(path, 'Link.txt') # Define the file path

    # Write the description to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        for line in list:
            file.write(line)

def video_processes(video_url):
    info = get_youtube_video_info(video_url)
    info['transcript_list'] = get_available_subtitles(info['id'])
    if len(info['transcript_list'])>0 and info['transcript_list'][0] == "Error":
        info['transcript_list'] = []

    print('           ', end='\r')
    clear_console()
    print(f'\nVideo Information:')
    print(f'Title: {info['title']}')
    print(f'Duration: {info['length']}')
    if len(info['transcript_list']) > 0:
        print(f'Video have subtitles: {info['transcript_list']}')
    else:
        print(f"Video doesn't have subtitles")
    if len(info['chapters']):
        print_chapters_information(info['chapters'])
    else:
        print(f"Video doesn't have chapters")

    downloadChoice = input("\nDownload Video: Y or N ?  ")
    if downloadChoice == 'Y' or downloadChoice == 'y':
        subtitle_choise = print_subtitles(info['transcript_list'])
        folder_path = input("\nPlease enter the path to the folder where you want to save: ")
        # createVideoFolder = input("\nWrap video with a folder: Y or N ?  ")
        createVideoFolder = input("\nSplit video to chapters: Y or N ?  ")
        if createVideoFolder == 'Y' or createVideoFolder == 'y':
            createVideoFolder = True
            folder_path = os.path.join(folder_path, info['title'])
            os.makedirs(folder_path, exist_ok=True)
        else:
            createVideoFolder = False

        print("\nStart Downloading ... \n")
        download_youtube_videos(info['url'], info['title'], folder_path)
        subtitleFilePath = ""
        if len(info['transcript_list']) > 0 and subtitle_choise <= len(info['transcript_list']):
            subtitleFilePath = download_subtitles(info['id'], info['title'], folder_path, info['transcript_list'][subtitle_choise - 1])

        if createVideoFolder:
            textFile = [
                "Video Url: \n",
                info['url'],
                "\n\n\n\n\n\n\n\n\n\n",
                f"Title: \n{info['title']}\n\n",
                "Description: \n",
                info['description']
            ]
            create_text_file(textFile, folder_path)
            video_path = os.path.join(folder_path, f"{info['title']}.mp4")
            chapters = info['chapters']
            if chapters:
                Chapters_folder_path = os.path.join(folder_path, 'Chapters')
                os.makedirs(Chapters_folder_path, exist_ok=True)
                split_video_into_chapters(video_path, chapters, Chapters_folder_path)
                if len(subtitleFilePath) > 0:
                    split_subtitles_into_chapters(subtitleFilePath, chapters, Chapters_folder_path)

        print("\nDownload Finished\n\n")
        os.startfile(folder_path)

def playlist_processes(playlist_url):
    info = get_youtube_playlist_info(playlist_url)
    for video in info['videos_info']:
        list = get_available_subtitles(video['id'])
        if len(list)>0 and list[0] != "Error":
            info['transcript_list'] = list
            break

    print('           ', end='\r')
    clear_console()
    print(f'Playlist Information:')
    print(f'Title: {info['title']}')
    print(f'Number of Videos: {info['number_videos']}')
    print(f'Total Duration: {info['length']}')
    if len(info['transcript_list']) > 0: print(f'Playlist has subtitles: {info['transcript_list']}')
    # print(f'Description: {info['description']}')

    downloadChoice = input("\nDownload Playlist: Y or N ?  ")
    if downloadChoice == 'Y' or downloadChoice == 'y':
        subtitle_choise = print_subtitles(info['transcript_list'])

        numerateChoice = input("\nNumerated Playlist: Y or N ?  ")
        if numerateChoice == 'y' or numerateChoice == 'Y': numerateChoice = True
        else: numerateChoice = False

        folder_path = input("\nPlease enter the path to the folder where you want to save: ")

        print("\nStart Downloading ... \n")
        folder_path = os.path.join(folder_path, info['title'])
        os.makedirs(folder_path, exist_ok=True)


        textFile = ["Playlist Url: \n", info['url'], "\n\n\n\n\n\n\n\n\n\n", "Videos Information: \n\n\n\n"]
        for index, video in enumerate(info['videos_info']):
            if numerateChoice: video_title = f'{format_counter(index+1, info['number_videos'])}{video['title']}'
            else: video_title = video['title']

            textFile.append(f"Video #{index+1}\n")
            textFile.append("====================================\n")
            textFile.append(f"Title: {video_title}\n")
            textFile.append(f"Description: {video["description"]} \n")
            textFile.append("====================================\n\n\n\n\n\n\n")

            download_youtube_videos(video['url'], video_title, folder_path)
            download_subtitles(video['id'], video_title, folder_path, info['transcript_list'][subtitle_choise - 1])


        create_text_file(textFile, folder_path)
        print("\nDownload Finished\n\n")
        os.startfile(folder_path)


def start_program():
    while True:
        print("\nWelcome to Youtube Downloader V1.1.2 😊 developed by Eng.Hossam Hatem \n")
        downloadType = int(input("Please choose number: \n1 - Video \n2 - Playlist \n3 - Quit 👋\nYou choice is: "))
        if downloadType == 1:
            video_url = input("\nPlease enter the link of youtube video: ")
            print('\n')
            print('Waiting ...', end='\r')
            video_processes(video_url)
        elif downloadType == 2:
            playlist_url = input("\nPlease enter the link of youtube playlist: ")
            print('\n')
            print('Waiting ...', end='\r')
            playlist_processes(playlist_url)
        else:
            break

        input("\n\n\nPress any key to continue .. \n")
        clear_console()


def split_downloaded_video_and_subtitle_into_chapters():
    url = input("video url: ")
    info = get_youtube_video_info(url)
    if info['chapters']:
        print(f"Num of chapters: {len(info['chapters'])} \n")
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
        split_video_into_chapters(video_path, info['chapters'], Chapters_folder_path)
        if len(subtitleFilePath) > 0:
            split_subtitles_into_chapters(subtitleFilePath, info['chapters'], Chapters_folder_path)


if __name__ == '__main__':
    start_program()

    # split_downloaded_video_and_subtitle_into_chapters()








