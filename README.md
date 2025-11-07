# YouTube Audio Segment Downloader

This Python script downloads specific time ranges of audio from YouTube videos.

## Requirements

- Python 3.6+
- FFmpeg

## Installation

1.  Clone this repository or download the files.
2.  Install the required Python packages:
    ```
    pip install -r requirements.txt
    ```
3.  Download FFmpeg (ffmpeg-git-essentials.7z) from [https://www.gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds) and extract it.
4.  Place the extracted FFmpeg folder in the root directory of the project. The folder structure should look like this:
    ```
    Youtube_Audio_Segmentation/
    ├── ffmpeg-2025-11-06-git-222127418b-essentials_build/
    │   └── ...
    ├── main.py
    ├── ...
    ```

## Usage

1.  Create a file named `videos.txt` in the same directory as the script.
2.  Add the YouTube video URLs and the desired time ranges to the `videos.txt` file. The format for each line should be:
    ```
    <youtube_url>,<start_time>,<end_time>
    ```
    For example:
    ```
    https://www.youtube.com/watch?v=dQw4w9WgXcQ,00:00:30,00:01:00
    https://www.youtube.com/watch?v=3tmd-ClpJxA,00:01:00,00:01:30
    ```
3.  Run the script:
    ```
    python main.py
    ```
4.  The audio segments will be downloaded and saved in the same directory with filenames formatted as `<video_id>_<start_time>_<end_time>.mp3`.

