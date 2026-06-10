# YouTube Audio Downloader 🎵

A fast, modern, and user-friendly desktop application for downloading high-quality audio from YouTube. Built with Python and CustomTkinter, this tool allows you to download full tracks, precise audio clips, or entire playlists with ease—no coding required.

## ✨ Features

* **Full Audio Download:** Paste a YouTube URL and instantly download the highest quality audio as an MP3.
* **Segment Downloading:** Only want a specific part of a video? Enter start and end timestamps (HH:MM:SS) to extract exact audio clips without having to download or process the whole video manually.
* **Playlist Support:** Download entire YouTube playlists. The app automatically creates an organized folder for the playlist and tracks the download progress of each video.
* **Modern GUI:** A clean, dark-mode-ready interface that stays responsive even while heavy background downloads are happening.
* **Live Progress Tracking:** Built-in progress bar and status text so you always know exactly what the application is doing.

---

## 🚀 Getting Started (Using the Release)

You do not need to install Python or understand code to run this application. Just follow these simple steps:

### 1. Download the App
Download the app release `YouTube_Audio_Downloader_v1.0.exe`.

### 2. Install FFmpeg (Crucial Step)
This application uses FFmpeg in the background to process, trim, and format the audio files. It will not work without it.

Download the latest FFmpeg essentials build from [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/).
Extract the downloaded file and place the `ffmpeg-*-essentials_build` folder (e.g., `ffmpeg-2025-11-06-git-222127418b-essentials_build`) besides the exe file.

### 3. Run the App
* Double-click `YouTube_Audio_Downloader_v1.0.exe` to launch the application.
* Select your desired tab at the top (Full Audio, Segment, or Playlist).
* Paste your YouTube URL, configure your times (if using the Segment tab), and click **Download**.

All downloaded MP3 files will automatically be saved into an `output` folder that the app creates right next to the `.exe`.

---

## Preview
<img width="800" height="431" alt="RS2Tracker2026-06-1013-20-00-ezgif com-video-to-gif-converter" src="https://github.com/user-attachments/assets/505bf4a2-261b-48e5-b9f3-80ffc43d582a" />

