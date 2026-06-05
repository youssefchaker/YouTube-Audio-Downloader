# YouTube Audio Downloader

This Python script allows you to download audio from YouTube videos, either full audio, specific segments or an entire playlist.

## Features

*   Download full audio from a YouTube video.
*   Download specific audio segments from a YouTube video.
*   Download audio from an entire YouTube playlist.
*   Command-line interface for easy interaction.

## Requirements

*   Python 3.6+
*   FFmpeg

## Installation

1.  Clone this repository or download the files.
2.  Install the required Python packages:
    ```
    pip install -r requirements.txt
    ```
3.  Download the latest FFmpeg essentials build from [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/).
4.  Extract the downloaded file and place the `ffmpeg-*-essentials_build` folder (e.g., `ffmpeg-2025-11-06-git-222127418b-essentials_build`) into the root of the project directory. The script is configured to dynamically locate FFmpeg within this folder.

## Usage

Run the script from your terminal:

```
python main.py
```

The script will present you with a menu of options:

1.  **Download full video audio**: Prompts for a YouTube video URL and downloads the entire audio track.
2.  **Download video audio segment**: Prompts for a YouTube video URL, a start time (HH:MM:SS), and an end time (HH:MM:SS) to download a specific audio segment.
3.  **Download playlist audio**: Prompts for a YouTube playlist URL and downloads the audio for all videos in the playlist into a new folder within the `output` directory, named after the playlist.
4.  **Exit**: Exits the application.

The downloaded audio files will be saved in the `output` directory. For segments, filenames are formatted as `<video_title>_<start_time>_<end_time>.mp3`. For full video audio, it's `<video_title>.mp3`. For playlists, a new folder named after the playlist will be created in `output`, containing `<video_title>.mp3` for each video.