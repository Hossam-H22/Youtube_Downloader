
from pytube import Playlist, YouTube
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import SRTFormatter
import re
import os
import time


def clean_filename(filename):
    pattern = r'[<>:"/\\|?*\x00-\x1F]'
    return re.sub(pattern, '', filename)

def download_youtube_videos(playlist_url, noplaylist = True, output_path='.'):
    ydl_opts = {
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        # 'format': 'best',  # Download the best quality
        # 'format': 'bestvideo+bestaudio/best',  # Download the best quality
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',  # Download the best quality
        'noplaylist': noplaylist,  # Only download single video, not the whole playlist
        'progress_hooks': [lambda d: clean_filename(d['filename'])]  # Hook to sanitize filename
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])

def download_subtitles(video_url, output_path='.', language_code='en'):
    try:
        # Extract video ID from the URL
        video_id = video_url.split('v=')[1]

        # Get the transcript for the video
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Find the transcript in the desired language
        transcript = transcript_list.find_transcript([language_code])

        # Fetch the transcript
        transcript_data = transcript.fetch()

        # Format the transcript into SRT format
        formatter = SRTFormatter()
        srt_text = formatter.format_transcript(transcript_data)

        # Save the subtitle as SRT file
        yt = YouTube(video_url)
        title = clean_filename(yt.title)
        filename = f'{output_path}/{title}.srt'
        with open(filename, "w", encoding="utf-8") as file:
            file.write(srt_text)
        print(f"Subtitle saved as {filename}")
    except Exception as e:
        print(f"An error occurred: {e}")

def get_available_subtitles(video_id):
    try:
        # Retrieve the list of available transcripts
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        subtitle_languages = []

        for transcript in transcripts:
            # Collect available languages
            subtitle_languages.append(transcript.language_code)

        return subtitle_languages
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def format_video_length(seconds):
    hours = seconds // 3600  # Calculate the number of hours
    minutes = (seconds % 3600) // 60  # Calculate the remaining minutes
    remaining_seconds = seconds % 60  # Calculate the remaining seconds
    msg=""
    if hours>0:
        msg += f"{hours} hourse"
    if minutes>0:
        msg += f" and {minutes} minutes"
    if remaining_seconds>0:
        msg += f" and {remaining_seconds} seconds"
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




while True:
    print("\nWelcome to Youtube Downloader 😊 \n")

    dwonloadType = int(input("Please choose number: \n1 - Video \n2 - Playlist \n3 - Quit 👋\nYou choice is: "))

    if dwonloadType == 1:
        video_url = input("\nPlease enter the link of youtube video: ")
    elif dwonloadType == 2:
        playlist_url = input("\nPlease enter the link of youtube playlist: ")
    else:
        break


    if dwonloadType == 1:
        print('\n')
        print('Waiting ...', end='\r')
        yt = YouTube(video_url)
        video_title = yt.title
        video_length = format_video_length(yt.length)
        transcript_list = get_available_subtitles(video_url.split('v=')[1])
        print('           ', end='\r')

        print(f'Video Information:')
        print(f'Title: {video_title}')
        print(f'Duration: {video_length}')
        if len(transcript_list)>0:
            print(f'Video has subtitles: {transcript_list}')

        downloadChoice = input("\nDownload Video: Y or N ?  ")
        if downloadChoice=='Y' or downloadChoice=='y':
            subtitle_choise = print_subtitles(transcript_list)
            folder_path = input("Please enter the path to the folder where you want to save: ")

            print("\nStart Downloading ... \n")
            download_youtube_videos(video_url, True, folder_path)
            if len(transcript_list)>0 and subtitle_choise<=len(transcript_list):
                download_subtitles(video_url, folder_path, transcript_list[subtitle_choise-1])
            print("\nDownload Finished\n\n")
            os.startfile(folder_path)
            time.sleep(5)
        else: time.sleep(1)
    else:
        print('\n')
        print('Waiting ...', end='\r')
        playlist = Playlist(playlist_url)
        playlist_title = playlist.title
        playlist_urls = playlist.video_urls
        playlist_length = format_video_length( get_totlal_length_playlist(playlist_urls) )
        transcript_list = get_available_subtitles(playlist_urls[0].split('v=')[1])
        print('           ', end='\r')

        print(f'Playlist Information:')
        print(f'Title: {playlist_title}')
        print(f'Number of Videos: {len(playlist_urls)}')
        print(f'Total Duration: {playlist_length}')
        if len(transcript_list) > 0:
            print(f'Playlist has subtitles: {transcript_list}')

        downloadChoice = input("\nDownload Video: Y or N ?  ")
        if downloadChoice == 'Y' or downloadChoice == 'y':
            subtitle_choise = print_subtitles(transcript_list)
            folder_path = input("Please enter the path to the folder where you want to save: ")

            print("\nStart Downloading ... \n")
            folder_path = os.path.join(folder_path, playlist_title)
            os.makedirs(folder_path, exist_ok=True)

            download_youtube_videos(playlist_url, False, folder_path)
            for video_url in playlist_urls:
                download_subtitles(video_url, folder_path, transcript_list[subtitle_choise-1])
            print("\nDownload Finished\n\n")
            os.startfile(folder_path)
            time.sleep(5)
        else: time.sleep(1)

    clear_console()






