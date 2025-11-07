import yt_dlp
import ffmpeg
import os
from tqdm import tqdm
import shutil
import re
import glob

ffmpeg_path = (glob.glob(os.path.join(os.path.dirname(__file__), 'ffmpeg-*-essentials_build', 'ffmpeg-*-essentials_build', 'bin')) or
               glob.glob(os.path.join(os.path.dirname(__file__), 'ffmpeg-*-essentials_build', 'bin')))

if ffmpeg_path:
    os.environ["PATH"] += os.pathsep + ffmpeg_path[0]
else:
    print("FFMPEG path not found. Please make sure ffmpeg is extracted in the root directory.")
    exit()

def is_valid_youtube_url(url):
    """
    Checks if the given URL is a valid YouTube video URL and not a playlist.
    """
    if 'list=' in url:
        return False
    youtube_regex = re.compile(
        r'^(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%?]{11})$')
    return re.match(youtube_regex, url) is not None

def download_full_audio(youtube_url):
    """
    Downloads the full audio from a YouTube video.

    Args:
        youtube_url (str): The URL of the YouTube video.
    """
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pbar = tqdm(total=100, unit='%', desc="Downloading")

    def progress_hook(d):
        if d['status'] == 'downloading':
            pbar.total = d['total_bytes']
            pbar.update(d['downloaded_bytes'] - pbar.n)
        if d['status'] == 'finished':
            pbar.n = pbar.total
            pbar.close()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=True)
        video_title = info_dict.get('title', 'untitled')
        sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-')).rstrip()
        output_filename = os.path.join(output_dir, f"{sanitized_title}.mp3")
        downloaded_file = ydl.prepare_filename(info_dict).replace(info_dict['ext'], 'mp3')
        os.rename(downloaded_file, output_filename)
        return output_filename


def download_audio_segment(youtube_url, start_time, end_time):
    """
    Downloads a specific audio segment from a YouTube video.

    Args:
        youtube_url (str): The URL of the YouTube video.
        start_time (str): The start time of the audio segment in HH:MM:SS format.
        end_time (str): The end time of the audio segment in HH:MM:SS format.
    """
    
    if not os.path.exists("temp"):
        os.makedirs("temp")

    pbar = tqdm(total=100, unit='%', desc="Downloading")

    def progress_hook(d):
        if d['status'] == 'downloading':
            pbar.total = d['total_bytes']
            pbar.update(d['downloaded_bytes'] - pbar.n)
        if d['status'] == 'finished':
            pbar.n = pbar.total
            pbar.close()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "temp/%(id)s.%(ext)s",
        "progress_hooks": [progress_hook],
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=True)
        audio_file = ydl.prepare_filename(info_dict).replace(info_dict['ext'], 'mp3')
        video_title = info_dict.get('title', 'untitled')


    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-')).rstrip()
    output_filename = os.path.join(output_dir, f"{sanitized_title}_{start_time.replace(':', '-')}_{end_time.replace(':', '-')}.mp3")

    # Cut the audio to the specified time range
    (
        ffmpeg
        .input(audio_file, ss=start_time, to=end_time)
        .output(output_filename)
        .run()
    )

    # Clean up the temporary audio file
    os.remove(audio_file)
    return output_filename

def validate_time(time_str):
    """Validates the time format and returns the time in seconds."""
    try:
        h, m, s = map(int, time_str.split(':'))
        if not (0 <= h and 0 <= m <= 59 and 0 <= s <= 59):
            return None
        return h * 3600 + m * 60 + s
    except (ValueError, TypeError):
        return None


def is_valid_youtube_playlist_url(url):
    """
    Checks if the given URL is a valid YouTube playlist URL.
    """
    playlist_regex = re.compile(r'^(https?://)?(www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)')
    return re.match(playlist_regex, url) is not None

def download_playlist(playlist_url):
    """
    Downloads the audio of all videos in a YouTube playlist.

    Args:
        playlist_url (str): The URL of the YouTube playlist.
    """
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(playlist_url, download=False)
        playlist_title = info_dict.get('title', 'untitled_playlist')
        sanitized_playlist_title = "".join(c for c in playlist_title if c.isalnum() or c in (' ', '-')).rstrip()
        playlist_output_dir = os.path.join(output_dir, sanitized_playlist_title)

    if not os.path.exists(playlist_output_dir):
        os.makedirs(playlist_output_dir)

    pbar = tqdm(total=len(info_dict['entries']), unit='video', desc=f"Downloading playlist: {playlist_title}")

    def progress_hook(d):
        if d['status'] == 'finished':
            pbar.update(1)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(playlist_output_dir, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        'ignoreerrors': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])
    
    pbar.close()
    return playlist_output_dir


if __name__ == "__main__":
    while True:
        print("Welcome to youtube audio downloader!")
        print("Choose an option:")
        print("1. Download full video audio")
        print("2. Download video audio segment")
        print("3. Download playlist audio")
        print("4. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            while True:
                youtube_url = input("Enter the YouTube URL: ")
                if is_valid_youtube_url(youtube_url):
                    break
                else:
                    print("Invalid YouTube URL. Please enter a valid URL.")
            try:
                print(f"Downloading full audio from {youtube_url}...")
                output_filename = download_full_audio(youtube_url)
                print(f"Successfully downloaded full audio to{output_filename}")
            except Exception as e:
                print(f"Error downloading {youtube_url}: {e}")

        elif choice == '2':
            while True:
                youtube_url = input("Enter the YouTube URL: ")
                if is_valid_youtube_url(youtube_url):
                    break
                else:
                    print("Invalid YouTube URL. Please enter a valid URL.")
            while True:
                start_time_str = input("Enter the start time (HH:MM:SS): ")
                end_time_str = input("Enter the end time (HH:MM:SS): ")

                start_time_seconds = validate_time(start_time_str)
                end_time_seconds = validate_time(end_time_str)

                if start_time_seconds is None or end_time_seconds is None:
                    print("Invalid time format. Please use HH:MM:SS.")
                    continue

                if start_time_seconds >= end_time_seconds:
                    print("Start time must be less than end time.")
                    continue
                
                break
            
            try:
                print(f"Downloading audio segment from {youtube_url} between {start_time_str} and {end_time_str}...")
                output_filename = download_audio_segment(youtube_url, start_time_str, end_time_str)
                print(f"Successfully downloaded audio segment to{output_filename}")
            except Exception as e:
                print(f"Error downloading {youtube_url}: {e}")

        elif choice == '3':
            while True:
                playlist_url = input("Enter the YouTube playlist URL: ")
                if is_valid_youtube_playlist_url(playlist_url):
                    break
                else:
                    print("Invalid YouTube playlist URL. Please enter a valid URL.")
            try:
                print(f"Downloading playlist from {playlist_url}...")
                playlist_dir = download_playlist(playlist_url)
                print(f"Successfully downloaded playlist to {playlist_dir}")
            except Exception as e:
                print(f"Error downloading playlist {playlist_url}: {e}")

        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

    # Clean up the temporary directory
    if os.path.exists("temp"):
        shutil.rmtree("temp")